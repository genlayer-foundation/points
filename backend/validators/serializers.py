from rest_framework import serializers
from .models import ValidatorWallet, Validator


class ValidatorWalletSerializer(serializers.ModelSerializer):
    """
    Serializer for ValidatorWallet model.
    Used to display validator wallet data with operator info.
    """
    operator_user = serializers.SerializerMethodField()

    class Meta:
        model = ValidatorWallet
        fields = [
            'id',
            'address',
            'status',
            'operator_address',
            'operator_user',
            'v_stake',
            'd_stake',
            'moniker',
            'logo_uri',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_operator_user(self, obj):
        """
        Get operator user info if the operator is linked to a Validator in our DB.
        Returns user data (name, address, profile_image_url) or None if not linked.
        """
        if obj.operator and obj.operator.user:
            user = obj.operator.user
            return {
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'profile_image_url': user.profile_image_url,
                'visible': user.visible
            }
        return None


class LightValidatorWalletSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for ValidatorWallet in list views.
    Minimal fields for performance.
    """
    class Meta:
        model = ValidatorWallet
        fields = ['id', 'address', 'status', 'operator_address']
        read_only_fields = fields


class ValidatorWithWalletsSerializer(serializers.Serializer):
    """
    Serializer that combines Validator data with their validator wallets.
    Used for profile views to show operator's validators.
    """
    validator_wallets = ValidatorWalletSerializer(many=True, read_only=True)
    active_validators_count = serializers.SerializerMethodField()
    total_validators_count = serializers.SerializerMethodField()

    def get_active_validators_count(self, obj):
        """Get count of active validator wallets for this operator."""
        return obj.validator_wallets.filter(status='active').count()

    def get_total_validators_count(self, obj):
        """Get total count of validator wallets for this operator."""
        return obj.validator_wallets.count()
