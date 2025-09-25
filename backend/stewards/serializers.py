from rest_framework import serializers
from .models import Steward
from users.models import User
from users.serializers import UserSerializer


class StewardSerializer(serializers.ModelSerializer):
    """
    Serializer for Steward model.
    """
    class Meta:
        model = Steward
        fields = ['created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


