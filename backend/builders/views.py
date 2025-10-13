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
        Get builders sorted by their first builder contribution date (newest first).
        Returns the 5 most recent builders to join.
        Returns minimal user data for performance.
        """
        limit = int(request.GET.get('limit', 5))

        # Get all builder category contributions, excluding 'Builder Welcome'
        builder_contributions = (
            Contribution.objects
            .filter(contribution_type__category__slug='builder')
            .exclude(contribution_type__slug='builder-welcome')
            .values('user', 'user__address', 'user__name', 'user__profile_image_url')
            .annotate(
                first_contribution_date=Min('contribution_date')
            )
            .order_by('-first_contribution_date')[:limit]
        )

        # Build result with minimal user data
        result = []
        for contribution in builder_contributions:
            result.append({
                'id': contribution['user'],
                'address': contribution['user__address'],
                'name': contribution['user__name'],
                'profile_image_url': contribution['user__profile_image_url'],
                'created_at': contribution['first_contribution_date']
            })

        return Response(result)