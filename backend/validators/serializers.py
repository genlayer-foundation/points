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


class GrafanaValidatorSerializer(serializers.ModelSerializer):
    """
    Minimal validator roster for the Grafana Infinity datasource.

    One flat row per validator wallet, stable and intentionally small — no
    observability/Wall-of-Shame fields (those churn and live on the
    `wall-of-shame` endpoint). `network` is the Grafana `network` label value
    (e.g. 'asimov-phase5') and `node` is the on-chain validator address that
    matches the Prometheus `genlayer_node_info` `node` label, so a dashboard can
    join the roster straight onto metrics. Operator account identity (name,
    account address) is only exposed for visible operators; non-visible
    operators are identified by their on-chain operator address alone.
    """
    network = serializers.SerializerMethodField()
    node = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    operator = serializers.CharField(source='operator_address')
    account = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    explorer_url = serializers.SerializerMethodField()

    class Meta:
        model = ValidatorWallet
        fields = [
            'network',
            'node',
            'name',
            'status',
            'operator',
            'account',
            'account_name',
            'explorer_url',
        ]
        read_only_fields = fields

    def _visible_user(self, obj):
        if obj.operator and obj.operator.user and obj.operator.user.visible:
            return obj.operator.user
        return None

    def get_network(self, obj):
        return settings.GRAFANA_NETWORK_LABELS.get(obj.network, obj.network)

    def get_node(self, obj):
        return (obj.address or '').lower()

    def get_name(self, obj):
        if obj.moniker:
            return obj.moniker
        user = self._visible_user(obj)
        if user and user.name:
            return user.name
        addr = obj.address or ''
        return f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr

    def get_account(self, obj):
        user = self._visible_user(obj)
        return (user.address or '').lower() if user and user.address else None

    def get_account_name(self, obj):
        user = self._visible_user(obj)
        return user.name if user else None

    def get_explorer_url(self, obj):
        return settings.TESTNET_NETWORKS.get(obj.network, {}).get('explorer_url', '')


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
