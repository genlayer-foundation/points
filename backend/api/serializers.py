from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Action, Participant, Badge, Leaderboard, LeaderboardEntry


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = ['id', 'name', 'description', 'multiplier', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class BadgeSerializer(serializers.ModelSerializer):
    action_name = serializers.ReadOnlyField(source='action.name')
    
    class Meta:
        model = Badge
        fields = ['id', 'participant', 'action', 'action_name', 'points', 'notes', 
                  'evidence_url', 'multiplier_at_issuance', 'created_at', 'updated_at']
        read_only_fields = ['id', 'multiplier_at_issuance', 'created_at', 'updated_at']


class ParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    badges_count = serializers.SerializerMethodField()
    total_points = serializers.ReadOnlyField()
    
    class Meta:
        model = Participant
        fields = ['id', 'user', 'display_name', 'bio', 'avatar', 
                  'badges_count', 'total_points', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_badges_count(self, obj):
        return obj.badges.count()


class ParticipantCreateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = Participant
        fields = ['username', 'email', 'password', 'display_name', 'bio', 'avatar']
    
    def create(self, validated_data):
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(username=username, email=email, password=password)
        return Participant.objects.create(user=user, **validated_data)


class ParticipantDetailSerializer(ParticipantSerializer):
    badges = BadgeSerializer(many=True, read_only=True)
    
    class Meta(ParticipantSerializer.Meta):
        fields = ParticipantSerializer.Meta.fields + ['badges']


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    participant_name = serializers.ReadOnlyField(source='participant.display_name')
    username = serializers.ReadOnlyField(source='participant.user.username')
    
    class Meta:
        model = LeaderboardEntry
        fields = ['id', 'position', 'participant', 'participant_name', 'username', 'total_points']
        read_only_fields = ['id']


class LeaderboardSerializer(serializers.ModelSerializer):
    entries = LeaderboardEntrySerializer(many=True, read_only=True)
    
    class Meta:
        model = Leaderboard
        fields = ['id', 'name', 'snapshot_date', 'description', 'entries']
        read_only_fields = ['id', 'snapshot_date']


class LeaderboardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leaderboard
        fields = ['name', 'description']
    
    def create(self, validated_data):
        # Create a leaderboard
        leaderboard = Leaderboard.objects.create(**validated_data)
        
        # Get all participants and sort by total points
        participants = Participant.objects.all()
        sorted_participants = sorted(participants, key=lambda p: p.total_points, reverse=True)
        
        # Create entries for each participant
        for position, participant in enumerate(sorted_participants, 1):
            LeaderboardEntry.objects.create(
                leaderboard=leaderboard,
                participant=participant,
                position=position,
                total_points=participant.total_points
            )
        
        return leaderboard