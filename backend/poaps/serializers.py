from rest_framework import serializers

from users.serializers import LightUserSerializer

from .models import PoapClaim, PoapDrop


class PoapDropListSerializer(serializers.ModelSerializer):
    claimed_count = serializers.SerializerMethodField()
    has_claimed = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()
    claim_state = serializers.SerializerMethodField()

    class Meta:
        model = PoapDrop
        fields = [
            'id', 'title', 'slug', 'description', 'artwork_url',
            'event_start_at', 'event_end_at', 'status', 'max_claims',
            'claimed_count', 'has_claimed', 'can_claim', 'claim_state',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_claimed_count(self, obj):
        value = getattr(obj, 'claimed_count_value', None)
        if value is not None:
            return value
        return obj.claims.filter(user__isnull=False).count()

    def get_has_claimed(self, obj):
        value = getattr(obj, 'has_claimed_value', None)
        if value is not None:
            return bool(value)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return obj.claims.filter(user=request.user).exists()
        return bool(value)

    def get_can_claim(self, obj):
        return self._can_claim(obj)

    def get_claim_state(self, obj):
        if self.get_has_claimed(obj):
            return 'claimed'
        if obj.status == PoapDrop.STATUS_DRAFT:
            return 'draft'
        if obj.status == PoapDrop.STATUS_ARCHIVED:
            return 'archived'
        if not self._drop_has_capacity(obj):
            return 'full'
        if not self._has_open_distribution(obj):
            return 'unavailable'
        return 'live'

    def _can_claim(self, obj):
        return (
            obj.status == PoapDrop.STATUS_ACTIVE
            and not self.get_has_claimed(obj)
            and self._drop_has_capacity(obj)
            and self._has_open_distribution(obj)
        )

    def _drop_has_capacity(self, obj):
        if obj.max_claims is None:
            return True
        return self.get_claimed_count(obj) < obj.max_claims

    def _has_open_distribution(self, obj):
        value = getattr(obj, 'has_open_distribution_value', None)
        if value is not None:
            return bool(value)

        distributions = getattr(obj, 'prefetched_distributions', None)
        if distributions is None:
            distributions = obj.distributions.all()
        return any(distribution.is_open() for distribution in distributions)


class PoapDropDetailSerializer(PoapDropListSerializer):
    distributions = serializers.SerializerMethodField()
    current_user_claim = serializers.SerializerMethodField()

    class Meta(PoapDropListSerializer.Meta):
        fields = PoapDropListSerializer.Meta.fields + [
            'artwork_public_id', 'legacy_poap_id', 'discord_role_id',
            'distributions', 'current_user_claim',
        ]

    def get_distributions(self, obj):
        distributions = getattr(obj, 'prefetched_distributions', None)
        if distributions is None:
            distributions = obj.distributions.all()
        result = []
        for distribution in distributions:
            result.append({
                'id': distribution.id,
                'method': distribution.method,
                'active': distribution.active,
                'starts_at': distribution.starts_at,
                'ends_at': distribution.ends_at,
                'max_claims': distribution.max_claims,
                'claimed_count': distribution.claimed_count,
                'mint_link_count': getattr(distribution, 'mint_link_count', 0),
            })
        return result

    def get_current_user_claim(self, obj):
        claim = getattr(obj, 'current_user_claim_obj', None)
        if not claim:
            return None
        return {
            'id': claim.id,
            'claimed_at': claim.claimed_at,
            'claim_method': claim.claim_method,
            'source': claim.source,
        }


class PoapClaimSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = PoapClaim
        fields = [
            'id', 'user_details', 'claim_method', 'claimed_at', 'created_at',
        ]
        read_only_fields = fields

    def get_user_details(self, obj):
        if not obj.user:
            return None
        return LightUserSerializer(obj.user).data


class PoapProfileDropSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoapDrop
        fields = [
            'id', 'title', 'slug', 'description', 'artwork_url',
            'event_start_at', 'event_end_at', 'status',
        ]
        read_only_fields = fields


class PoapProfileClaimSerializer(serializers.ModelSerializer):
    drop = PoapProfileDropSerializer(read_only=True)

    class Meta:
        model = PoapClaim
        fields = ['id', 'drop', 'claim_method', 'claimed_at', 'source']
        read_only_fields = fields
