from django import forms
from django.contrib import admin

from notifications import services as notification_services
from notifications.admin_mixins import BroadcastNotificationAdminMixin
from utils.admin_mixins import CloudinaryUploadMixin

from .models import Partner


class PartnerAdminForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        show_in_overview = cleaned_data.get('show_in_overview')
        overview_logo_url = cleaned_data.get('overview_logo_url')

        if overview_logo_url is None and self.instance and self.instance.pk:
            overview_logo_url = self.instance.overview_logo_url

        uploaded_file = self.files.get('overview_logo_url_upload')
        clears_existing_file = self.data.get('overview_logo_url_clear')
        has_overview_image = bool(overview_logo_url) and not clears_existing_file

        if show_in_overview and not has_overview_image and not uploaded_file:
            message = "Provide an overview logo URL or upload an overview image before showing this partner in the overview."
            if 'overview_logo_url' in self.fields:
                self.add_error('overview_logo_url', message)
            else:
                raise forms.ValidationError(message)

        return cleaned_data


@admin.register(Partner)
class PartnerAdmin(BroadcastNotificationAdminMixin, CloudinaryUploadMixin, admin.ModelAdmin):
    form = PartnerAdminForm
    broadcast_event_slug = 'partner.published'
    broadcast_service = staticmethod(notification_services.broadcast_partner)
    broadcast_eligible = staticmethod(lambda obj: obj.is_active)
    broadcast_ineligible_reason = 'the partner is inactive'

    cloudinary_upload_fields = {
        'logo_url': {
            'public_id_field': 'logo_public_id',
            'folder': 'tally/partners',
        },
        'overview_logo_url': {
            'public_id_field': 'overview_logo_public_id',
            'folder': 'tally/partners/overview',
        },
    }

    list_display = (
        'name',
        'display_order',
        'is_active',
        'show_in_overview',
        'website_url',
        'created_at',
    )
    list_editable = ('display_order', 'is_active', 'show_in_overview')
    list_filter = ('is_active', 'show_in_overview')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'logo_public_id', 'overview_logo_public_id')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'is_active'),
        }),
        ('Ecosystem image', {
            'fields': ('logo_url',),
            'description': 'Base partner image used on the ecosystem partners page.',
        }),
        ('Overview marquee', {
            'fields': ('show_in_overview', 'overview_logo_url'),
            'description': 'Partners shown in the overview marquee must have this overview-specific image.',
        }),
        ('URLs', {
            'fields': ('website_url', 'url'),
        }),
        ('Display', {
            'fields': ('display_order',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
