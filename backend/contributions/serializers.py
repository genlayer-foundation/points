from rest_framework import serializers
from .models import ContributionType, Contribution
from users.serializers import UserSerializer
import decimal


class ContributionTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionType
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ContributionSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    
    class Meta:
        model = Contribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name', 
                  'points', 'frozen_global_points', 'multiplier_at_creation', 'contribution_date',
                  'evidence_url', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'frozen_global_points', 'created_at', 'updated_at']
    
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