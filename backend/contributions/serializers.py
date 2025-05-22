from rest_framework import serializers
from .models import ContributionType, Contribution
from users.serializers import UserSerializer


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
                  'points', 'frozen_global_points', 'evidence_url', 'notes', 
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'frozen_global_points', 'created_at', 'updated_at']