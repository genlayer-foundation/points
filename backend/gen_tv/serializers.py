from rest_framework import serializers

from .models import Stream, StreamCategory


class StreamCategorySerializer(serializers.ModelSerializer):
    """Detailed stream category exposed for Gen TV filters."""

    group_display = serializers.CharField(source='get_group_display', read_only=True)

    class Meta:
        model = StreamCategory
        fields = [
            'id',
            'name',
            'slug',
            'group',
            'group_display',
            'description',
            'display_order',
        ]
        read_only_fields = fields


class LightStreamCategorySerializer(serializers.ModelSerializer):
    """Nested category payload for stream cards."""

    group_display = serializers.CharField(source='get_group_display', read_only=True)

    class Meta:
        model = StreamCategory
        fields = ['id', 'name', 'slug', 'group', 'group_display']
        read_only_fields = fields


class ActiveDetailedCategoryMixin:
    def get_detailed_category(self, obj):
        category = obj.detailed_category
        if not category or not category.is_active:
            return None
        return LightStreamCategorySerializer(category).data


class LightStreamSerializer(ActiveDetailedCategoryMixin, serializers.ModelSerializer):
    """Minimal stream payload for list views."""

    status = serializers.CharField(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    detailed_category = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'image_url',
            'url',
            'starts_at',
            'ends_at',
            'category',
            'category_display',
            'detailed_category',
            'status',
            'updated_at',
        ]
        read_only_fields = fields


class StreamSerializer(ActiveDetailedCategoryMixin, serializers.ModelSerializer):
    """Full stream payload for detail views."""

    status = serializers.CharField(read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    detailed_category = serializers.SerializerMethodField()

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
            'category_display',
            'detailed_category',
            'status',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields
