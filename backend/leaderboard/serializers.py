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
    active_validators_count = serializers.SerializerMethodField()

    class Meta:
        model = LeaderboardEntry
        fields = ['id', 'user', 'user_details', 'type', 'total_points', 'rank', 'graduation_date', 'referral_points', 'active_validators_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'type', 'total_points', 'rank', 'graduation_date', 'referral_points', 'active_validators_count', 'created_at', 'updated_at']

    def get_user_details(self, obj):
        """
        Returns user details using lightweight or full serializer based on context.
        Use lightweight serializer for list views to avoid returning unnecessary data.
        """
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            from users.serializers import LightUserSerializer
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

    def get_active_validators_count(self, obj):
        """
        Get count of active validator wallets for this user's validator.
        Returns null if user has no validator wallets linked, otherwise returns the active count.
        Uses annotated values from queryset to avoid N+1 queries.
        """
        # Use annotated values if available (from optimized queryset)
        if hasattr(obj, '_total_validators_count') and hasattr(obj, '_active_validators_count'):
            # If no validator wallets at all, return null
            if obj._total_validators_count == 0:
                return None
            return obj._active_validators_count

        # Fallback to query if annotation not available
        if not hasattr(obj.user, 'validator') or obj.user.validator is None:
            return None
        from validators.models import ValidatorWallet
        total = ValidatorWallet.objects.filter(operator=obj.user.validator).count()
        if total == 0:
            return None
        return ValidatorWallet.objects.filter(
            operator=obj.user.validator,
            status='active'
        ).count()
