from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from . import services
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

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
