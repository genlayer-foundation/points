from rest_framework import serializers
from .models import GlobalLeaderboardMultiplier, LeaderboardEntry
from contributions.serializers import ContributionTypeSerializer
from users.serializers import UserSerializer


class GlobalLeaderboardMultiplierSerializer(serializers.ModelSerializer):
    contribution_type_details = ContributionTypeSerializer(source='contribution_type', read_only=True)
    
    class Meta:
        model = GlobalLeaderboardMultiplier
        fields = ['id', 'contribution_type', 'contribution_type_details', 'multiplier_value', 
                  'valid_from', 'description', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaderboardEntrySerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = LeaderboardEntry
        fields = ['id', 'user', 'user_details', 'total_points', 'rank', 'created_at', 'updated_at']
        read_only_fields = ['id', 'total_points', 'rank', 'created_at', 'updated_at']