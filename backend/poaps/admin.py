import csv

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse

from utils.admin_mixins import CloudinaryUploadMixin

from .models import PoapClaim, PoapDistribution, PoapDrop, PoapImportBatch, PoapMintLink
from .services import decrypt_token, encrypt_token, generate_mint_links, hash_secret, hash_token


class PoapDropAdminForm(forms.ModelForm):
    class Meta:
        model = PoapDrop
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('event_start_at')
        end = cleaned_data.get('event_end_at')
        max_claims = cleaned_data.get('max_claims')
        errors = {}

        if start and end and end <= start:
            errors['event_end_at'] = 'End time must be after start time.'

        if self.instance.pk and max_claims is not None:
            claimed_count = self.instance.claims.filter(user__isnull=False).count()
            if max_claims < claimed_count:
                errors['max_claims'] = f'Max claims cannot be lower than the current claimed count ({claimed_count}).'

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data


class PoapDistributionAdminForm(forms.ModelForm):
    secret_phrase = forms.CharField(
        required=False,
        help_text='For secret phrase distributions only. Enter a new value to set or rotate the phrase.',
        widget=forms.PasswordInput(render_value=False),
    )
    mint_link_count = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=500,
        label='Generate mint links',
        help_text='Optional. Creates this many mint links when saving a mint-link distribution.',
    )
    mint_link_max_uses = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        initial=1,
        label='Uses per generated link',
    )
    mint_link_expires_at = forms.DateTimeField(
        required=False,
        label='Generated link expiration',
        help_text='Optional expiration applied to links generated from this save.',
    )

    class Meta:
        model = PoapDistribution
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('method')
        secret_phrase = (cleaned_data.get('secret_phrase') or '').strip()
        existing_secret_hash = getattr(self.instance, 'secret_hash', '')
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')
        max_claims = cleaned_data.get('max_claims')
        mint_link_count = cleaned_data.get('mint_link_count') or 0
        mint_link_max_uses = cleaned_data.get('mint_link_max_uses') or 1
        mint_link_expires_at = cleaned_data.get('mint_link_expires_at')
        errors = {}

        if method == PoapDistribution.METHOD_SECRET and not secret_phrase and not existing_secret_hash:
            errors['secret_phrase'] = 'Secret phrase is required for secret phrase distributions.'

        if mint_link_count and method != PoapDistribution.METHOD_MINT_LINK:
            errors['mint_link_count'] = 'Mint links can only be generated for mint-link distributions.'

        if starts_at and ends_at and ends_at <= starts_at:
            errors['ends_at'] = 'End time must be after start time.'

        if starts_at and mint_link_expires_at and mint_link_expires_at <= starts_at:
            errors['mint_link_expires_at'] = 'Expiration must be after start time.'

        if max_claims is not None and self.instance.pk and max_claims < self.instance.claimed_count:
            errors['max_claims'] = f'Max claims cannot be lower than the current claimed count ({self.instance.claimed_count}).'

        if mint_link_count:
            requested_claims = mint_link_count * mint_link_max_uses
            claimed_count = getattr(self.instance, 'claimed_count', 0)
            if max_claims is not None and requested_claims > max_claims - claimed_count:
                errors['mint_link_count'] = f'Only {max_claims - claimed_count} claim slots remain on this distribution.'

            drop = cleaned_data.get('drop')
            if drop and drop.max_claims is not None:
                drop_claimed_count = drop.claims.filter(user__isnull=False).count()
                remaining_drop_claims = drop.max_claims - drop_claimed_count
                if requested_claims > remaining_drop_claims:
                    errors['mint_link_count'] = f'Only {remaining_drop_claims} claim slots remain on this POAP.'

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        secret_phrase = (self.cleaned_data.get('secret_phrase') or '').strip()
        if instance.method == PoapDistribution.METHOD_SECRET:
            if secret_phrase:
                instance.secret_hash = hash_secret(secret_phrase)
        else:
            instance.secret_hash = ''

        if commit:
            instance.save()
            self.save_m2m()
        return instance


class PoapDistributionInline(admin.TabularInline):
    model = PoapDistribution
    form = PoapDistributionAdminForm
    extra = 0
    fields = ('method', 'active', 'starts_at', 'ends_at', 'max_claims', 'secret_phrase', 'claimed_count')
    readonly_fields = ('claimed_count',)


class PoapClaimInline(admin.TabularInline):
    model = PoapClaim
    extra = 0
    fields = ('user', 'claim_method', 'source', 'claimed_at', 'legacy_wallet_address', 'legacy_email')
    readonly_fields = ('claimed_at',)
    autocomplete_fields = ('user',)
    show_change_link = True


@admin.register(PoapDrop)
class PoapDropAdmin(CloudinaryUploadMixin, admin.ModelAdmin):
    form = PoapDropAdminForm
    cloudinary_upload_fields = {
        'artwork_url': {
            'public_id_field': 'artwork_public_id',
            'folder': 'tally/poaps',
        },
    }

    list_display = ('title', 'status', 'event_start_at', 'max_claims', 'legacy_poap_id', 'created_at')
    list_filter = ('status', 'event_start_at')
    search_fields = ('title', 'description', 'slug', 'legacy_poap_id')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'artwork_public_id')
    autocomplete_fields = ('created_by',)
    inlines = [PoapDistributionInline, PoapClaimInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'status', 'created_by'),
        }),
        ('Artwork', {
            'fields': ('artwork_url',),
            'description': 'Upload POAP artwork directly or paste a Cloudinary URL.',
        }),
        ('Event', {
            'fields': ('event_start_at', 'event_end_at'),
        }),
        ('Claiming', {
            'fields': ('max_claims', 'discord_role_id'),
        }),
        ('Legacy import', {
            'fields': ('legacy_poap_id',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(PoapDistribution)
class PoapDistributionAdmin(admin.ModelAdmin):
    form = PoapDistributionAdminForm
    list_display = ('drop', 'method', 'active', 'starts_at', 'ends_at', 'max_claims', 'claimed_count')
    list_filter = ('method', 'active')
    search_fields = ('drop__title', 'drop__slug')
    readonly_fields = ('claimed_count', 'created_at', 'updated_at')
    autocomplete_fields = ('drop',)
    fieldsets = (
        (None, {
            'fields': ('drop', 'method', 'active'),
        }),
        ('Claim window and cap', {
            'fields': ('starts_at', 'ends_at', 'max_claims', 'claimed_count'),
        }),
        ('Secret phrase', {
            'fields': ('secret_phrase',),
            'description': 'Only used when method is Secret phrase. Existing phrases are stored hashed and cannot be viewed.',
        }),
        ('Mint links', {
            'fields': ('mint_link_count', 'mint_link_max_uses', 'mint_link_expires_at'),
            'description': 'Only used when method is Mint link. Generated URLs can be downloaded from the POAP mint links admin list.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        mint_link_count = form.cleaned_data.get('mint_link_count') or 0
        if not mint_link_count:
            return

        created = generate_mint_links(
            distribution=obj,
            count=mint_link_count,
            max_uses=form.cleaned_data.get('mint_link_max_uses') or 1,
            expires_at=form.cleaned_data.get('mint_link_expires_at'),
        )
        messages.success(request, f'Generated {len(created)} mint link(s).')


@admin.register(PoapMintLink)
class PoapMintLinkAdmin(admin.ModelAdmin):
    list_display = ('distribution', 'claim_url', 'max_uses', 'used_count', 'expires_at', 'created_at')
    list_filter = ('expires_at',)
    search_fields = ('distribution__drop__title', 'distribution__drop__slug')
    readonly_fields = ('claim_url', 'token_hash', 'token_ciphertext', 'used_count', 'created_at', 'updated_at')
    autocomplete_fields = ('distribution',)
    actions = ('download_selected_claim_urls',)
    fieldsets = (
        (None, {
            'fields': ('distribution', 'max_uses', 'expires_at'),
        }),
        ('Generated claim link', {
            'fields': ('claim_url', 'token_hash', 'token_ciphertext', 'used_count'),
            'description': 'The token is generated automatically when a mint link is created.',
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        generated_token = ''
        if not obj.token_hash:
            generated_token = PoapMintLink.generate_token()
            obj.token_hash = hash_token(generated_token)
            obj.token_ciphertext = encrypt_token(generated_token)

        super().save_model(request, obj, form, change)

        if generated_token:
            messages.success(request, f'Mint link generated: {self._claim_url_from_token(generated_token)}')

    @admin.display(description='Claim URL')
    def claim_url(self, obj):
        token = decrypt_token(obj.token_ciphertext)
        if not token:
            return ''
        return self._claim_url_from_token(token)

    @admin.action(description='Download selected claim URLs')
    def download_selected_claim_urls(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="poap-mint-links.csv"'
        writer = csv.writer(response)
        writer.writerow(['drop', 'distribution_id', 'mint_link_id', 'claim_url', 'max_uses', 'used_count', 'expires_at'])
        for link in queryset.select_related('distribution__drop'):
            token = decrypt_token(link.token_ciphertext)
            writer.writerow([
                link.distribution.drop.title,
                link.distribution_id,
                link.id,
                self._claim_url_from_token(token) if token else '',
                link.max_uses,
                link.used_count,
                link.expires_at.isoformat() if link.expires_at else '',
            ])
        return response

    def _claim_url_from_token(self, token):
        frontend_url = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        if not frontend_url:
            return f'/#/claim/poap/{token}'
        return f'{frontend_url}/#/claim/poap/{token}'


@admin.register(PoapClaim)
class PoapClaimAdmin(admin.ModelAdmin):
    list_display = ('drop', 'user', 'claim_method', 'source', 'claimed_at')
    list_filter = ('claim_method', 'source', 'claimed_at')
    search_fields = (
        'drop__title', 'drop__slug', 'user__email', 'user__name', 'user__address',
        'legacy_wallet_address', 'legacy_email', 'legacy_external_id',
    )
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('drop', 'user', 'distribution', 'mint_link', 'import_batch')


@admin.register(PoapImportBatch)
class PoapImportBatchAdmin(admin.ModelAdmin):
    list_display = ('source_name', 'file_name', 'total_rows', 'imported_count', 'matched_count', 'unmatched_count', 'error_count', 'created_at')
    search_fields = ('source_name', 'file_name')
    readonly_fields = ('created_at', 'updated_at', 'errors')
    autocomplete_fields = ('created_by',)
