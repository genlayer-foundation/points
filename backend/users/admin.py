from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Validator
from contributions.models import Contribution


class ContributionInline(admin.TabularInline):
    model = Contribution
    extra = 0  # Don't show empty rows
    fields = ('contribution_type', 'points', 'contribution_date', 'evidence_link', 'multiplier_at_creation', 'frozen_global_points')
    readonly_fields = ('multiplier_at_creation', 'frozen_global_points', 'evidence_link')
    can_delete = True
    show_change_link = True
    verbose_name = "Contribution"
    verbose_name_plural = "Contributions"
    ordering = ('-created_at', '-contribution_date')  # Most recent contributions first, based on creation date
    
    def evidence_link(self, obj):
        """Display a link to add/edit evidence for this contribution."""
        from django.utils.html import format_html
        from django.urls import reverse
        
        if obj and obj.id:
            change_url = reverse('admin:contributions_contribution_change', args=[obj.id])
            count = obj.evidence_items.count()
            if count > 0:
                return format_html('<a href="{}#evidence_items-group">View/Edit {} Evidence Item{}</a>', 
                               change_url, count, 's' if count > 1 else '')
            else:
                return format_html('<a href="{}#evidence_items-group">Add Evidence</a>', change_url)
        return '-'
    evidence_link.short_description = 'Evidence'


class ValidatorInline(admin.StackedInline):
    model = Validator
    extra = 0  # Don't show empty rows
    max_num = 1  # Only one validator per user
    fields = ('node_version',)
    verbose_name = "Validator Information"
    verbose_name_plural = "Validator Information"
    can_delete = False  # Don't allow deletion through inline


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'is_staff', 'is_active', 'visible', 'address')
    list_filter = ('is_staff', 'is_active', 'visible')
    search_fields = ('email', 'name', 'address')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('name', 'address')}),
        (_('Visibility'), {'fields': ('visible',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'name', 'address', 'visible'),
        }),
    )
    
    inlines = [ValidatorInline, ContributionInline]
