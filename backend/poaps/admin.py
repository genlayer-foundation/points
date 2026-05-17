from django.contrib import admin

from utils.admin_mixins import CloudinaryUploadMixin

from .models import PoapClaim, PoapDistribution, PoapDrop, PoapImportBatch, PoapMintLink


class PoapDistributionInline(admin.TabularInline):
    model = PoapDistribution
    extra = 0
    fields = ('method', 'active', 'starts_at', 'ends_at', 'max_claims', 'claimed_count')
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
    list_display = ('drop', 'method', 'active', 'starts_at', 'ends_at', 'max_claims', 'claimed_count')
    list_filter = ('method', 'active')
    search_fields = ('drop__title', 'drop__slug')
    readonly_fields = ('claimed_count', 'created_at', 'updated_at')
    autocomplete_fields = ('drop',)


@admin.register(PoapMintLink)
class PoapMintLinkAdmin(admin.ModelAdmin):
    list_display = ('distribution', 'max_uses', 'used_count', 'expires_at', 'created_at')
    list_filter = ('expires_at',)
    search_fields = ('distribution__drop__title', 'distribution__drop__slug')
    readonly_fields = ('token_hash', 'token_ciphertext', 'used_count', 'created_at', 'updated_at')


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
