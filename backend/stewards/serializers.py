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


class BannedValidatorSerializer(serializers.Serializer):
    """
    Serializer for banned validator data from blockchain.
    """
    address = serializers.CharField(max_length=42, help_text="Validator's blockchain address")
    ban_timestamp = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="ISO formatted ban timestamp"
    )
    ban_timestamp_unix = serializers.IntegerField(
        allow_null=True,
        required=False,
        help_text="Unix timestamp of when validator was banned"
    )
    ban_index = serializers.IntegerField(
        allow_null=True,
        required=False,
        help_text="Index in the banned validators array"
    )
    is_banned = serializers.BooleanField(
        default=True,
        help_text="Whether the validator is currently banned"
    )
    user = UserSerializer(
        allow_null=True,
        required=False,
        read_only=True,
        help_text="User profile associated with this address (if exists)"
    )
    error = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Any error encountered while fetching validator data"
    )

    def to_representation(self, instance):
        """
        Convert the instance to a representation, enriching with user data if available.
        """
        representation = super().to_representation(instance)

        # Try to enrich with user data from database
        if 'address' in instance:
            try:
                user = User.objects.get(address__iexact=instance['address'])
                representation['user'] = UserSerializer(user).data
            except User.DoesNotExist:
                representation['user'] = None

        return representation


class BannedValidatorListSerializer(serializers.Serializer):
    """
    Serializer for the banned validators list response.
    """
    banned_validators = BannedValidatorSerializer(many=True)
    total_banned = serializers.IntegerField(help_text="Total number of banned validators")
    error = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Any error encountered while fetching data"
    )