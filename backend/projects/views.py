from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.cloudinary_service import CloudinaryService

from .models import Project
from .serializers import (
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectProfileUpdateSerializer,
)


def _as_bool(value):
    if value is None:
        return None
    return str(value).lower() in {'1', 'true', 'yes', 'on'}


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only API for project profiles."""

    permission_classes = [permissions.AllowAny]
    pagination_class = None
    lookup_field = 'slug'

    def get_queryset(self):
        queryset = (
            Project.objects
            .filter(status=Project.STATUS_ACTIVE)
            .select_related('user')
            .prefetch_related(
                'participants',
                'related_contributions__user',
                'related_contributions__contribution_type',
                'related_contributions__evidence_items',
                'related_contributions__highlights',
            )
            .order_by('order', '-created_at')
        )
        show_in_overview = _as_bool(self.request.query_params.get('show_in_overview'))
        if show_in_overview is not None:
            queryset = queryset.filter(show_in_overview=show_in_overview)

        try:
            limit = int(self.request.query_params.get('limit', 0))
        except (TypeError, ValueError):
            limit = 0
        if limit > 0:
            queryset = queryset[:min(limit, 50)]

        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProjectDetailSerializer
        return ProjectListSerializer

    def ensure_project_editor(self, project):
        if not project.can_be_edited_by(self.request.user):
            raise PermissionDenied('You can only edit projects you own or participate in.')

    @action(detail=True, methods=['patch'], url_path='profile', permission_classes=[permissions.IsAuthenticated])
    def profile(self, request, slug=None):
        project = self.get_object()
        self.ensure_project_editor(project)

        serializer = ProjectProfileUpdateSerializer(instance=project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        project.refresh_from_db()
        response_serializer = ProjectDetailSerializer(project, context={'request': request})
        return Response(response_serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-image', permission_classes=[permissions.IsAuthenticated])
    def upload_image(self, request, slug=None):
        project = self.get_object()
        self.ensure_project_editor(project)

        image = request.FILES.get('image')
        image_type = request.data.get('image_type')
        field_config = {
            'logo': ('user_profile_image_url', 'user_profile_image_public_id', 'logos'),
            'desktop': ('hero_image_url', 'hero_image_public_id', 'desktop'),
            'tablet': ('hero_image_url_tablet', 'hero_image_tablet_public_id', 'tablet'),
            'mobile': ('hero_image_url_mobile', 'hero_image_mobile_public_id', 'mobile'),
        }.get(image_type)

        if not field_config:
            return Response({'error': 'Unknown image type.'}, status=status.HTTP_400_BAD_REQUEST)
        if not image:
            return Response({'error': 'Image file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not getattr(image, 'content_type', '').startswith('image/'):
            return Response({'error': 'Only image files are supported.'}, status=status.HTTP_400_BAD_REQUEST)

        url_field, public_id_field, folder_name = field_config
        old_public_id = getattr(project, public_id_field, '')

        try:
            result = CloudinaryService.upload_image(
                image,
                folder=f'tally/projects/{project.slug}/{folder_name}',
            )
            setattr(project, url_field, result['url'])
            setattr(project, public_id_field, result['public_id'])
            project.save(update_fields=[url_field, public_id_field, 'updated_at'])
            if old_public_id:
                CloudinaryService.delete_image(old_public_id)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'image_type': image_type,
            'field': url_field,
            'url': result['url'],
            'public_id': result['public_id'],
        })
