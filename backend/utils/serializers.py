"""
Lightweight serializers for optimized API responses.

These serializers return minimal data for list views and nested relationships,
significantly reducing the number of database queries and response payload size.
"""
from rest_framework import serializers


class LightUserSerializer(serializers.Serializer):
    """
    Minimal user serializer for list views and nested relationships.
    Only includes essential display fields, no related objects or computed fields.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    profile_image_url = serializers.URLField(read_only=True)
    visible = serializers.BooleanField(read_only=True)


class LightContributionTypeSerializer(serializers.Serializer):
    """
    Minimal contribution type serializer for nested relationships.
    Only includes basic type information without expensive computed fields.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    description = serializers.CharField(read_only=True)
    min_points = serializers.IntegerField(read_only=True)
    max_points = serializers.IntegerField(read_only=True)
    # Include category slug only, not the full category object
    category = serializers.SerializerMethodField()

    def get_category(self, obj):
        """Return just the category slug."""
        return obj.category.slug if obj.category else None


class LightContributionSerializer(serializers.Serializer):
    """
    Minimal contribution serializer for recent contributions and highlights.
    Uses lightweight nested serializers to avoid N+1 queries.
    """
    id = serializers.IntegerField(read_only=True)
    user = LightUserSerializer(read_only=True)
    contribution_type = LightContributionTypeSerializer(read_only=True)
    points = serializers.IntegerField(read_only=True)
    frozen_global_points = serializers.IntegerField(read_only=True)
    multiplier_at_creation = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    contribution_date = serializers.DateTimeField(read_only=True)
    notes = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class LightValidatorSerializer(serializers.Serializer):
    """
    Minimal validator serializer without expensive stat calculations.
    Only includes node version and basic matching info.
    """
    node_version = serializers.CharField(read_only=True)
    matches_target = serializers.SerializerMethodField()
    target_version = serializers.SerializerMethodField()

    def get_matches_target(self, obj):
        """Check if the validator's version matches or is higher than the target."""
        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active()
        if target and obj.node_version:
            return obj.version_matches_or_higher(target.version)
        return False

    def get_target_version(self, obj):
        """Get the current target version."""
        from contributions.node_upgrade.models import TargetNodeVersion
        target = TargetNodeVersion.get_active()
        return target.version if target else None


class LightBuilderSerializer(serializers.Serializer):
    """
    Minimal builder serializer without expensive stat calculations.
    Just indicates the user is a builder.
    """
    created_at = serializers.DateTimeField(read_only=True)


class LightLeaderboardEntrySerializer(serializers.Serializer):
    """
    Minimal leaderboard entry for nested user data.
    Only includes rank and points, not full user details.
    """
    rank = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)
