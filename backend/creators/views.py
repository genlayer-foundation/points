from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Creator
from users.serializers import CreatorSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_creator_view(request):
    """
    Allow authenticated users to join the community program.
    """
    user = request.user

    if hasattr(user, 'creator'):
        return Response(
            {'message': 'You are already a community member!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    creator = Creator.objects.create(user=user)
    serializer = CreatorSerializer(creator)

    return Response({
        'message': 'Successfully joined the community!',
        'creator': serializer.data
    }, status=status.HTTP_201_CREATED)
