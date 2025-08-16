from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Validator
from users.serializers import ValidatorSerializer


class ValidatorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Validator profiles.
    """
    queryset = Validator.objects.all()
    serializer_class = ValidatorSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def my_profile(self, request):
        """
        Get or update current user's validator profile.
        """
        if request.method == 'GET':
            try:
                validator = Validator.objects.get(user=request.user)
                serializer = self.get_serializer(validator)
                return Response(serializer.data)
            except Validator.DoesNotExist:
                return Response(
                    {'detail': 'Validator profile not found for current user.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif request.method == 'PATCH':
            validator, created = Validator.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(validator, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)