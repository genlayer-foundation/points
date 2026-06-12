from django.db import models, transaction
from rest_framework import serializers
from .models import (
    ContributionType, Contribution, SubmittedContribution, Evidence,
    ContributionHighlight, Mission, StartupRequest, SubmissionNote,
    FeaturedContent, Alert, EvidenceURLType, ContributionDiscordXPState,
    DiscordXPDistributionEvent, ProjectMilestoneReview,
)
from .rubric_review import (
    normalize_rubric_review_payload,
    validate_template_action,
    uses_project_rubric,
)
from users.serializers import UserSerializer, LightUserSerializer
from users.models import User
from stewards.models import ReviewTemplate
from .project_milestones import is_milestone_contribution_type
from .recaptcha_field import ReCaptchaField
import decimal


# ============================================================================
# Evidence URL Type Serializers
# ============================================================================


class LightEvidenceURLTypeSerializer(serializers.Serializer):
    """Minimal evidence URL type for nested use in contribution types."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    is_generic = serializers.BooleanField(read_only=True)


class EvidenceURLTypeSerializer(serializers.ModelSerializer):
    """Full evidence URL type serializer with patterns for client-side detection."""
    class Meta:
        model = EvidenceURLType
        fields = ['id', 'name', 'slug', 'description', 'url_patterns',
                  'is_generic', 'order']
        read_only_fields = fields


# ============================================================================
# Lightweight Serializers for Optimized List Views
# ============================================================================
# These serializers provide minimal data for list views and nested relationships,
# significantly reducing database queries and response payload size.


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
    rubric_extra_points = serializers.IntegerField(read_only=True)
    max_submissions = serializers.IntegerField(read_only=True)
    review_flow = serializers.CharField(read_only=True)
    # Include category slug only, not the full category object
    category = serializers.SerializerMethodField()

    def get_category(self, obj):
        """Return just the category slug."""
        return obj.category.slug if obj.category else None


class LightMissionSerializer(serializers.Serializer):
    """
    Minimal mission serializer for nested relationships.
    Only includes basic mission information without expensive computed fields.
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    contribution_type = serializers.PrimaryKeyRelatedField(read_only=True)
    max_submissions = serializers.IntegerField(read_only=True)
    max_submissions_per_user = serializers.IntegerField(read_only=True)


class LightProjectContributionSerializer(serializers.Serializer):
    """Minimal data for the accepted Projects contribution a milestone links to."""
    id = serializers.IntegerField(read_only=True)
    title = serializers.SerializerMethodField()
    github_url = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()

    def get_title(self, obj):
        from .project_milestones import project_contribution_display_title
        return project_contribution_display_title(obj)

    def get_github_url(self, obj):
        from .project_milestones import project_contribution_github_url
        return project_contribution_github_url(obj)

    def get_link(self, obj):
        return f'/contribution/{obj.id}'


class EvidenceSerializer(serializers.ModelSerializer):
    """Serializer for evidence items."""
    url_type = LightEvidenceURLTypeSerializer(read_only=True)

    class Meta:
        model = Evidence
        fields = ['id', 'description', 'url', 'url_type', 'created_at']
        read_only_fields = ['id', 'url_type', 'created_at']


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
    title = serializers.CharField(read_only=True, allow_blank=True)
    project_contribution = LightProjectContributionSerializer(read_only=True)
    milestone_version = serializers.IntegerField(read_only=True)
    is_highlighted = serializers.SerializerMethodField()
    highlight = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_highlight(self, obj):
        highlight = next(iter(obj.highlights.all()), None)
        if not highlight:
            return None
        return {
            'title': highlight.title,
            'description': highlight.description,
        }

    def get_is_highlighted(self, obj):
        return bool(self.get_highlight(obj))

    def get_evidence_items(self, obj):
        """Returns serialized evidence items for this contribution."""
        # ViewSet prefetches evidence_items to avoid N+1 queries
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True).data


# ============================================================================
# Full Serializers
# ============================================================================


class ContributionTypeSerializer(serializers.ModelSerializer):
    current_multiplier = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.slug', read_only=True)
    accepted_evidence_url_types = serializers.SerializerMethodField()
    required_evidence_url_types = serializers.SerializerMethodField()
    required_discord_roles = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    submissions_remaining = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()

    class Meta:
        model = ContributionType
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'min_points', 'max_points',
            'rubric_extra_points', 'current_multiplier', 'is_submittable', 'review_flow', 'max_submissions',
            'submission_count', 'submissions_remaining', 'is_full',
            'show_in_contributions', 'examples',
            'required_social_accounts', 'required_discord_roles',
            'accepted_evidence_url_types', 'required_evidence_url_types',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_current_multiplier(self, obj):
        """Get the current multiplier value for this contribution type."""
        annotated_multiplier = getattr(obj, 'current_multiplier_value', None)
        if annotated_multiplier is not None:
            return float(annotated_multiplier)

        from leaderboard.models import GlobalLeaderboardMultiplier
        try:
            return float(GlobalLeaderboardMultiplier.get_current_multiplier_value(obj))
        except Exception:
            return 1.0

    def _all_evidence_url_types(self):
        cached = self.context.get('_all_evidence_url_types')
        if cached is None:
            cached = list(EvidenceURLType.objects.all().order_by('order', 'name'))
            self.context['_all_evidence_url_types'] = cached
        return cached

    @staticmethod
    def _ordered_url_types(url_types):
        return sorted(url_types, key=lambda t: (t.order, t.name))

    def get_accepted_evidence_url_types(self, obj):
        """Return accepted evidence URL types with patterns for client-side detection.

        An empty ``accepted_evidence_url_types`` means all types are accepted,
        so we return all evidence URL types in that case (even when
        ``required_evidence_url_types`` is set, since requiring a type does
        not restrict which other types are allowed as extras).
        Required types are merged in when an explicit accepted list is set,
        so they are always part of the returned list.
        """
        accepted = list(obj.accepted_evidence_url_types.all())
        if not accepted:
            url_types = self._all_evidence_url_types()
        else:
            required = list(obj.required_evidence_url_types.all())
            merged = {t.id: t for t in accepted}
            for t in required:
                merged.setdefault(t.id, t)
            url_types = self._ordered_url_types(merged.values())
        return EvidenceURLTypeSerializer(url_types, many=True).data

    def get_required_evidence_url_types(self, obj):
        """Return required evidence URL types (at least one must match)."""
        url_types = self._ordered_url_types(
            obj.required_evidence_url_types.all()
        )
        return EvidenceURLTypeSerializer(url_types, many=True).data

    def get_required_discord_roles(self, obj):
        """Return active Discord roles that can satisfy this contribution type."""
        from social_connections.serializers import DiscordRoleSerializer

        roles = obj.required_discord_roles.filter(
            deleted_at__isnull=True,
        ).exclude(
            role_id=models.F('guild_id'),
        ).order_by('-position', 'name')
        return DiscordRoleSerializer(roles, many=True).data

    def get_submission_count(self, obj):
        return obj.get_submission_count()

    def get_submissions_remaining(self, obj):
        return obj.submissions_remaining()

    def get_is_full(self, obj):
        return obj.is_full()



class ContributionSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    contribution_type_min_points = serializers.ReadOnlyField(source='contribution_type.min_points')
    contribution_type_max_points = serializers.ReadOnlyField(source='contribution_type.max_points')
    contribution_type_details = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    highlight = serializers.SerializerMethodField()
    project_contribution = LightProjectContributionSerializer(read_only=True)

    class Meta:
        model = Contribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name',
                  'contribution_type_min_points', 'contribution_type_max_points', 'contribution_type_details',
                  'points', 'frozen_global_points', 'multiplier_at_creation', 'contribution_date',
                  'evidence_items', 'notes', 'title', 'highlight', 'mission',
                  'project_contribution', 'milestone_version', 'created_at', 'updated_at']
        read_only_fields = ['id', 'frozen_global_points', 'created_at', 'updated_at']

    def get_user_details(self, obj):
        """
        Returns user details using lightweight or full serializer based on context.
        Use lightweight serializer for list views to avoid N+1 queries.
        """
        use_light = self.context.get('use_light_serializers', True)
        if use_light:
            return LightUserSerializer(obj.user).data
        return UserSerializer(obj.user, context=self.context).data

    def get_evidence_items(self, obj):
        """Returns serialized evidence items for this contribution."""
        # Always include evidence - ViewSet already prefetches to avoid N+1 queries
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True, context=self.context).data

    def get_contribution_type_details(self, obj):
        """
        Returns contribution type details using lightweight or full serializer based on context.
        Use lightweight serializer for list views to avoid N+1 queries.
        """
        use_light = self.context.get('use_light_serializers', True)
        if use_light:
            return LightContributionTypeSerializer(obj.contribution_type).data
        return ContributionTypeSerializer(obj.contribution_type, context=self.context).data

    def get_highlight(self, obj):
        """Returns highlight information if this contribution is highlighted."""
        # For list views, skip highlight queries
        if self.context.get('use_light_serializers', True):
            return None
        highlight = obj.highlights.first()  # Using related_name from the model
        if highlight:
            return {
                'title': highlight.title,
                'description': highlight.description
            }
        return None


    def to_representation(self, instance):
        """Override to_representation to handle invalid decimal values gracefully and smart mission serialization"""
        ret = super().to_representation(instance)

        # Handle potentially corrupted multiplier_at_creation
        try:
            if ret.get('multiplier_at_creation') is not None:
                # Try to convert to string first to check validity
                decimal_str = str(ret['multiplier_at_creation'])
                # If successful, keep the value as is
        except (decimal.InvalidOperation, TypeError, ValueError):
            # If there's an error, set a default value
            ret['multiplier_at_creation'] = '1.00'

        # Transform mission from ID to full object for reads
        if instance.mission:
            use_light = self.context.get('use_light_serializers', True)
            if use_light:
                ret['mission'] = LightMissionSerializer(instance.mission).data
            else:
                ret['mission'] = MissionSerializer(instance.mission, context=self.context).data

        return ret


class DiscordXPDistributionEventSerializer(serializers.ModelSerializer):
    actor = LightUserSerializer(read_only=True)

    class Meta:
        model = DiscordXPDistributionEvent
        fields = [
            'id', 'amount', 'action', 'actor',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ContributionDiscordXPStateSerializer(serializers.ModelSerializer):
    contributor = serializers.SerializerMethodField()
    discord = serializers.SerializerMethodField()
    contribution_type = serializers.SerializerMethodField()
    contribution_title = serializers.CharField(source='contribution.title', read_only=True)
    contribution_notes = serializers.CharField(source='contribution.notes', read_only=True)
    contribution_date = serializers.DateTimeField(source='contribution.contribution_date', read_only=True)
    contribution_created_at = serializers.DateTimeField(source='contribution.created_at', read_only=True)
    community_points = serializers.IntegerField(source='contribution.frozen_global_points', read_only=True)
    frozen_global_points = serializers.IntegerField(source='contribution.frozen_global_points', read_only=True)
    pending_amount = serializers.SerializerMethodField()
    command = serializers.SerializerMethodField()
    distributed_by = LightUserSerializer(read_only=True)
    last_copied_by = LightUserSerializer(read_only=True)
    latest_event = serializers.SerializerMethodField()

    class Meta:
        model = ContributionDiscordXPState
        fields = [
            'id', 'contribution', 'status', 'awarded_amount',
            'community_points', 'frozen_global_points', 'pending_amount', 'command',
            'distributed_at', 'distributed_by',
            'last_copied_at', 'last_copied_by',
            'contributor', 'discord', 'contribution_type',
            'contribution_title', 'contribution_notes', 'contribution_date',
            'contribution_created_at', 'latest_event', 'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_contributor(self, obj):
        return LightUserSerializer(obj.contribution.user).data

    def get_discord(self, obj):
        connection = getattr(obj.contribution.user, 'discordconnection', None)
        if not connection:
            return None

        return {
            'platform_username': connection.platform_username,
            'guild_nick': connection.guild_nick,
            'guild_member': connection.guild_member,
            'avatar_url': connection.avatar_url,
        }

    def get_contribution_type(self, obj):
        return LightContributionTypeSerializer(obj.contribution.contribution_type).data

    def get_pending_amount(self, obj):
        annotated = getattr(obj, 'pending_xp', None)
        if annotated is not None:
            return annotated
        return obj.pending_amount

    def get_command(self, obj):
        return obj.command

    def get_latest_event(self, obj):
        events = list(getattr(obj, 'latest_events', []))
        if not events:
            events = list(getattr(obj, '_prefetched_objects_cache', {}).get('events', []))
        if events:
            return DiscordXPDistributionEventSerializer(events[0]).data
        latest = obj.events.order_by('-created_at').first()
        if not latest:
            return None
        return DiscordXPDistributionEventSerializer(latest).data


class SubmittedEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for evidence items belonging to submitted contributions."""
    id = serializers.IntegerField(required=False)  # Optional: present for existing evidence, absent for new
    url = serializers.URLField(
        required=True,
        allow_blank=False,
        error_messages={
            'blank': 'An evidence URL is required.',
            'required': 'An evidence URL is required.',
        },
    )
    url_type = LightEvidenceURLTypeSerializer(read_only=True)

    class Meta:
        model = Evidence
        fields = ['id', 'description', 'url', 'url_type', 'created_at']
        read_only_fields = ['url_type', 'created_at']


class SubmittedContributionSerializer(serializers.ModelSerializer):
    """
    Serializer for submitted contributions (user submissions).
    Context-aware: Uses lightweight serializers for list views to avoid N+1 queries.
    Supports formset-style evidence updates: evidence items with 'id' are updated,
    items without 'id' are created, and items not in the list are deleted.

    Note: reCAPTCHA validation is required only for creating new submissions.
    """
    user_details = serializers.SerializerMethodField()
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    contribution_type_details = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    can_edit = serializers.SerializerMethodField()
    contribution = serializers.SerializerMethodField()
    project_contribution = serializers.PrimaryKeyRelatedField(
        queryset=Contribution.objects.filter(contribution_type__slug='projects'),
        required=False,
        allow_null=True,
    )
    recaptcha = ReCaptchaField(required=False)  # Required only on create, handled in validate()

    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name',
                  'contribution_type_details', 'contribution_date', 'notes', 'title', 'state', 'state_display',
                  'staff_reply', 'reviewed_by', 'reviewed_at', 'evidence_items', 'can_edit',
                  'proposed_points', 'converted_contribution', 'contribution', 'mission',
                  'project_contribution', 'milestone_version',
                  'has_appeal', 'appeal_reason',
                  'created_at', 'updated_at', 'last_edited_at', 'recaptcha']
        read_only_fields = ['id', 'user', 'state', 'staff_reply', 'reviewed_by',
                          'reviewed_at', 'created_at', 'updated_at', 'last_edited_at',
                          'proposed_points', 'converted_contribution',
                          'milestone_version',
                          'has_appeal', 'appeal_reason']

    def get_user_details(self, obj):
        """
        Returns user details using lightweight or full serializer based on context.
        Use lightweight serializer for list views to avoid N+1 queries.
        """
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightUserSerializer(obj.user).data
        return UserSerializer(obj.user, context=self.context).data

    def get_contribution_type_details(self, obj):
        """
        Returns contribution type details using lightweight or full serializer based on context.
        Use lightweight serializer for list views to avoid N+1 queries.
        """
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightContributionTypeSerializer(obj.contribution_type).data
        return ContributionTypeSerializer(obj.contribution_type, context=self.context).data

    def get_evidence_items(self, obj):
        """Returns serialized evidence items for this submission."""
        # Always include evidence - ViewSet already prefetches to avoid N+1 queries
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return SubmittedEvidenceSerializer(evidence_items, many=True, context=self.context).data

    def get_can_edit(self, obj):
        """Check if the submission can be edited."""
        return obj.state in ['pending', 'more_info_needed']

    def get_contribution(self, obj):
        """Get the created contribution if submission was accepted."""
        # Skip for list views
        if self.context.get('use_light_serializers', False):
            return None
        if obj.converted_contribution:
            # Use context to control serialization depth
            contrib_context = self.context.copy()
            contrib_context['use_light_serializers'] = True  # Use light even for detail
            return ContributionSerializer(obj.converted_contribution, context=contrib_context).data
        return None

    def validate_contribution_date(self, value):
        """
        The contribution date is client-provided and flows into date-ranged
        leaderboards once accepted, so future dates are rejected server-side
        (small allowance for client clock skew).
        """
        from django.utils import timezone
        from datetime import timedelta

        if value and value > timezone.now() + timedelta(minutes=5):
            raise serializers.ValidationError(
                'Contribution date cannot be in the future. '
                'Please check your device clock or use the current date.'
            )
        return value

    def validate(self, data):
        """
        Validate submission data.
        Require reCAPTCHA only for new submissions (create operation).
        """
        # Check if this is a create operation (no instance exists)
        if not self.instance:
            # Creating new submission - require reCAPTCHA
            if 'recaptcha' not in data or not data.get('recaptcha'):
                raise serializers.ValidationError({
                    'recaptcha': 'reCAPTCHA verification is required for new submissions.'
                })

        # Remove recaptcha from validated data as it's not a model field
        data.pop('recaptcha', None)

        return data

    def _validate_evidence_items(self, evidence_items_data,
                                 require_at_least_one,
                                 contribution_type=None,
                                 user=None,
                                 exclude_submission_id=None):
        """Validate inline evidence payloads for create/update flows.

        Performs URL type detection, type mismatch checking, duplicate URL
        checking, and handle ownership validation.
        """
        from .url_utils import (
            detect_url_type, normalize_url, check_duplicate_url,
            validate_handle_ownership,
        )

        if evidence_items_data is None:
            if require_at_least_one:
                raise serializers.ValidationError(
                    {
                        'evidence_items': (
                            'At least one evidence item with a URL is required.'
                        ),
                    }
                )
            return None

        if not isinstance(evidence_items_data, list):
            raise serializers.ValidationError(
                {'evidence_items': 'Expected a list of evidence items.'}
            )

        evidence_serializer = SubmittedEvidenceSerializer(
            data=evidence_items_data, many=True,
        )
        if not evidence_serializer.is_valid():
            raise serializers.ValidationError(
                {'evidence_items': evidence_serializer.errors}
            )

        evidence_validated = evidence_serializer.validated_data
        if require_at_least_one and not any(
            item.get('url') for item in evidence_validated
        ):
            raise serializers.ValidationError(
                {
                    'evidence_items': (
                        'At least one evidence item with a URL is required.'
                    ),
                }
            )

        # --- Evidence URL type validation ---
        # accepted_types = None means "all types accepted" (existing behavior
        # when accepted_evidence_url_types is empty). required types are
        # orthogonal: they add an at-least-one-match rule without restricting
        # which other types are allowed as extras.
        accepted_types = None
        required_type_ids = set()
        required_type_names = []
        if contribution_type:
            accepted_qs = contribution_type.accepted_evidence_url_types.all()
            required_qs = contribution_type.required_evidence_url_types.all()
            required_type_ids = set(required_qs.values_list('id', flat=True))
            required_type_names = list(required_qs.values_list('name', flat=True))
            if accepted_qs.exists():
                accepted_types = set(
                    accepted_qs.values_list('id', flat=True)
                ) | required_type_ids

        errors = []
        has_required_match = not required_type_ids  # satisfied if none required
        for i, item in enumerate(evidence_validated):
            url = item.get('url', '')
            if not url:
                continue

            # 1. Auto-detect URL type
            url_type = detect_url_type(url)
            item['_detected_url_type'] = url_type

            # Track whether any URL satisfies the required-type rule
            if url_type and url_type.id in required_type_ids:
                has_required_match = True

            # 2. URL type mismatch check
            # Generic-typed URLs ('Other') must not bypass an explicit
            # whitelist. An admin restricting accepted types intends to
            # reject unrecognized URLs too; if generic URLs should be
            # allowed, the admin can add the 'Other' type to
            # accepted_evidence_url_types.
            if (accepted_types is not None
                    and url_type
                    and url_type.id not in accepted_types):
                accepted_names = list(
                    contribution_type.accepted_evidence_url_types
                    .values_list('name', flat=True)
                )
                # Include required types in the accepted list shown to users
                for n in required_type_names:
                    if n not in accepted_names:
                        accepted_names.append(n)
                errors.append({
                    'index': i,
                    'field': 'url',
                    'message': (
                        f"This contribution type does not accept "
                        f"{url_type.name} URLs. Expected: "
                        f"{', '.join(accepted_names)}."
                    ),
                })
                continue  # Skip further checks for this URL

            # 3. Duplicate URL check
            dup_msg = check_duplicate_url(url, exclude_submission_id=exclude_submission_id)
            if dup_msg:
                errors.append({
                    'index': i,
                    'field': 'url',
                    'message': dup_msg,
                })
                continue

            # 4. Handle ownership check
            if url_type and user:
                ownership_error = validate_handle_ownership(url, url_type, user)
                if ownership_error:
                    errors.append({
                        'index': i,
                        'field': 'url',
                        'message': ownership_error,
                    })

        if errors:
            raise serializers.ValidationError(
                {'evidence_items': errors}
            )

        if not has_required_match:
            raise serializers.ValidationError(
                {
                    'evidence_items': (
                        f"At least one evidence URL must be one of: "
                        f"{', '.join(required_type_names)}."
                    ),
                }
            )

        return evidence_validated

    def create(self, validated_data):
        """Create a new submission with the current user and inline evidence.

        Requires at least one evidence item with a URL. The submission and
        its evidence are created inside a DB transaction so a mid-loop
        failure cannot leave a partial record behind.
        """
        user = self.context['request'].user
        validated_data['user'] = user
        evidence_items_data = self.initial_data.get('evidence_items', None)

        # Resolve contribution_type for evidence validation
        contribution_type = validated_data.get('contribution_type')

        evidence_validated = self._validate_evidence_items(
            evidence_items_data,
            # Milestones are reviewed from the linked project's repository,
            # so extra evidence URLs are optional for them.
            require_at_least_one=not is_milestone_contribution_type(contribution_type),
            contribution_type=contribution_type,
            user=user,
        )

        with transaction.atomic():
            instance = super().create(validated_data)
            for evidence_data in (evidence_validated or []):
                detected_type = evidence_data.pop('_detected_url_type', None)
                Evidence.objects.create(
                    submitted_contribution=instance,
                    description=evidence_data.get('description', ''),
                    url=evidence_data.get('url', ''),
                    url_type=detected_type,
                )

        return instance

    def update(self, instance, validated_data):
        """
        Update submission with formset-style evidence handling.
        Evidence items with 'id' are updated, items without 'id' are created,
        and items not in the list are deleted.
        """
        # Extract evidence items from initial_data (raw request data)
        # since evidence_items is a SerializerMethodField and not in validated_data
        evidence_items_data = self.initial_data.get('evidence_items', None)
        evidence_items_validated = None
        if evidence_items_data is not None:
            request = self.context.get('request')
            user = request.user if request else instance.user
            contribution_type = (
                validated_data.get('contribution_type')
                or instance.contribution_type
            )
            evidence_items_validated = self._validate_evidence_items(
                evidence_items_data,
                require_at_least_one=not is_milestone_contribution_type(contribution_type),
                contribution_type=contribution_type,
                user=user,
                exclude_submission_id=instance.id,
            )

        # Handle evidence updates if provided (formset pattern)
        with transaction.atomic():
            # Update the submission fields only after evidence validation passes
            instance = super().update(instance, validated_data)

            if evidence_items_validated is not None:
                # Get existing evidence IDs
                existing_evidence_ids = set(
                    instance.evidence_items.values_list('id', flat=True)
                )

                # Track which evidence items are being kept/updated
                processed_evidence_ids = set()

                for evidence_data in evidence_items_validated:
                    evidence_id = evidence_data.get('id')
                    detected_type = evidence_data.pop('_detected_url_type', None)

                    if evidence_id:
                        # Update existing evidence
                        try:
                            evidence = Evidence.objects.get(
                                id=evidence_id,
                                submitted_contribution=instance,
                            )
                            # Update fields
                            evidence.description = evidence_data.get(
                                'description', evidence.description,
                            )
                            evidence.url = evidence_data.get(
                                'url', evidence.url,
                            )
                            evidence.url_type = detected_type
                            evidence.save()
                            processed_evidence_ids.add(evidence_id)
                        except Evidence.DoesNotExist:
                            raise serializers.ValidationError(
                                {
                                    'evidence_items': (
                                        f'Invalid evidence item ID: '
                                        f'{evidence_id}'
                                    ),
                                }
                            )
                    else:
                        # Create new evidence
                        Evidence.objects.create(
                            submitted_contribution=instance,
                            description=evidence_data.get('description', ''),
                            url=evidence_data.get('url', ''),
                            url_type=detected_type,
                        )

                # Delete evidence items that weren't in the submitted list
                evidence_to_delete = existing_evidence_ids - processed_evidence_ids
                if evidence_to_delete:
                    Evidence.objects.filter(id__in=evidence_to_delete).delete()

        return instance

    def to_representation(self, instance):
        """Transform mission from ID to full object for reads"""
        ret = super().to_representation(instance)

        # Transform mission from ID to full object for reads
        if instance.mission:
            use_light = self.context.get('use_light_serializers', True)
            if use_light:
                ret['mission'] = LightMissionSerializer(instance.mission).data
            else:
                ret['mission'] = MissionSerializer(instance.mission, context=self.context).data
        if instance.project_contribution:
            ret['project_contribution'] = LightProjectContributionSerializer(
                instance.project_contribution
            ).data

        return ret


class ContributionHighlightSerializer(serializers.ModelSerializer):
    contribution_details = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='contribution.user.name', read_only=True)
    user_address = serializers.CharField(source='contribution.user.address', read_only=True)
    user_profile_image_url = serializers.URLField(source='contribution.user.profile_image_url', read_only=True)
    # Role status fields for Avatar color determination
    user_validator = serializers.SerializerMethodField()
    user_builder = serializers.SerializerMethodField()
    user_steward = serializers.SerializerMethodField()
    user_has_validator_waitlist = serializers.SerializerMethodField()
    user_has_builder_welcome = serializers.SerializerMethodField()
    contribution_type_name = serializers.CharField(source='contribution.contribution_type.name', read_only=True)
    contribution_type_id = serializers.IntegerField(source='contribution.contribution_type.id', read_only=True)
    contribution_type_slug = serializers.SlugField(source='contribution.contribution_type.slug', read_only=True)
    contribution_type_category = serializers.CharField(source='contribution.contribution_type.category.slug', read_only=True)
    contribution_points = serializers.IntegerField(source='contribution.frozen_global_points', read_only=True)
    contribution_title = serializers.CharField(source='contribution.title', read_only=True)
    contribution_date = serializers.DateTimeField(source='contribution.contribution_date', read_only=True)
    # Mission fields for indicating when highlight is from a mission
    mission_name = serializers.CharField(source='contribution.mission.name', read_only=True)
    mission_id = serializers.IntegerField(source='contribution.mission.id', read_only=True)

    class Meta:
        model = ContributionHighlight
        fields = ['id', 'title', 'description', 'contribution', 'contribution_details',
                  'user_name', 'user_address', 'user_profile_image_url',
                  'user_validator', 'user_builder', 'user_steward',
                  'user_has_validator_waitlist', 'user_has_builder_welcome',
                  'contribution_type_name', 'contribution_type_id', 'contribution_type_slug',
                  'contribution_type_category', 'contribution_points', 'contribution_date',
                  'contribution_title', 'mission_name', 'mission_id', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_contribution_details(self, obj):
        """
        Return lightweight contribution details to avoid N+1 queries.
        Most needed info is already in the flat fields above.
        """
        return LightContributionSerializer(obj.contribution).data

    def get_user_validator(self, obj):
        """Check if user has validator role (OneToOne)."""
        return hasattr(obj.contribution.user, 'validator')

    def get_user_builder(self, obj):
        """Check if user has builder role (OneToOne)."""
        return hasattr(obj.contribution.user, 'builder')

    def get_user_steward(self, obj):
        """Check if user has steward role (OneToOne)."""
        return hasattr(obj.contribution.user, 'steward')

    def get_user_has_validator_waitlist(self, obj):
        """Check if user has validator-waitlist contribution."""
        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
            return Contribution.objects.filter(
                user=obj.contribution.user,
                contribution_type=waitlist_type
            ).exists()
        except ContributionType.DoesNotExist:
            return False

    def get_user_has_builder_welcome(self, obj):
        """Check if user has builder-welcome contribution."""
        try:
            welcome_type = ContributionType.objects.get(slug='builder-welcome')
            return Contribution.objects.filter(
                user=obj.contribution.user,
                contribution_type=welcome_type
            ).exists()
        except ContributionType.DoesNotExist:
            return False



class StewardSubmissionReviewSerializer(serializers.Serializer):
    """Serializer for steward review actions on submissions."""
    action = serializers.ChoiceField(choices=['accept', 'reject', 'more_info'])
    
    # User field to assign the contribution to a different user than the submitter
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        help_text="User to assign the contribution to (defaults to original submitter)"
    )
    
    # Fields for acceptance
    contribution_type = serializers.PrimaryKeyRelatedField(
        queryset=ContributionType.objects.all(),
        required=False,
        help_text="Contribution type (can be changed from original)"
    )
    project_contribution = serializers.PrimaryKeyRelatedField(
        queryset=Contribution.objects.filter(contribution_type__slug='projects'),
        required=False,
        allow_null=True,
        help_text="Accepted Projects contribution to link when accepting as a milestone"
    )
    points = serializers.IntegerField(
        required=False,
        min_value=0,
        help_text="Points to award (required for accept)"
    )
    
    # Highlight fields (optional for acceptance)
    create_highlight = serializers.BooleanField(default=False, required=False)
    highlight_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    highlight_description = serializers.CharField(required=False, allow_blank=True)
    
    # Staff reply (required for reject/more_info)
    staff_reply = serializers.CharField(required=False, allow_blank=True)

    # Template tracking for calibration
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=ReviewTemplate.objects.all(), required=False, allow_null=True,
    )
    rubric_review = serializers.JSONField(required=False)
    
    def validate(self, data):
        """Validate the review action and required fields."""
        action = data.get('action')
        validate_template_action(data.get('template_id'), action)
        submission = self.context.get('submission')
        request = self.context.get('request')
        current_contribution_type = submission.contribution_type if submission else None
        effective_contribution_type = (
            data.get('contribution_type')
            if action == 'accept'
            else current_contribution_type
        ) or current_contribution_type
        current_requires_rubric = uses_project_rubric(current_contribution_type)
        requires_rubric = uses_project_rubric(effective_contribution_type)
        requires_direct_rubric = requires_rubric and action in ['accept', 'reject']
        if requires_direct_rubric or 'rubric_review' in data:
            if requires_rubric:
                data['rubric_review'] = normalize_rubric_review_payload(
                    data.get('rubric_review'),
                    action,
                    require_overall_reason=False,
                    action_field='action',
                )
            elif current_requires_rubric:
                data.pop('rubric_review', None)
            else:
                raise serializers.ValidationError({
                    'rubric_review': 'Rubric review is only accepted for Builder Project reviews.'
                })
        
        if action == 'accept':
            if 'points' not in data or data.get('points') is None:
                raise serializers.ValidationError({
                    'points': 'Points are required when accepting a submission.'
                })
            
            # Validate points are within contribution type limits
            contribution_type = data.get('contribution_type')
            if not contribution_type and submission:
                contribution_type = submission.contribution_type
            if contribution_type:
                points = data.get('points')
                if points < contribution_type.min_points or points > contribution_type.max_points:
                    raise serializers.ValidationError({
                        'points': f'Points must be between {contribution_type.min_points} and {contribution_type.max_points} for {contribution_type.name}.'
                    })

            if submission and data.get('user') and data['user'] != submission.user:
                reviewer_is_staff = bool(
                    request
                    and request.user
                    and request.user.is_authenticated
                    and (request.user.is_staff or request.user.is_superuser)
                )
                if not reviewer_is_staff:
                    raise serializers.ValidationError({
                        'user': 'Only staff users can reassign accepted contributions.'
                    })
            
            # Validate highlight fields if creating highlight
            if data.get('create_highlight'):
                if not data.get('highlight_title'):
                    raise serializers.ValidationError({
                        'highlight_title': 'Title is required when creating a highlight.'
                    })
                if not data.get('highlight_description'):
                    raise serializers.ValidationError({
                        'highlight_description': 'Description is required when creating a highlight.'
                    })
        
        elif action in ['reject', 'more_info']:
            if not data.get('staff_reply'):
                action_text = 'rejecting' if action == 'reject' else 'requesting more information for'
                raise serializers.ValidationError({
                    'staff_reply': f'Staff reply is required when {action_text} a submission.'
                })
        
        return data


class StewardAcceptedSubmissionUpdateSerializer(serializers.Serializer):
    """Serializer for correcting accepted submission awards."""
    points = serializers.IntegerField(required=True, min_value=0)
    create_highlight = serializers.BooleanField(default=False, required=False)
    remove_highlight = serializers.BooleanField(default=False, required=False)
    highlight_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    highlight_description = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        contribution_type = self.context['contribution_type']
        points = data['points']
        if points < contribution_type.min_points or points > contribution_type.max_points:
            raise serializers.ValidationError({
                'points': f'Points must be between {contribution_type.min_points} and {contribution_type.max_points} for {contribution_type.name}.'
            })

        if data.get('create_highlight'):
            if data.get('remove_highlight'):
                raise serializers.ValidationError({
                    'remove_highlight': 'Cannot remove and create a highlight in the same update.'
                })
            if not data.get('highlight_title'):
                raise serializers.ValidationError({
                    'highlight_title': 'Title is required when creating a highlight.'
                })
            if not data.get('highlight_description'):
                raise serializers.ValidationError({
                    'highlight_description': 'Description is required when creating a highlight.'
                })

        return data


class SubmissionNoteSerializer(serializers.ModelSerializer):
    """Serializer for CRM notes on submissions."""
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionNote
        fields = ['id', 'user', 'user_name', 'message', 'is_proposal', 'data', 'created_at']
        read_only_fields = ['id', 'user', 'user_name', 'is_proposal', 'data', 'created_at']

    def get_user_name(self, obj):
        return obj.user.name or obj.user.address[:10] + '...'


class ProjectMilestoneReviewSerializer(serializers.ModelSerializer):
    proposer_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMilestoneReview
        fields = [
            'id', 'review_flow', 'action', 'confidence', 'gate_failures',
            'sections', 'extras', 'overall_reason', 'proposer',
            'proposer_name', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_proposer_name(self, obj):
        if not obj.proposer:
            return None
        return obj.proposer.name or obj.proposer.address[:10] + '...'


class SubmissionProposeSerializer(serializers.Serializer):
    """Serializer for steward proposal actions on submissions."""
    proposed_action = serializers.ChoiceField(choices=['accept', 'reject', 'more_info'])

    # Fields for acceptance proposals
    proposed_points = serializers.IntegerField(required=False, min_value=0)
    proposed_contribution_type = serializers.PrimaryKeyRelatedField(
        queryset=ContributionType.objects.all(),
        required=False,
    )
    proposed_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
    )
    proposed_staff_reply = serializers.CharField(required=False, allow_blank=True, default='')
    # Template tracking for calibration
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=ReviewTemplate.objects.all(), required=False, allow_null=True,
    )
    proposed_create_highlight = serializers.BooleanField(default=False, required=False)
    proposed_highlight_title = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    proposed_highlight_description = serializers.CharField(required=False, allow_blank=True, default='')
    confidence = serializers.ChoiceField(
        choices=['high', 'medium', 'low'],
        required=False,
        allow_null=True,
    )
    rubric_review = serializers.JSONField(required=False)

    def validate(self, data):
        submission = self.context.get('submission')
        action = data.get('proposed_action')
        validate_template_action(data.get('template_id'), action)
        current_contribution_type = submission.contribution_type if submission else None
        effective_contribution_type = (
            data.get('proposed_contribution_type')
            or current_contribution_type
        )
        current_requires_rubric = uses_project_rubric(current_contribution_type)
        requires_rubric = uses_project_rubric(effective_contribution_type)

        if requires_rubric:
            data['rubric_review'] = normalize_rubric_review_payload(
                data.get('rubric_review'),
                action,
            )
        elif 'rubric_review' in data:
            if current_requires_rubric:
                data.pop('rubric_review', None)
            else:
                raise serializers.ValidationError({
                    'rubric_review': 'Rubric review is only accepted for Builder Project proposals.'
                })

        if action == 'accept':
            proposed_points = data.get('proposed_points')
            if proposed_points is None:
                if not requires_rubric:
                    raise serializers.ValidationError({
                        'proposed_points': 'Points are required when proposing acceptance.'
                    })
            else:
                ct = effective_contribution_type
                pts = proposed_points
                if ct and (pts < ct.min_points or pts > ct.max_points):
                    raise serializers.ValidationError({
                        'proposed_points': f'Points must be between {ct.min_points} and {ct.max_points} for {ct.name}.'
                    })
            if data.get('proposed_create_highlight') and not requires_rubric:
                if not data.get('proposed_highlight_title'):
                    raise serializers.ValidationError({
                        'proposed_highlight_title': 'Title is required when proposing a highlight.'
                    })
                if not data.get('proposed_highlight_description'):
                    raise serializers.ValidationError({
                        'proposed_highlight_description': 'Description is required when proposing a highlight.'
                    })
        elif action in ['reject', 'more_info']:
            if not data.get('proposed_staff_reply'):
                action_text = 'rejecting' if action == 'reject' else 'requesting more information'
                raise serializers.ValidationError({
                    'proposed_staff_reply': f'Reply is required when proposing {action_text}.'
                })
        return data


class StewardSubmissionSerializer(serializers.ModelSerializer):
    """
    Enhanced serializer for steward view of submissions with all needed data.
    Context-aware: Uses lightweight serializers for list views to avoid N+1 queries.
    """
    user_details = serializers.SerializerMethodField()
    contribution_type_details = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    contribution = serializers.SerializerMethodField()
    assigned_to = serializers.PrimaryKeyRelatedField(read_only=True)
    # Proposal fields
    proposed_by_details = serializers.SerializerMethodField()
    proposed_user_details = serializers.SerializerMethodField()
    has_proposal = serializers.SerializerMethodField()
    proposed_template_name = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()
    rubric_review = serializers.SerializerMethodField()
    project_contribution = LightProjectContributionSerializer(read_only=True)

    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_details',
                  'contribution_date', 'notes', 'title', 'state', 'state_display', 'staff_reply',
                  'reviewed_by', 'reviewed_at', 'assigned_to',
                  'evidence_items', 'proposed_points',
                  # Proposal fields
                  'proposed_action', 'proposed_contribution_type', 'proposed_user', 'proposed_user_details',
                  'proposed_staff_reply', 'proposed_create_highlight',
                  'proposed_highlight_title', 'proposed_highlight_description',
                  'proposed_by', 'proposed_at', 'proposed_by_details', 'has_proposal',
                  'proposed_confidence', 'proposed_template', 'proposed_template_name',
                  'rubric_review',
                  'notes_count', 'is_interesting',
                  'has_appeal', 'appeal_reason',
                  'created_at', 'updated_at', 'last_edited_at', 'converted_contribution', 'contribution',
                  'mission', 'project_contribution', 'milestone_version']
        # Every model-backed field is read-only: this serializer only renders
        # steward review data. State transitions, proposals and reviewer
        # attribution are written exclusively by the viewset's custom actions,
        # never through serializer input.
        read_only_fields = ['id', 'user', 'contribution_type', 'contribution_date', 'notes',
                            'title', 'state', 'staff_reply', 'reviewed_by', 'reviewed_at',
                            'proposed_action', 'proposed_contribution_type', 'proposed_user',
                            'proposed_staff_reply', 'proposed_create_highlight',
                            'proposed_highlight_title', 'proposed_highlight_description',
                            'proposed_by', 'proposed_at', 'proposed_confidence', 'proposed_template',
                            'created_at', 'updated_at', 'last_edited_at', 'proposed_points',
                            'is_interesting', 'has_appeal', 'appeal_reason',
                            'converted_contribution', 'mission', 'milestone_version']

    def get_user_details(self, obj):
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            data = LightUserSerializer(obj.user).data
        else:
            data = UserSerializer(obj.user, context=self.context).data

        # Always include social connections so stewards can see which networks
        # the user has linked, even on the paginated list view that uses the
        # light serializer.
        from social_connections.serializers import (
            DiscordConnectionSerializer,
            GitHubConnectionSerializer,
            TwitterConnectionSerializer,
        )

        def _get(related_name, serializer_class):
            try:
                connection = getattr(obj.user, related_name)
            except Exception:
                return None
            if connection is None:
                return None
            return serializer_class(connection).data

        data.setdefault('github_connection', _get('githubconnection', GitHubConnectionSerializer))
        data.setdefault('twitter_connection', _get('twitterconnection', TwitterConnectionSerializer))
        data.setdefault('discord_connection', _get('discordconnection', DiscordConnectionSerializer))
        return data

    def get_contribution_type_details(self, obj):
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightContributionTypeSerializer(obj.contribution_type).data
        return ContributionTypeSerializer(obj.contribution_type, context=self.context).data

    def get_evidence_items(self, obj):
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True, context=self.context).data

    def get_contribution(self, obj):
        if obj.converted_contribution:
            if self.context.get('use_light_serializers', False):
                contribution = obj.converted_contribution
                highlight = next(iter(contribution.highlights.all()), None)
                return {
                    'id': contribution.id,
                    'user': contribution.user_id,
                    'user_details': LightUserSerializer(contribution.user).data,
                    'contribution_type': contribution.contribution_type_id,
                    'contribution_type_name': contribution.contribution_type.name,
                    'contribution_type_min_points': contribution.contribution_type.min_points,
                    'contribution_type_max_points': contribution.contribution_type.max_points,
                    'contribution_type_details': LightContributionTypeSerializer(
                        contribution.contribution_type
                    ).data,
                    'points': contribution.points,
                    'frozen_global_points': contribution.frozen_global_points,
                    'multiplier_at_creation': str(contribution.multiplier_at_creation) if contribution.multiplier_at_creation is not None else None,
                    'contribution_date': contribution.contribution_date,
                    'notes': contribution.notes,
                    'title': contribution.title,
                    'project_contribution': (
                        LightProjectContributionSerializer(contribution.project_contribution).data
                        if contribution.project_contribution else None
                    ),
                    'milestone_version': contribution.milestone_version,
                    'highlight': {
                        'title': highlight.title,
                        'description': highlight.description
                    } if highlight else None,
                    'is_highlighted': bool(highlight),
                    'mission': LightMissionSerializer(contribution.mission).data if contribution.mission else None,
                    'created_at': contribution.created_at,
                    'updated_at': contribution.updated_at,
                }

            from .models import ContributionHighlight
            contrib_context = self.context.copy()
            contrib_context['use_light_serializers'] = True
            contribution_data = ContributionSerializer(obj.converted_contribution, context=contrib_context).data

            try:
                highlight = ContributionHighlight.objects.get(contribution=obj.converted_contribution)
                contribution_data['is_highlighted'] = True
                contribution_data['highlight'] = {
                    'title': highlight.title,
                    'description': highlight.description
                }
            except ContributionHighlight.DoesNotExist:
                contribution_data['is_highlighted'] = False
                contribution_data['highlight'] = None

            contribution_data['contribution_type_details'] = LightContributionTypeSerializer(
                obj.converted_contribution.contribution_type
            ).data
            contribution_data['project_contribution'] = (
                LightProjectContributionSerializer(obj.converted_contribution.project_contribution).data
                if obj.converted_contribution.project_contribution else None
            )

            return contribution_data
        return None

    def get_proposed_by_details(self, obj):
        if obj.proposed_by:
            return {
                'name': obj.proposed_by.name or obj.proposed_by.address[:10] + '...',
                'address': obj.proposed_by.address,
            }
        return None

    def get_proposed_user_details(self, obj):
        if obj.proposed_user:
            return {
                'id': obj.proposed_user.id,
                'name': obj.proposed_user.name,
                'address': obj.proposed_user.address,
                'display_name': obj.proposed_user.name or f"{obj.proposed_user.address[:6]}...{obj.proposed_user.address[-4:]}",
                'profile_image_url': obj.proposed_user.profile_image_url,
            }
        return None

    def get_has_proposal(self, obj):
        return obj.proposed_action is not None

    def get_proposed_template_name(self, obj):
        if obj.proposed_template:
            return obj.proposed_template.label
        return None

    def get_rubric_review(self, obj):
        try:
            review = obj.project_milestone_review
        except ProjectMilestoneReview.DoesNotExist:
            return None
        return ProjectMilestoneReviewSerializer(review).data

    def get_notes_count(self, obj):
        if hasattr(obj, 'internal_notes_count'):
            return obj.internal_notes_count

        # Use prefetched data if available
        if hasattr(obj, '_prefetched_objects_cache') and 'internal_notes' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['internal_notes'])
        return obj.internal_notes.count()

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if instance.mission:
            use_light = self.context.get('use_light_serializers', True)
            if use_light:
                ret['mission'] = LightMissionSerializer(instance.mission).data
            else:
                ret['mission'] = MissionSerializer(instance.mission, context=self.context).data

        return ret


class MissionSerializer(serializers.ModelSerializer):
    is_active = serializers.SerializerMethodField()
    contribution_type_details = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    submissions_remaining = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    user_submission_count = serializers.SerializerMethodField()
    user_submissions_remaining = serializers.SerializerMethodField()
    user_is_full = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id', 'name', 'description',
            'start_date', 'end_date', 'contribution_type',
            'contribution_type_details',
            'max_submissions', 'max_submissions_per_user',
            'submission_count', 'submissions_remaining', 'is_full',
            'user_submission_count', 'user_submissions_remaining',
            'user_is_full',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_active(self, obj):
        return obj.is_active()

    def get_contribution_type_details(self, obj):
        contribution_type = obj.contribution_type
        data = LightContributionTypeSerializer(contribution_type).data
        submission_count = getattr(obj, 'contribution_type_submission_count', None)
        max_submissions = contribution_type.max_submissions
        if submission_count is None:
            submission_count = contribution_type.get_submission_count()

        data['submission_count'] = submission_count
        data['submissions_remaining'] = (
            None
            if max_submissions is None
            else max(max_submissions - submission_count, 0)
        )
        data['is_full'] = (
            max_submissions is not None
            and submission_count >= max_submissions
        )
        return data

    def get_submission_count(self, obj):
        return obj.get_submission_count()

    def get_submissions_remaining(self, obj):
        return obj.submissions_remaining()

    def get_is_full(self, obj):
        return obj.is_full()

    def _current_user(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            return user
        return None

    def get_user_submission_count(self, obj):
        return obj.get_user_submission_count(self._current_user())

    def get_user_submissions_remaining(self, obj):
        return obj.user_submissions_remaining(self._current_user())

    def get_user_is_full(self, obj):
        return obj.is_full_for_user(self._current_user())


class StartupRequestListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing startup requests.
    """
    class Meta:
        model = StartupRequest
        fields = ['id', 'title', 'short_description', 'is_active', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class StartupRequestDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for startup request detail view.
    Includes all fields for rendering the full page with markdown and documents.
    """
    class Meta:
        model = StartupRequest
        fields = [
            'id', 'title', 'description', 'short_description',
            'documents', 'is_active', 'order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeaturedContentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_address = serializers.CharField(source='user.address', read_only=True)
    user_profile_image_url = serializers.SerializerMethodField()
    featured_profile_image_url = serializers.CharField(
        source='user_profile_image_url',
        read_only=True,
    )
    link = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedContent
        fields = ['id', 'content_type', 'title', 'description', 'author',
                  'hero_image_url', 'hero_image_url_tablet', 'hero_image_url_mobile',
                  'hero_placements',
                  'url', 'link',
                  'user', 'user_name', 'user_address', 'user_profile_image_url',
                  'featured_profile_image_url',
                  'contribution', 'status', 'order', 'created_at']

    def get_user_profile_image_url(self, obj):
        """Return the FeaturedContent's user_profile_image_url if set, otherwise fall back to user's profile_image_url."""
        if obj.user_profile_image_url:
            return obj.user_profile_image_url
        if obj.user and obj.user.profile_image_url:
            return obj.user.profile_image_url
        return ''

    def get_link(self, obj):
        return obj.get_link()


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ['id', 'alert_type', 'icon', 'text', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']
