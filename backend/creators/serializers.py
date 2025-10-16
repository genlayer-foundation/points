from rest_framework import serializers
from .models import Creator


class CreatorSerializer(serializers.ModelSerializer):
    """
    Serializer for Creator model.
    """
    class Meta:
        model = Creator
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']