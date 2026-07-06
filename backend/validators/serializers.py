from rest_framework import serializers
from django.conf import settings
from .models import ValidatorOperatorWallet, ValidatorWallet, Validator
from users.utils import truncate_address


def grafana_network_label(network):
    """Grafana `network` label value for a portal network key (e.g. 'asimov-phase5')."""
    return settings.GRAFANA_NETWORK_LABELS.get(network, network)


def grafana_explorer_url(network):
    """Explorer base URL for a portal network key ('' if unconfigured)."""
    return settings.TESTNET_NETWORKS.get(network, {}).get('explorer_url', '')


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
                # Portal account address: public form is truncated (users.utils).
                'address': truncate_address(user.address),
                'profile_image_url': user.profile_image_url,
                'visible': user.visible
            }
        return None

    def get_explorer_url(self, obj):
        network_config = settings.TESTNET_NETWORKS.get(obj.network, {})
        return network_config.get('explorer_url', '')


class ValidatorOperatorWalletSerializer(serializers.ModelSerializer):
    """
    Serializer for operator wallets claimed by a portal validator profile.
    """
    wallet_count = serializers.SerializerMethodField()
    active_wallet_count = serializers.SerializerMethodField()
    networks = serializers.SerializerMethodField()

    class Meta:
        model = ValidatorOperatorWallet
        fields = [
            'id',
            'address',
            'wallet_count',
            'active_wallet_count',
            'networks',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def _wallet_rows(self, obj):
        cache_name = '_matching_wallet_rows'
        if not hasattr(obj, cache_name):
            rows = list(
                ValidatorWallet.objects
                .filter(operator_address=obj.address)
                .values('status', 'network')
            )
            setattr(obj, cache_name, rows)
        return getattr(obj, cache_name)

    def get_wallet_count(self, obj):
        return len(self._wallet_rows(obj))

    def get_active_wallet_count(self, obj):
        return sum(1 for row in self._wallet_rows(obj) if row['status'] == 'active')

    def get_networks(self, obj):
        return sorted({row['network'] for row in self._wallet_rows(obj)})


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

    Raw facts only — verdicts are computed dashboard-side. `linked` says
    whether the wallet is attributed to a portal account (safe for
    non-visible operators: a bare boolean, never who). `moniker` / `logo_uri`
    are the raw on-chain getIdentity() values as synced (empty string =
    unset); `has_description` is a presence flag so the roster doesn't ship
    long description texts.
    """
    network = serializers.SerializerMethodField()
    node = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    operator = serializers.CharField(source='operator_address')
    account = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    explorer_url = serializers.SerializerMethodField()
    linked = serializers.SerializerMethodField()
    has_description = serializers.SerializerMethodField()

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
            'linked',
            'moniker',
            'logo_uri',
            'has_description',
        ]
        read_only_fields = fields

    def _visible_user(self, obj):
        if obj.operator and obj.operator.user and obj.operator.user.visible:
            return obj.operator.user
        return None

    def get_network(self, obj):
        return grafana_network_label(obj.network)

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
        # Identity display only — dashboards join on `node`, never on account.
        user = self._visible_user(obj)
        return truncate_address((user.address or '').lower()) if user and user.address else None

    def get_account_name(self, obj):
        user = self._visible_user(obj)
        return user.name if user else None

    def get_explorer_url(self, obj):
        return grafana_explorer_url(obj.network)

    def get_linked(self, obj):
        return obj.operator_id is not None

    def get_has_description(self, obj):
        return bool(obj.description)


class WallOfShameSerializer(serializers.ModelSerializer):
    """
    Serializer for the public Wall of Shame endpoint.
    Surfaces the Grafana observability status alongside enough operator
    identity for the page to render the same identity surface as
    /validators/participants.
    """
    operator_user = serializers.SerializerMethodField()
    explorer_url = serializers.SerializerMethodField()
    clean_streak_days = serializers.SerializerMethodField()
    clean_streak_broken_by = serializers.SerializerMethodField()

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
            'clean_streak_days',
            'clean_streak_broken_by',
        ]
        read_only_fields = fields

    def _streak(self, obj):
        # Per-node streak, injected by the view via context to avoid N+1 queries.
        return (self.context.get('streaks_by_wallet_id') or {}).get(obj.id)

    def get_clean_streak_days(self, obj):
        streak = self._streak(obj)
        return streak['days'] if streak else None

    def get_clean_streak_broken_by(self, obj):
        streak = self._streak(obj)
        return streak['broken_by'] if streak else []

    def get_operator_user(self, obj):
        if obj.operator and obj.operator.user and obj.operator.user.visible:
            user = obj.operator.user
            return {
                'id': user.id,
                'name': user.name,
                # Portal account address: public form is truncated (users.utils).
                'address': truncate_address(user.address),
                'profile_image_url': user.profile_image_url,
                'visible': user.visible,
            }
        return None

    def get_explorer_url(self, obj):
        network_config = settings.TESTNET_NETWORKS.get(obj.network, {})
        return network_config.get('explorer_url', '')
