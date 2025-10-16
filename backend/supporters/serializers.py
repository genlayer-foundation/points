from rest_framework import serializers
from .models import Supporter


class SupporterSerializer(serializers.ModelSerializer):
    """
    Serializer for Supporter model.
    """
    class Meta:
        model = Supporter
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']