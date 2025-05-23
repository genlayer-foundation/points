from django.contrib import admin
from .models import Nonce


@admin.register(Nonce)
class NonceAdmin(admin.ModelAdmin):
    list_display = ('value', 'created_at', 'expires_at', 'used')
    list_filter = ('used',)
    search_fields = ('value',)
    readonly_fields = ('created_at',)
    
    def has_change_permission(self, request, obj=None):
        # Nonces should not be changed once created
        return False