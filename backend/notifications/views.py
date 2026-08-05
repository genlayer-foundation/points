from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from validators.permissions import IsCronToken

from . import services
from . import telegram as telegram_delivery
from .serializers import (
    LightNotificationSerializer,
    NotificationSerializer,
    WhatsNewAnnouncementSerializer,
    WhatsNewMarkSeenSerializer,
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return LightNotificationSerializer
        return NotificationSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['use_light_serializers'] = self.action == 'list'
        return context

    def get_queryset(self):
        user = self.request.user
        queryset = services.annotate_read_state(services.feed_for(user), user)

        unread = self.request.query_params.get('unread')
        if unread and unread.lower() in ('1', 'true', 'yes'):
            queryset = queryset.filter(services.UNREAD_Q)

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Strictly reverse-chronological so pagination stays stable while
        # items are marked read; unread state is styling, not ordering.
        return queryset.order_by('-created_at', '-id')

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        user = request.user
        count = (
            services.annotate_read_state(services.feed_for(user), user)
            .filter(services.UNREAD_Q)
            .count()
        )
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        services.mark_notification_read(notification, request.user)
        notification.receipt_read = True
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated = services.mark_all_read(request.user)
        return Response({'updated': updated})

    @action(
        detail=False,
        methods=['post'],
        url_path='telegram/deliver',
        permission_classes=[IsCronToken],
        authentication_classes=[],
    )
    def telegram_deliver(self, request):
        """Drain the Telegram outbox. Cron-triggered (X-Cron-Token)."""
        try:
            limit = int(request.data.get('limit', telegram_delivery.DEFAULT_RUN_LIMIT))
        except (TypeError, ValueError):
            limit = telegram_delivery.DEFAULT_RUN_LIMIT
        return Response(telegram_delivery.deliver_pending(limit=limit))


class WhatsNewPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class WhatsNewAnnouncementViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = WhatsNewAnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = WhatsNewPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['use_light_serializers'] = self.action == 'list'
        return context

    def get_queryset(self):
        preview = self.request.query_params.get('preview')
        if preview and preview.lower() in ('1', 'true', 'yes'):
            return services.seen_whats_new_for(self.request.user)
        return services.unseen_whats_new_for(self.request.user)

    @action(detail=False, methods=['get'], url_path='unseen-count')
    def unseen_count(self, request):
        return Response({'count': services.whats_new_unseen_count(request.user)})

    @action(detail=False, methods=['post'], url_path='mark-seen')
    def mark_seen(self, request):
        serializer = WhatsNewMarkSeenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = services.mark_whats_new_seen(
            request.user,
            serializer.validated_data['ids'],
            action=serializer.validated_data['action'],
        )
        return Response({
            'updated': updated,
            'count': services.whats_new_unseen_count(request.user),
        })
