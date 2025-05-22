from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer, UserCreateSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    Users with visible=False are excluded from the queryset,
    except for the authenticated user viewing their own profile.
    """
    queryset = User.objects.filter(visible=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]  # Allow read-only access without authentication
    
    def get_object(self):
        """
        Override to allow users to access their own profile
        even if they're marked as not visible.
        """
        obj = super().get_object()
        # If the user is accessing their own profile, allow it
        if self.request.user.is_authenticated and obj.id == self.request.user.id:
            return obj
        # Otherwise, enforce visibility rules
        if not obj.visible:
            self.permission_denied(self.request, message="User not found.")
        return obj
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create' and 'visible' in self.request.data:
            context['visible'] = self.request.data.get('visible')
        return context
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get the authenticated user's profile.
        Users can always see their own profile regardless of visibility setting.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """
        Register a new user.
        """
        visible = request.data.get('visible', True)
        serializer = UserCreateSerializer(data=request.data, context={'visible': visible})
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
