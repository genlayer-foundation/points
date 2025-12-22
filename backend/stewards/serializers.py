from rest_framework import serializers
from .models import Steward, WorkingGroup, WorkingGroupParticipant
from users.models import User
from users.serializers import UserSerializer


class StewardSerializer(serializers.ModelSerializer):
    """
    Serializer for Steward model.
    """
    class Meta:
        model = Steward
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class WorkingGroupParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer for working group participant with user details and points.
    """
    id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.name', read_only=True)
    address = serializers.CharField(source='user.address', read_only=True)
    profile_image_url = serializers.URLField(source='user.profile_image_url', read_only=True)
    builder_points = serializers.SerializerMethodField()
    validator_points = serializers.SerializerMethodField()
    steward = serializers.SerializerMethodField()
    validator = serializers.SerializerMethodField()
    builder = serializers.SerializerMethodField()
    has_validator_waitlist = serializers.SerializerMethodField()
    has_builder_welcome = serializers.SerializerMethodField()

    class Meta:
        model = WorkingGroupParticipant
        fields = [
            'id', 'name', 'address', 'profile_image_url',
            'builder_points', 'validator_points',
            'steward', 'validator', 'builder',
            'has_validator_waitlist', 'has_builder_welcome'
        ]

    def get_builder_points(self, obj):
        from leaderboard.models import LeaderboardEntry
        entry = LeaderboardEntry.objects.filter(user=obj.user, type='builder').first()
        return entry.total_points if entry else 0

    def get_validator_points(self, obj):
        from leaderboard.models import LeaderboardEntry
        entry = LeaderboardEntry.objects.filter(user=obj.user, type='validator').first()
        return entry.total_points if entry else 0

    def get_steward(self, obj):
        return hasattr(obj.user, 'steward') and obj.user.steward is not None

    def get_validator(self, obj):
        return hasattr(obj.user, 'validator') and obj.user.validator is not None

    def get_builder(self, obj):
        return hasattr(obj.user, 'builder') and obj.user.builder is not None

    def get_has_validator_waitlist(self, obj):
        from contributions.models import Contribution
        return Contribution.objects.filter(
            user=obj.user,
            contribution_type__slug='validator-waitlist'
        ).exists()

    def get_has_builder_welcome(self, obj):
        from contributions.models import Contribution
        return Contribution.objects.filter(
            user=obj.user,
            contribution_type__slug='builder-welcome'
        ).exists()


class WorkingGroupListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing working groups with participant count.
    """
    participant_count = serializers.IntegerField(read_only=True)
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = WorkingGroup
        fields = ['id', 'name', 'participant_count', 'is_member', 'created_at']

    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(user=request.user).exists()
        return False


class WorkingGroupDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for working group detail with participants and conditional discord_url.
    """
    participant_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    discord_url = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta:
        model = WorkingGroup
        fields = ['id', 'name', 'discord_url', 'participant_count', 'is_member', 'participants', 'created_at']

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.participants.filter(user=request.user).exists()
        return False

    def get_discord_url(self, obj):
        """Only show discord_url if user is a member or a steward."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        is_member = obj.participants.filter(user=request.user).exists()
        is_steward = hasattr(request.user, 'steward')

        if is_member or is_steward:
            return obj.discord_url
        return None

    def get_participants(self, obj):
        participants = obj.participants.select_related('user').all()
        return WorkingGroupParticipantSerializer(participants, many=True).data


class WorkingGroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a working group.
    """
    class Meta:
        model = WorkingGroup
        fields = ['name', 'discord_url']
