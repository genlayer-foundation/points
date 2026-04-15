from django.db import transaction
from rest_framework import serializers
from .models import ContributionType, Contribution, SubmittedContribution, Evidence, ContributionHighlight, Mission, StartupRequest, SubmissionNote, FeaturedContent, Alert, EvidenceURLType
from users.serializers import UserSerializer, LightUserSerializer
from users.models import User
from stewards.models import ReviewTemplate
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
    evidence_items = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

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

    class Meta:
        model = ContributionType
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'min_points', 'max_points',
            'current_multiplier', 'is_submittable', 'examples', 'required_social_accounts',
            'accepted_evidence_url_types',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_current_multiplier(self, obj):
        """Get the current multiplier value for this contribution type."""
        from leaderboard.models import GlobalLeaderboardMultiplier
        try:
            return float(GlobalLeaderboardMultiplier.get_current_multiplier_value(obj))
        except Exception:
            return 1.0

    def get_accepted_evidence_url_types(self, obj):
        """Return accepted evidence URL types with patterns for client-side detection.

        If the M2M is empty (meaning all types are accepted), returns all
        evidence URL types so the frontend always has pattern data for
        client-side detection, badges, and ownership prompts.
        """
        url_types = obj.accepted_evidence_url_types.all()
        if not url_types.exists():
            url_types = EvidenceURLType.objects.all().order_by('order')
        return EvidenceURLTypeSerializer(url_types, many=True).data



class ContributionSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    contribution_type_min_points = serializers.ReadOnlyField(source='contribution_type.min_points')
    contribution_type_max_points = serializers.ReadOnlyField(source='contribution_type.max_points')
    contribution_type_details = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    highlight = serializers.SerializerMethodField()

    class Meta:
        model = Contribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name',
                  'contribution_type_min_points', 'contribution_type_max_points', 'contribution_type_details',
                  'points', 'frozen_global_points', 'multiplier_at_creation', 'contribution_date',
                  'evidence_items', 'notes', 'title', 'highlight', 'mission', 'created_at', 'updated_at']
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
    recaptcha = ReCaptchaField(required=False)  # Required only on create, handled in validate()

    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name',
                  'contribution_type_details', 'contribution_date', 'notes', 'title', 'state', 'state_display',
                  'staff_reply', 'reviewed_by', 'reviewed_at', 'evidence_items', 'can_edit',
                  'proposed_points', 'converted_contribution', 'contribution', 'mission',
                  'created_at', 'updated_at', 'last_edited_at', 'recaptcha']
        read_only_fields = ['id', 'user', 'state', 'staff_reply', 'reviewed_by',
                          'reviewed_at', 'created_at', 'updated_at', 'last_edited_at',
                          'proposed_points', 'converted_contribution']

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
        accepted_types = None
        if contribution_type:
            accepted_qs = contribution_type.accepted_evidence_url_types.all()
            if accepted_qs.exists():
                accepted_types = set(accepted_qs.values_list('id', flat=True))

        errors = []
        for i, item in enumerate(evidence_validated):
            url = item.get('url', '')
            if not url:
                continue

            # 1. Auto-detect URL type
            url_type = detect_url_type(url)
            item['_detected_url_type'] = url_type

            # 2. URL type mismatch check
            if (accepted_types is not None
                    and url_type
                    and not url_type.is_generic
                    and url_type.id not in accepted_types):
                accepted_names = list(
                    contribution_type.accepted_evidence_url_types
                    .values_list('name', flat=True)
                )
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
            require_at_least_one=True,
            contribution_type=contribution_type,
            user=user,
        )

        with transaction.atomic():
            instance = super().create(validated_data)
            for evidence_data in evidence_validated:
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
            user = self.context['request'].user
            contribution_type = (
                validated_data.get('contribution_type')
                or instance.contribution_type
            )
            evidence_items_validated = self._validate_evidence_items(
                evidence_items_data,
                require_at_least_one=True,
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
    
    def validate(self, data):
        """Validate the review action and required fields."""
        action = data.get('action')
        
        if action == 'accept':
            if not data.get('points'):
                raise serializers.ValidationError({
                    'points': 'Points are required when accepting a submission.'
                })
            
            # Validate points are within contribution type limits
            contribution_type = data.get('contribution_type')
            if contribution_type:
                points = data.get('points')
                if points < contribution_type.min_points or points > contribution_type.max_points:
                    raise serializers.ValidationError({
                        'points': f'Points must be between {contribution_type.min_points} and {contribution_type.max_points} for {contribution_type.name}.'
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


class SubmissionNoteSerializer(serializers.ModelSerializer):
    """Serializer for CRM notes on submissions."""
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = SubmissionNote
        fields = ['id', 'user', 'user_name', 'message', 'is_proposal', 'data', 'created_at']
        read_only_fields = ['id', 'user', 'user_name', 'is_proposal', 'data', 'created_at']

    def get_user_name(self, obj):
        return obj.user.name or obj.user.address[:10] + '...'


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

    def validate(self, data):
        action = data.get('proposed_action')
        if action == 'accept':
            if not data.get('proposed_points'):
                raise serializers.ValidationError({
                    'proposed_points': 'Points are required when proposing acceptance.'
                })
            ct = data.get('proposed_contribution_type')
            if ct:
                pts = data['proposed_points']
                if pts < ct.min_points or pts > ct.max_points:
                    raise serializers.ValidationError({
                        'proposed_points': f'Points must be between {ct.min_points} and {ct.max_points} for {ct.name}.'
                    })
            if data.get('proposed_create_highlight'):
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
    has_proposal = serializers.SerializerMethodField()
    proposed_template_name = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_details',
                  'contribution_date', 'notes', 'title', 'state', 'state_display', 'staff_reply',
                  'reviewed_by', 'reviewed_at', 'assigned_to',
                  'evidence_items', 'proposed_points',
                  # Proposal fields
                  'proposed_action', 'proposed_contribution_type', 'proposed_user',
                  'proposed_staff_reply', 'proposed_create_highlight',
                  'proposed_highlight_title', 'proposed_highlight_description',
                  'proposed_by', 'proposed_at', 'proposed_by_details', 'has_proposal',
                  'proposed_confidence', 'proposed_template', 'proposed_template_name',
                  'notes_count',
                  'created_at', 'updated_at', 'last_edited_at', 'converted_contribution', 'contribution',
                  'mission']
        read_only_fields = ['id', 'created_at', 'updated_at', 'proposed_points']

    def get_user_details(self, obj):
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightUserSerializer(obj.user).data
        return UserSerializer(obj.user, context=self.context).data

    def get_contribution_type_details(self, obj):
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightContributionTypeSerializer(obj.contribution_type).data
        return ContributionTypeSerializer(obj.contribution_type, context=self.context).data

    def get_evidence_items(self, obj):
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True, context=self.context).data

    def get_contribution(self, obj):
        if self.context.get('use_light_serializers', False):
            return None

        if obj.converted_contribution:
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

            return contribution_data
        return None

    def get_proposed_by_details(self, obj):
        if obj.proposed_by:
            return {
                'name': obj.proposed_by.name or obj.proposed_by.address[:10] + '...',
                'address': obj.proposed_by.address,
            }
        return None

    def get_has_proposal(self, obj):
        return obj.proposed_action is not None

    def get_proposed_template_name(self, obj):
        if obj.proposed_template:
            return obj.proposed_template.label
        return None

    def get_notes_count(self, obj):
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

    class Meta:
        model = Mission
        fields = [
            'id', 'name', 'description',
            'start_date', 'end_date', 'contribution_type',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_active(self, obj):
        return obj.is_active()


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
    link = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedContent
        fields = ['id', 'content_type', 'title', 'description', 'author',
                  'hero_image_url', 'hero_image_url_tablet', 'hero_image_url_mobile',
                  'url', 'link',
                  'user', 'user_name', 'user_address', 'user_profile_image_url',
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
