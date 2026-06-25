from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from creators import community_journey as cj
from .models import Creator
from users.serializers import CreatorSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_creator_view(request):
    """
    Legacy creator join endpoint.

    Keep the route for old clients, but do not let it bypass the community
    journey. The Creator row is granted only after the journey has started and
    all required steps are complete.
    """
    user = request.user

    journey = cj.journey_status(user)
    if not journey['started']:
        return Response(
            {
                'error': 'not_started',
                'missing_steps': ['start'],
                'message': 'Start the community journey first.',
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    if not journey['complete']:
        return Response(
            {
                'error': 'incomplete',
                'missing_steps': journey['missing_steps'],
                'message': 'Complete all community journey steps first.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if hasattr(user, 'creator'):
        serializer = CreatorSerializer(user.creator)
        return Response({
            'message': 'You are already a community member!',
            'creator': serializer.data,
        }, status=status.HTTP_200_OK)

    creator = Creator.objects.create(user=user)
    from leaderboard.models import update_user_leaderboard_entries
    update_user_leaderboard_entries(user)
    serializer = CreatorSerializer(creator)

    return Response({
        'message': 'Successfully joined the community!',
        'creator': serializer.data
    }, status=status.HTTP_201_CREATED)
