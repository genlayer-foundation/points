from rest_framework import serializers

from .models import Stream


class LightStreamSerializer(serializers.ModelSerializer):
    """Minimal stream payload for list views."""

    status = serializers.CharField(read_only=True)

    class Meta:
        model = Stream
        fields = [
            'id',
            'title',
            'slug',
            'image_url',
            'url',
            'starts_at',
            'ends_at',
            'category',
            'status',
        ]
        read_only_fields = fields


class StreamSerializer(serializers.ModelSerializer):
    """Full stream payload for detail views."""

    status = serializers.CharField(read_only=True)

    class Meta:
        model = Stream
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'url',
            'image_url',
            'starts_at',
            'ends_at',
            'category',
            'status',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
