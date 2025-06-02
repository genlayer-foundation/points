from rest_framework import serializers
from .models import ContributionType, Contribution, Evidence
from users.serializers import UserSerializer
import decimal


class ContributionTypeSerializer(serializers.ModelSerializer):
    current_multiplier = serializers.SerializerMethodField()
    
    class Meta:
        model = ContributionType
        fields = ['id', 'name', 'description', 'min_points', 'max_points', 'current_multiplier', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_current_multiplier(self, obj):
        """Get the current multiplier value for this contribution type."""
        from leaderboard.models import GlobalLeaderboardMultiplier
        try:
            return float(GlobalLeaderboardMultiplier.get_current_multiplier_value(obj))
        except Exception:
            return 1.0


class ContributionSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    contribution_type_min_points = serializers.ReadOnlyField(source='contribution_type.min_points')
    contribution_type_max_points = serializers.ReadOnlyField(source='contribution_type.max_points')
    evidence_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Contribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name', 
                  'contribution_type_min_points', 'contribution_type_max_points', 'points', 
                  'frozen_global_points', 'multiplier_at_creation', 'contribution_date',
                  'evidence_items', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'frozen_global_points', 'created_at', 'updated_at']
        
    def get_evidence_items(self, obj):
        """Returns serialized evidence items for this contribution."""
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True, context=self.context).data
    
    def to_representation(self, instance):
        """Override to_representation to handle invalid decimal values gracefully"""
        ret = super().to_representation(instance)
        
        # Handle potentially corrupted multiplier_at_creation
        try:
            if ret.get('multiplier_at_creation') is not None:
                float(ret['multiplier_at_creation'])
        except (ValueError, decimal.InvalidOperation, TypeError):
            # If conversion fails, use a fallback value
            ret['multiplier_at_creation'] = "1.0"
            
        return ret


class EvidenceSerializer(serializers.ModelSerializer):
    """Serializer for the Evidence model."""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Evidence
        fields = ['id', 'contribution', 'description', 'url', 'file', 'file_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_file_url(self, obj):
        """Returns the full URL to the file if it exists."""
        if not obj.file:
            return None
        
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url