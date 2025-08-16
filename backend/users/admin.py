from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

from .models import User
from contributions.models import Contribution
from validators.admin import ValidatorInline
from builders.admin import BuilderInline
from stewards.admin import StewardInline
from validators.models import Validator
from builders.models import Builder
from stewards.models import Steward


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


# ValidatorInline removed - now in validators app


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
    
    inlines = [ContributionInline, ValidatorInline, BuilderInline, StewardInline]
    actions = ['set_as_builder', 'set_as_validator', 'set_as_steward']
    
    def set_as_builder(self, request, queryset):
        """Action to set selected users as builders."""
        count = 0
        for user in queryset:
            # Check if already a builder
            if hasattr(user, 'builder'):
                self.message_user(request, f"{user.email} is already a builder.", level=messages.WARNING)
                continue
            
            # Create builder profile
            Builder.objects.create(user=user)
            count += 1
        
        if count > 0:
            self.message_user(request, f"Successfully set {count} user(s) as builder(s).", level=messages.SUCCESS)
    set_as_builder.short_description = "Set selected users as builders"
    
    def set_as_validator(self, request, queryset):
        """Action to set selected users as validators."""
        count = 0
        for user in queryset:
            # Check if already a validator
            if hasattr(user, 'validator'):
                self.message_user(request, f"{user.email} is already a validator.", level=messages.WARNING)
                continue
            
            # Create validator profile
            Validator.objects.create(user=user)
            count += 1
        
        if count > 0:
            self.message_user(request, f"Successfully set {count} user(s) as validator(s).", level=messages.SUCCESS)
    set_as_validator.short_description = "Set selected users as validators"
    
    def set_as_steward(self, request, queryset):
        """Action to set selected users as stewards."""
        count = 0
        for user in queryset:
            # Check if already a steward
            if hasattr(user, 'steward'):
                self.message_user(request, f"{user.email} is already a steward.", level=messages.WARNING)
                continue
            
            # Create steward profile
            Steward.objects.create(user=user)
            count += 1
        
        if count > 0:
            self.message_user(request, f"Successfully set {count} user(s) as steward(s).", level=messages.SUCCESS)
    set_as_steward.short_description = "Set selected users as stewards"
