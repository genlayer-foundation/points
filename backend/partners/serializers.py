from rest_framework import serializers

from .models import Partner


class LightPartnerSerializer(serializers.ModelSerializer):
    """Minimal partner payload for list views."""

    class Meta:
        model = Partner
        fields = ['id', 'name', 'slug', 'logo_url', 'website_url']
        read_only_fields = fields


class PartnerSerializer(serializers.ModelSerializer):
    """Full partner payload for detail views."""

    class Meta:
        model = Partner
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'logo_url',
            'website_url',
            'url',
            'display_order',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
