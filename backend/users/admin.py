from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User
from contributions.models import Contribution


class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 0  # Don't show empty rows
    fields = ('contribution_type', 'points', 'contribution_date', 'evidence_url', 'multiplier_at_creation', 'frozen_global_points')
    readonly_fields = ('multiplier_at_creation', 'frozen_global_points')
    can_delete = True
    show_change_link = True
    verbose_name = "Contribution"
    verbose_name_plural = "Contributions"
    ordering = ('-contribution_date',)  # Most recent contributions first


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'name', 'address')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('name', 'address')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'name', 'address'),
        }),
    )
    
    inlines = [ContributionInline]
