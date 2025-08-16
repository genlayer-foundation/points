from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Builder
from users.serializers import BuilderSerializer


class BuilderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Builder profiles.
    """
    queryset = Builder.objects.all()
    serializer_class = BuilderSerializer
    permission_classes = [IsAuthenticated]
    
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