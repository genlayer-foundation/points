from django.contrib import admin
from django.utils import timezone

from .models import ServiceAccount, ServiceAccountToken


@admin.register(ServiceAccount)
class ServiceAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')


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
