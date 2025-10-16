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
    user_details = serializers.SerializerMethodField()
    referral_points = serializers.SerializerMethodField()

    class Meta:
        model = LeaderboardEntry
        fields = ['id', 'user', 'user_details', 'type', 'total_points', 'rank', 'graduation_date', 'referral_points', 'created_at', 'updated_at']
        read_only_fields = ['id', 'type', 'total_points', 'rank', 'graduation_date', 'referral_points', 'created_at', 'updated_at']

    def get_user_details(self, obj):
        """
        Returns user details using lightweight or full serializer based on context.
        Use lightweight serializer for list views to avoid returning unnecessary data.
        """
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            from utils.serializers import LightUserSerializer
            return LightUserSerializer(obj.user).data
        return UserSerializer(obj.user, context=self.context).data

    def get_referral_points(self, obj):
        """Get user's referral points if they exist."""
        from .models import ReferralPoints
        try:
            rp = obj.user.referral_points
            return {
                'builder_points': rp.builder_points,
                'validator_points': rp.validator_points
            }
        except ReferralPoints.DoesNotExist:
            return None
