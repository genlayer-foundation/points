from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Min
from .models import Builder
from users.serializers import BuilderSerializer
from contributions.models import Contribution


class BuilderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Builder profiles.
    """
    queryset = Builder.objects.all()
    serializer_class = BuilderSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Allow read-only access without authentication for public endpoints.
        """
        if self.action in ['newest_builders']:
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def my_profile(self, request):
        """
        Get or update current user's builder profile.
        """
        if request.method == 'GET':
            try:
                builder = Builder.objects.get(user=request.user)
                serializer = self.get_serializer(builder)
                return Response(serializer.data)
            except Builder.DoesNotExist:
                return Response(
                    {'detail': 'Builder profile not found for current user.'},
                    status=status.HTTP_404_NOT_FOUND
                )

        elif request.method == 'PATCH':
            builder, created = Builder.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(builder, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='newest')
    def newest_builders(self, request):
        """
        Get builders sorted by when they completed the builder journey (newest first).
        Returns the most recent builders to join.
        Returns minimal user data for performance.
        """
        limit = int(request.GET.get('limit', 5))

        # Get builders ordered by creation date (when they completed the journey)
        builders = (
            Builder.objects
            .select_related('user')
            .order_by('-created_at')[:limit]
        )

        # Build result with minimal user data
        result = []
        for builder in builders:
            result.append({
                'id': builder.user.id,
                'address': builder.user.address,
                'name': builder.user.name,
                'profile_image_url': builder.user.profile_image_url,
                'created_at': builder.created_at
            })

        return Response(result)