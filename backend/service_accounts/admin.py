import re

from django import forms
from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.contrib.admin.widgets import AdminSplitDateTime
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import ServiceAccount, ServiceAccountToken


class ServiceAccountTokenIssueForm(forms.Form):
    scopes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text=(
            'Comma or whitespace separated scopes, e.g. '
            'ai_review:read ai_review:propose.'
        ),
    )
    expires_at = forms.SplitDateTimeField(
        required=False,
        widget=AdminSplitDateTime,
        help_text='Leave blank for a token that never expires.',
    )

    def clean_scopes(self):
        raw_scopes = re.split(r'[\s,]+', self.cleaned_data['scopes'].strip())
        scopes = []
        seen = set()
        for scope in raw_scopes:
            if scope and scope not in seen:
                scopes.append(scope)
                seen.add(scope)
        if not scopes:
            raise forms.ValidationError('Enter at least one scope.')
        return scopes

    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        if expires_at is not None and expires_at <= timezone.now():
            raise forms.ValidationError('Expiry must be in the future.')
        return expires_at


@admin.register(ServiceAccount)
class ServiceAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'issue_token_link')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at', 'issue_token_link')

    def get_urls(self):
        opts = self.model._meta
        custom_urls = [
            path(
                '<path:object_id>/issue-token/',
                self.admin_site.admin_view(self.issue_token_view),
                name=f'{opts.app_label}_{opts.model_name}_issue_token',
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description='Issue token')
    def issue_token_link(self, obj):
        if obj is None or obj.pk is None:
            return 'Save this service account before issuing tokens.'
        url = reverse(
            'admin:service_accounts_serviceaccount_issue_token',
            args=[obj.pk],
            current_app=self.admin_site.name,
        )
        return format_html('<a class="button" href="{}">Issue token</a>', url)

    def issue_token_view(self, request, object_id):
        account = self.get_object(request, unquote(object_id))
        if account is None:
            raise Http404('Service account not found.')
        if not self.has_change_permission(request, account):
            raise PermissionDenied

        form = ServiceAccountTokenIssueForm(
            request.POST or None,
            initial={'scopes': 'ai_review:read ai_review:propose'},
        )
        token = None
        plaintext = None

        if request.method == 'POST' and form.is_valid():
            token, plaintext = ServiceAccountToken.issue(
                account,
                form.cleaned_data['scopes'],
                expires_at=form.cleaned_data['expires_at'],
            )

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'original': account,
            'title': f'Issue token for {account.name}',
            'account': account,
            'form': form,
            'token': token,
            'plaintext': plaintext,
            'media': self.media + form.media,
            'account_change_url': reverse(
                'admin:service_accounts_serviceaccount_change',
                args=[account.pk],
                current_app=self.admin_site.name,
            ),
            'token_changelist_url': reverse(
                'admin:service_accounts_serviceaccounttoken_changelist',
                current_app=self.admin_site.name,
            ),
        }
        if token is not None:
            context['token_change_url'] = reverse(
                'admin:service_accounts_serviceaccounttoken_change',
                args=[token.pk],
                current_app=self.admin_site.name,
            )
        return TemplateResponse(
            request,
            'admin/service_accounts/serviceaccount/issue_token.html',
            context,
        )


@admin.register(ServiceAccountToken)
class ServiceAccountTokenAdmin(admin.ModelAdmin):
    list_display = (
        'identifier', 'service_account', 'scopes',
        'expires_at', 'revoked_at', 'last_used_at',
    )
    list_filter = ('service_account',)
    actions = ['revoke_tokens']

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        # Tokens are issued via the issue_service_account_token command so
        # the plaintext is printed exactly once and the digest is never
        # hand-edited.
        return False

    @admin.action(description='Revoke selected tokens')
    def revoke_tokens(self, request, queryset):
        count = queryset.filter(revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )
        self.message_user(request, f'Revoked {count} token(s).')
