from rest_framework import serializers
from .models import Steward


class StewardSerializer(serializers.ModelSerializer):
    """
    Serializer for Steward model.
    """
    class Meta:
        model = Steward
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']