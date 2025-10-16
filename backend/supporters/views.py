from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Supporter
from users.serializers import SupporterSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_supporter_view(request):
    """
    Allow authenticated users to become supporters.
    """
    user = request.user

    # Check if user already has a supporter profile
    if hasattr(user, 'supporter'):
        return Response(
            {'message': 'You are already a supporter!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create supporter profile
    supporter = Supporter.objects.create(user=user)
    serializer = SupporterSerializer(supporter)

    return Response({
        'message': 'Successfully joined as a supporter!',
        'supporter': serializer.data
    }, status=status.HTTP_201_CREATED)
