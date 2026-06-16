from rest_framework import serializers
from django.conf import settings
from .models import ValidatorWallet, Validator


class ValidatorWalletSerializer(serializers.ModelSerializer):
    """
    Serializer for ValidatorWallet model.
    Used to display validator wallet data with operator info.
    """
    operator_user = serializers.SerializerMethodField()
    explorer_url = serializers.SerializerMethodField()

    class Meta:
        model = ValidatorWallet
        fields = [
            'id',
            'address',
            'network',
            'status',
            'operator_address',
            'operator_user',
            'explorer_url',
            'v_stake',
            'd_stake',
            'moniker',
            'logo_uri',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_operator_user(self, obj):
        if obj.operator and obj.operator.user and obj.operator.user.visible:
            user = obj.operator.user
            return {
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'profile_image_url': user.profile_image_url,
                'visible': user.visible
            }
        return None

    def get_explorer_url(self, obj):
        network_config = settings.TESTNET_NETWORKS.get(obj.network, {})
        return network_config.get('explorer_url', '')


class WallOfShameSerializer(serializers.ModelSerializer):
    """
    Serializer for the public Wall of Shame endpoint.
    Surfaces the Grafana observability status alongside enough operator
    identity for the page to render the same identity surface as
    /validators/participants.
    """
    operator_user = serializers.SerializerMethodField()
    explorer_url = serializers.SerializerMethodField()

    class Meta:
        model = ValidatorWallet
        fields = [
            'id',
            'address',
            'network',
            'status',
            'moniker',
            'logo_uri',
            'operator_address',
            'operator_user',
            'explorer_url',
            'metrics_status',
            'logs_status',
            'last_grafana_check_at',
            'metrics_shame_started_at',
            'logs_shame_started_at',
            'version_shame_started_at',
        ]
        read_only_fields = fields

    def get_operator_user(self, obj):
        if obj.operator and obj.operator.user and obj.operator.user.visible:
            user = obj.operator.user
            return {
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'profile_image_url': user.profile_image_url,
                'visible': user.visible,
            }
        return None

    def get_explorer_url(self, obj):
        network_config = settings.TESTNET_NETWORKS.get(obj.network, {})
        return network_config.get('explorer_url', '')
