from rest_framework import serializers
from .models import ContributionType, Contribution, SubmittedContribution, Evidence, ContributionHighlight
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
                # Try to convert to string first to check validity
                decimal_str = str(ret['multiplier_at_creation'])
                # If successful, keep the value as is
        except (decimal.InvalidOperation, TypeError, ValueError):
            # If there's an error, set a default value
            ret['multiplier_at_creation'] = '1.00'
            
        return ret


class EvidenceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Evidence
        fields = ['id', 'description', 'url', 'file', 'file_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_file_url(self, obj):
        """Returns the full URL to the file if it exists."""
        if not obj.file:
            return None
        
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class SubmittedContributionSerializer(serializers.ModelSerializer):
    """Serializer for submitted contributions (user submissions)."""
    user_details = UserSerializer(source='user', read_only=True)
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    evidence_items = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name',
                  'contribution_date', 'notes', 'state', 'state_display', 'staff_reply',
                  'reviewed_by', 'reviewed_at', 'evidence_items', 'can_edit',
                  'created_at', 'updated_at', 'last_edited_at']
        read_only_fields = ['id', 'user', 'state', 'staff_reply', 'reviewed_by', 
                          'reviewed_at', 'created_at', 'updated_at', 'last_edited_at']
    
    def get_evidence_items(self, obj):
        """Returns serialized evidence items for this submission."""
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True, context=self.context).data
    
    def get_can_edit(self, obj):
        """Check if the submission can be edited."""
        return obj.state == 'more_info_needed'
    
    def create(self, validated_data):
        """Create a new submission with the current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SubmittedEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for evidence items belonging to submitted contributions."""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Evidence
        fields = ['id', 'description', 'url', 'file', 'file_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_file_url(self, obj):
        """Returns the full URL to the file if it exists."""
        if not obj.file:
            return None
        
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class ContributionHighlightSerializer(serializers.ModelSerializer):
    contribution_details = ContributionSerializer(source='contribution', read_only=True)
    user_name = serializers.CharField(source='contribution.user.name', read_only=True)
    user_address = serializers.CharField(source='contribution.user.address', read_only=True)
    contribution_type_name = serializers.CharField(source='contribution.contribution_type.name', read_only=True)
    contribution_type_id = serializers.IntegerField(source='contribution.contribution_type.id', read_only=True)
    contribution_points = serializers.IntegerField(source='contribution.frozen_global_points', read_only=True)
    contribution_date = serializers.DateTimeField(source='contribution.contribution_date', read_only=True)
    
    class Meta:
        model = ContributionHighlight
        fields = ['id', 'title', 'description', 'contribution', 'contribution_details',
                  'user_name', 'user_address', 'contribution_type_name', 'contribution_type_id',
                  'contribution_points', 'contribution_date', 'created_at']
        read_only_fields = ['id', 'created_at']