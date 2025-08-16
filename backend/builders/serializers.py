from rest_framework import serializers
from .models import Builder


class BuilderSerializer(serializers.ModelSerializer):
    """
    Serializer for Builder model.
    """
    class Meta:
        model = Builder
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']