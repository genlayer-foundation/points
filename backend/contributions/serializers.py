from rest_framework import serializers
from .models import ContributionType, Contribution, SubmittedContribution, Evidence, ContributionHighlight, Mission
from users.serializers import UserSerializer
from users.models import User
from utils.serializers import LightUserSerializer, LightContributionTypeSerializer
import decimal


class ContributionTypeSerializer(serializers.ModelSerializer):
    current_multiplier = serializers.SerializerMethodField()
    category = serializers.CharField(source='category.slug', read_only=True)
    
    class Meta:
        model = ContributionType
        fields = [
            'id', 'name', 'description', 'category', 'min_points', 'max_points',
            'current_multiplier', 'is_submittable', 'examples',
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
                  'evidence_items', 'notes', 'highlight', 'created_at', 'updated_at']
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
        """Override to_representation to handle invalid decimal values gracefully"""
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
            
        return ret


class EvidenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Evidence
        fields = ['id', 'description', 'url', 'created_at']
        read_only_fields = ['id', 'created_at']


class SubmittedEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for evidence items belonging to submitted contributions."""
    id = serializers.IntegerField(required=False)  # Optional: present for existing evidence, absent for new

    class Meta:
        model = Evidence
        fields = ['id', 'description', 'url', 'created_at']
        read_only_fields = ['created_at']


class SubmittedContributionSerializer(serializers.ModelSerializer):
    """
    Serializer for submitted contributions (user submissions).
    Context-aware: Uses lightweight serializers for list views to avoid N+1 queries.
    Supports formset-style evidence updates: evidence items with 'id' are updated,
    items without 'id' are created, and items not in the list are deleted.
    """
    user_details = serializers.SerializerMethodField()
    contribution_type_name = serializers.ReadOnlyField(source='contribution_type.name')
    contribution_type_details = serializers.SerializerMethodField()
    evidence_items = serializers.SerializerMethodField()
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    can_edit = serializers.SerializerMethodField()
    contribution = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_name',
                  'contribution_type_details', 'contribution_date', 'notes', 'state', 'state_display',
                  'staff_reply', 'reviewed_by', 'reviewed_at', 'evidence_items', 'can_edit',
                  'suggested_points', 'converted_contribution', 'contribution',
                  'created_at', 'updated_at', 'last_edited_at']
        read_only_fields = ['id', 'user', 'state', 'staff_reply', 'reviewed_by',
                          'reviewed_at', 'created_at', 'updated_at', 'last_edited_at',
                          'suggested_points', 'converted_contribution']

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

    def create(self, validated_data):
        """Create a new submission with the current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Update submission with formset-style evidence handling.
        Evidence items with 'id' are updated, items without 'id' are created,
        and items not in the list are deleted.
        """
        # Extract evidence items from initial_data (raw request data)
        # since evidence_items is a SerializerMethodField and not in validated_data
        evidence_items_data = self.initial_data.get('evidence_items', None)

        # Update the submission fields
        instance = super().update(instance, validated_data)

        # Handle evidence updates if provided (formset pattern)
        if evidence_items_data is not None:
            # Validate and serialize the evidence items
            evidence_serializer = SubmittedEvidenceSerializer(data=evidence_items_data, many=True)
            if not evidence_serializer.is_valid():
                raise serializers.ValidationError({'evidence_items': evidence_serializer.errors})

            evidence_items_validated = evidence_serializer.validated_data

            # Get existing evidence IDs
            existing_evidence_ids = set(instance.evidence_items.values_list('id', flat=True))

            # Track which evidence items are being kept/updated
            processed_evidence_ids = set()

            for evidence_data in evidence_items_validated:
                evidence_id = evidence_data.get('id')

                if evidence_id:
                    # Update existing evidence
                    try:
                        evidence = Evidence.objects.get(
                            id=evidence_id,
                            submitted_contribution=instance
                        )
                        # Update fields
                        evidence.description = evidence_data.get('description', evidence.description)
                        evidence.url = evidence_data.get('url', evidence.url)
                        evidence.save()
                        processed_evidence_ids.add(evidence_id)
                    except Evidence.DoesNotExist:
                        # Evidence doesn't belong to this submission - ignore or raise error
                        pass
                else:
                    # Create new evidence
                    Evidence.objects.create(
                        submitted_contribution=instance,
                        description=evidence_data.get('description', ''),
                        url=evidence_data.get('url', '')
                    )

            # Delete evidence items that weren't in the submitted list
            evidence_to_delete = existing_evidence_ids - processed_evidence_ids
            if evidence_to_delete:
                Evidence.objects.filter(id__in=evidence_to_delete).delete()

        return instance


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
    contribution_date = serializers.DateTimeField(source='contribution.contribution_date', read_only=True)

    class Meta:
        model = ContributionHighlight
        fields = ['id', 'title', 'description', 'contribution', 'contribution_details',
                  'user_name', 'user_address', 'user_profile_image_url',
                  'user_validator', 'user_builder', 'user_steward',
                  'user_has_validator_waitlist', 'user_has_builder_welcome',
                  'contribution_type_name', 'contribution_type_id', 'contribution_type_slug',
                  'contribution_type_category', 'contribution_points', 'contribution_date', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_contribution_details(self, obj):
        """
        Return lightweight contribution details to avoid N+1 queries.
        Most needed info is already in the flat fields above.
        """
        from utils.serializers import LightContributionSerializer
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

    class Meta:
        model = SubmittedContribution
        fields = ['id', 'user', 'user_details', 'contribution_type', 'contribution_type_details',
                  'contribution_date', 'notes', 'state', 'state_display', 'staff_reply',
                  'reviewed_by', 'reviewed_at', 'evidence_items', 'suggested_points',
                  'created_at', 'updated_at', 'last_edited_at', 'converted_contribution', 'contribution']
        read_only_fields = ['id', 'created_at', 'updated_at', 'suggested_points']

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
        # Stewards need evidence to make informed review decisions
        evidence_items = obj.evidence_items.all().order_by('-created_at')
        return EvidenceSerializer(evidence_items, many=True, context=self.context).data

    def get_contribution(self, obj):
        """Get the created contribution if submission was accepted."""
        # Skip for list views
        if self.context.get('use_light_serializers', False):
            return None

        if obj.converted_contribution:
            from .models import ContributionHighlight
            # Use light context to avoid deep nesting
            contrib_context = self.context.copy()
            contrib_context['use_light_serializers'] = True
            contribution_data = ContributionSerializer(obj.converted_contribution, context=contrib_context).data

            # Add highlight info if exists
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

            # Add contribution type details with light serializer
            contribution_data['contribution_type_details'] = LightContributionTypeSerializer(
                obj.converted_contribution.contribution_type
            ).data

            return contribution_data
        return None


class MissionSerializer(serializers.ModelSerializer):
    contribution_type_details = ContributionTypeSerializer(source='contribution_type', read_only=True)
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            'id', 'name', 'description',
            'start_date', 'end_date', 'contribution_type', 'contribution_type_details',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_active(self, obj):
        return obj.is_active()
