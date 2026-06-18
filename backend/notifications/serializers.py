from rest_framework import serializers

from .models import Notification, WhatsNewAnnouncement, WhatsNewAnnouncementSeen


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    is_broadcast = serializers.BooleanField(read_only=True)
    priority_label = serializers.CharField(source='get_priority_display', read_only=True)
    category_label = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'event_type',
            'category',
            'category_label',
            'priority',
            'priority_label',
            'title',
            'body',
            'link_url',
            'link_label',
            'payload',
            'is_broadcast',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields

    def get_is_read(self, obj):
        if obj.recipient_id is not None:
            return obj.read_at is not None
        return bool(getattr(obj, 'receipt_read', False))


class LightNotificationSerializer(NotificationSerializer):
    """List serializer: everything the feed UI renders, minus `payload`.

    The payload is channel-renderer data (ids/slugs for future email or
    Telegram delivery), not something list views need.
    """

    class Meta(NotificationSerializer.Meta):
        fields = [field for field in NotificationSerializer.Meta.fields if field != 'payload']
        read_only_fields = fields


class WhatsNewAnnouncementSerializer(serializers.ModelSerializer):
    audience_label = serializers.CharField(source='get_audience_display', read_only=True)

    class Meta:
        model = WhatsNewAnnouncement
        fields = [
            'id',
            'title',
            'body',
            'eyebrow',
            'link_url',
            'link_label',
            'image_url',
            'audience',
            'audience_label',
            'version',
        ]
        read_only_fields = fields


class WhatsNewMarkSeenSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )
    action = serializers.ChoiceField(
        choices=WhatsNewAnnouncementSeen.ACTION_CHOICES,
        default=WhatsNewAnnouncementSeen.ACTION_SEEN,
    )
