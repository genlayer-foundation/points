from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from utils.models import BaseModel
from utils.dates import utc_week_bounds
import decimal
import os
import uuid

from tally.middleware.logging_utils import get_app_logger

logger = get_app_logger('contributions')


def default_featured_hero_placements():
    return ['overview', 'builder', 'community']


class Category(BaseModel):
    """
    Defines a user category (Validator, Builder, Steward).
    Each category has its own profile model and contribution types.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    profile_model = models.CharField(
        max_length=100, 
        blank=True,
        help_text="App.Model reference for the profile model (e.g., 'validators.Validator')"
    )
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

def evidence_file_path(instance, filename):
    """Generate a unique file path for evidence files."""
    # Generate a unique path for each file based on user and timestamp
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if instance.contribution:
        user_id = instance.contribution.user.id
        folder_type = 'contribution'
        parent_id = instance.contribution.id
    elif instance.submitted_contribution:
        user_id = instance.submitted_contribution.user.id
        folder_type = 'submission'
        parent_id = instance.submitted_contribution.id
    else:
        user_id = 'unassigned'
        folder_type = 'unknown'
        parent_id = 'no_parent'
    
    # Use timestamp instead of instance.id since it's not available yet
    folder = f"evidence/{folder_type}/{user_id}/{parent_id}"
    # Add timestamp to filename to ensure uniqueness
    name, ext = os.path.splitext(filename)
    filename = f"{name}_{timestamp}{ext}"
    
    return os.path.join(folder, filename)


class ContributionType(BaseModel):
    """
    Represents different types of contributions that participants can make.
    Examples: Node Runner, Uptime, Asimov, Blog Post, etc.
    """
    REVIEW_FLOW_STANDARD = 'standard'
    REVIEW_FLOW_BUILDER_PROJECT = 'builder_project'
    REVIEW_FLOW_CHOICES = [
        (REVIEW_FLOW_STANDARD, 'Standard'),
        (REVIEW_FLOW_BUILDER_PROJECT, 'Builder Project'),
    ]
    BUILDER_CATEGORY_SLUG = 'builder'
    BUILDER_DEFAULT_ESCALATION_THRESHOLD_POINTS = 400
    BUILDER_REVIEW_DEFAULT_FIELDS = {
        'requires_ai_review',
        'escalation_threshold_points',
    }

    def __init__(self, *args, **kwargs):
        explicit_review_fields = self.BUILDER_REVIEW_DEFAULT_FIELDS.intersection(
            kwargs
        )
        super().__init__(*args, **kwargs)
        self._explicit_review_fields_on_create = explicit_review_fields

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True, help_text="Unique identifier for this contribution type")
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='contribution_types',
        null=True,  # Temporarily nullable for migration
        blank=True,
        help_text="The category this contribution type belongs to"
    )
    min_points = models.PositiveIntegerField(default=0, help_text="Minimum points allowed for this contribution type")
    max_points = models.PositiveIntegerField(default=100, help_text="Maximum points allowed for this contribution type")
    rubric_extra_points = models.PositiveIntegerField(
        default=2,
        help_text="Points awarded per verified extra in the Builder Project rubric."
    )
    is_default = models.BooleanField(default=False, help_text="Include this contribution type by default when creating validators")
    is_submittable = models.BooleanField(default=True, help_text="Whether this contribution type can be submitted by users")
    review_flow = models.CharField(
        max_length=30,
        choices=REVIEW_FLOW_CHOICES,
        default=REVIEW_FLOW_STANDARD,
        help_text=(
            "Steward review workflow for this contribution type. "
            "Builder Project flow requires structured rubric proposals."
        ),
    )
    max_submissions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Maximum number of non-rejected, non-canceled submissions allowed "
            "for this contribution type. Leave blank for unlimited."
        ),
    )
    max_submissions_per_user_per_week = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Maximum submissions each user may create for this contribution "
            "type per Monday-Sunday UTC week. Every submission state counts. "
            "Leave blank for unlimited."
        ),
    )
    requires_ai_review = models.BooleanField(
        default=False,
        help_text="Require AI review before tier-1 stewards can review pending submissions.",
    )
    escalation_threshold_points = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Escalate tier-1 accepts when rounded points after the multiplier "
            "meet or exceed this value. Leave blank to disable escalation."
        ),
    )
    show_in_contributions = models.BooleanField(
        default=False,
        help_text=(
            "Show this contribution type in the public Contributions list even when it is not directly submittable. "
            "Intended for informational / mission-host types whose missions carry the actual submissions."
        ),
    )
    examples = models.JSONField(
        default=list,
        blank=True,
        help_text="Example entries for this contribution type (array of short strings)"
    )
    required_social_accounts = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required social accounts for submission: 'twitter', 'discord', 'github'"
    )
    required_discord_roles = models.ManyToManyField(
        'social_connections.DiscordRole',
        blank=True,
        related_name='required_by_contribution_types',
        help_text=(
            "Discord guild roles required for submission. "
            "If set, the submitter must have at least one of these roles."
        ),
    )
    accepted_evidence_url_types = models.ManyToManyField(
        'EvidenceURLType',
        blank=True,
        related_name='contribution_types',
        help_text="Accepted evidence URL types. Empty means all types are accepted."
    )
    required_evidence_url_types = models.ManyToManyField(
        'EvidenceURLType',
        blank=True,
        related_name='required_by_contribution_types',
        help_text=(
            "If set, at least one submitted evidence URL must match one of "
            "these types. Required types are implicitly accepted."
        ),
    )
    required_evidence_url_type_groups = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of EvidenceURLType slug groups, e.g. "
            '[["studio-contract", "github-repo"], ["genlayer-explorer-contract"]]. '
            "A submission must have at least one evidence URL matching each group "
            "(AND across groups, OR within a group). Empty = no group requirement."
        ),
    )

    class Meta:
        ordering = ['category__name', 'name']

    def __str__(self):
        category_name = self.category.name if self.category else "No Category"
        return f"{category_name} - {self.name}"

    def get_submission_count(self):
        """
        Count submissions that consume this contribution type's capacity.
        """
        annotated_count = getattr(self, 'submission_count', None)
        if annotated_count is not None:
            return annotated_count
        return self.submitted_contributions.exclude(
            state__in=['rejected', 'canceled']
        ).count()

    def submissions_remaining(self):
        if self.max_submissions is None:
            return None
        return max(self.max_submissions - self.get_submission_count(), 0)

    def is_full(self):
        return (
            self.max_submissions is not None
            and self.get_submission_count() >= self.max_submissions
        )

    def get_user_weekly_submission_count(self, user, now=None):
        """Count a user's submissions in the current Monday-Sunday UTC week.

        State is deliberately not filtered: pending, accepted, rejected,
        canceled, and more-info submissions all consume the same weekly quota.
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        annotated_count = getattr(self, 'user_weekly_submission_count', None)
        if annotated_count is not None and now is None:
            return annotated_count
        week_start, week_end = utc_week_bounds(now)
        return self.submitted_contributions.filter(
            user=user,
            created_at__gte=week_start,
            created_at__lt=week_end,
        ).count()

    def user_weekly_submissions_remaining(self, user, now=None):
        if self.max_submissions_per_user_per_week is None:
            return None
        submission_count = self.get_user_weekly_submission_count(user, now=now)
        if submission_count is None:
            return None
        return max(self.max_submissions_per_user_per_week - submission_count, 0)

    def is_weekly_full_for_user(self, user, now=None):
        if self.max_submissions_per_user_per_week is None:
            return False
        submission_count = self.get_user_weekly_submission_count(user, now=now)
        if submission_count is None:
            return False
        return submission_count >= self.max_submissions_per_user_per_week

    def save(self, *args, **kwargs):
        if self._state.adding and self.category_id:
            category = self._state.fields_cache.get('category')
            category_slug = (
                category.slug
                if category is not None
                else Category.objects.filter(pk=self.category_id)
                .values_list('slug', flat=True)
                .first()
            )
            if category_slug == self.BUILDER_CATEGORY_SLUG:
                if (
                    'requires_ai_review'
                    not in self._explicit_review_fields_on_create
                    and self.requires_ai_review is False
                ):
                    self.requires_ai_review = True
                if (
                    'escalation_threshold_points'
                    not in self._explicit_review_fields_on_create
                    and self.escalation_threshold_points is None
                ):
                    self.escalation_threshold_points = (
                        self.BUILDER_DEFAULT_ESCALATION_THRESHOLD_POINTS
                    )
        super().save(*args, **kwargs)
        
    def clean(self):
        """Validate the contribution type data."""
        super().clean()

        # Ensure max_points is greater than or equal to min_points
        if self.max_points < self.min_points:
            raise ValidationError("Maximum points must be greater than or equal to minimum points")

        # required_evidence_url_type_groups must be a list of non-empty slug
        # lists; the submission validator iterates it as list[list[str]], so a
        # flat list or stray string would silently create impossible rules.
        groups = self.required_evidence_url_type_groups or []
        if not isinstance(groups, list) or any(
            not isinstance(group, list) or not group
            or any(not isinstance(slug, str) or not slug for slug in group)
            for group in groups
        ):
            raise ValidationError({
                'required_evidence_url_type_groups':
                    'Expected a list of non-empty EvidenceURLType slug lists.'
            })
        flat_slugs = {slug for group in groups for slug in group}
        known = set(
            EvidenceURLType.objects.filter(slug__in=flat_slugs)
            .values_list('slug', flat=True)
        )
        unknown = sorted(flat_slugs - known)
        if unknown:
            raise ValidationError({
                'required_evidence_url_type_groups':
                    f'Unknown EvidenceURLType slugs: {", ".join(unknown)}'
            })


class Contribution(BaseModel):
    """
    Represents a specific contribution made by a user.
    Links user with a contribution type and records points.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='contributions'
    )
    contribution_type = models.ForeignKey(
        ContributionType,
        on_delete=models.CASCADE,
        related_name='contributions'
    )
    mission = models.ForeignKey(
        'Mission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contributions',
        help_text='Mission this contribution fulfills (optional)'
    )
    project_contribution = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='milestones',
        help_text='Accepted Projects contribution this milestone belongs to'
    )
    milestone_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Sequential milestone version within the linked project contribution'
    )
    points = models.PositiveIntegerField(default=0)
    frozen_global_points = models.PositiveIntegerField(
        default=0,
        help_text="Global points calculated as points × multiplier."
    )
    multiplier_at_creation = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True,
        help_text="Multiplier value at the time of contribution creation."
    )
    contribution_date = models.DateTimeField(null=True, blank=True, help_text="Date when the contribution was made. Defaults to creation time if not specified.")
    notes = models.TextField(blank=True)
    title = models.CharField(max_length=200, blank=True, default='', help_text="Optional title for the contribution")

    def __str__(self):
        return f"{self.user} - {self.contribution_type} - {self.points} points"

    class Meta:
        indexes = [
            models.Index(fields=['created_at'], name='contrib_created_idx'),
        ]

    def _points_require_current_range_validation(self):
        """Return whether the current contribution type range should apply.

        Contribution type ranges are current award rules, not retroactive
        constraints on historical awards. Existing rows keep their original
        points when a type's range changes, but changing either the points or
        the contribution type must satisfy the current range.
        """
        if self._state.adding or not self.pk:
            return True

        original = type(self).objects.filter(pk=self.pk).values(
            'points', 'contribution_type_id'
        ).first()
        if original is None:
            return True

        return (
            self.points != original['points']
            or self.contribution_type_id != original['contribution_type_id']
        )
    
    def clean(self):
        """
        Validate that there is an active multiplier for this contribution type,
        that the user is visible, and that the points are within the allowed range.
        """
        super().clean()
        
        # Import here to avoid circular imports
        from django.utils import timezone
        from leaderboard.models import GlobalLeaderboardMultiplier
        
        # Check if the user is visible
        if not self.user.visible:
            raise ValidationError(
                f"Cannot add contributions for user '{self.user.email}' as they are marked as not visible. "
                "Only visible users can have contributions."
            )
        
        # Set contribution_date to now if not provided
        if not self.contribution_date:
            self.contribution_date = timezone.now()
        
        # Validate new awards and point/type edits against the current range.
        # Unchanged historical awards remain valid if the type range later changes.
        points_out_of_range = (
            self.points < self.contribution_type.min_points
            or self.points > self.contribution_type.max_points
        )
        if points_out_of_range and self._points_require_current_range_validation():
            raise ValidationError(
                f"Points must be between {self.contribution_type.min_points} and {self.contribution_type.max_points} "
                f"for contribution type '{self.contribution_type}'."
            )
        
        try:
            # Check if there's an active multiplier for this contribution type on the contribution date
            # The method returns a tuple of (multiplier_obj, multiplier_value)
            _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                self.contribution_type,
                at_date=self.contribution_date
            )
            self.multiplier_at_creation = multiplier_value
        except GlobalLeaderboardMultiplier.DoesNotExist as e:
            if getattr(self, '_allow_missing_multiplier', False) and self.multiplier_at_creation is not None:
                return
            raise ValidationError(
                f"No active multiplier exists for contribution type '{self.contribution_type}' "
                f"on {self.contribution_date.strftime('%Y-%m-%d %H:%M')}. "
                "Please set a multiplier that covers this date before adding contributions."
            ) from e
    
    def save(self, *args, **kwargs):
        """
        Override save to validate and calculate frozen_global_points.
        """
        from django.utils import timezone
        
        # Set contribution_date if not set yet
        if not self.contribution_date:
            self.contribution_date = timezone.now()
            
        # Only run validation on new contributions
        if not self.pk:
            self.clean()
            
            # Calculate frozen_global_points
            try:
                if self.multiplier_at_creation:
                    self.frozen_global_points = round(self.points * float(self.multiplier_at_creation))
            except (decimal.InvalidOperation, TypeError, ValueError):
                # Handle corrupted data by resetting the multiplier
                self.multiplier_at_creation = 1.0
                self.frozen_global_points = self.points
                
        super().save(*args, **kwargs)


# Signal to validate multiplier_at_creation before save
@receiver(pre_save, sender=Contribution)
def validate_multiplier_at_creation(sender, instance, **kwargs):
    """
    Signal to validate multiplier_at_creation before saving a Contribution.
    This helps prevent corrupted decimal values.
    """
    if instance.multiplier_at_creation:
        try:
            # Test if we can convert the decimal value
            float(instance.multiplier_at_creation)
        except (decimal.InvalidOperation, TypeError, ValueError):
            # If conversion fails, reset the multiplier to 1.0
            logger.warning("Fixing corrupted multiplier_at_creation value")
            instance.multiplier_at_creation = 1.0
            instance.frozen_global_points = instance.points


@receiver(post_save, sender=Contribution)
def ensure_validator_profile_for_graduation_contribution(sender, instance, **kwargs):
    if kwargs.get('raw', False):
        return

    if getattr(instance.contribution_type, 'slug', None) != 'validator':
        return

    from validators.models import ensure_validator_profile

    ensure_validator_profile(instance.user)


def is_community_contribution(contribution):
    """Return whether a contribution belongs to the community category."""
    contribution_type = getattr(contribution, 'contribution_type', None)
    category = getattr(contribution_type, 'category', None)
    return bool(category and category.slug == 'community')


def is_community_social_task_completion(completion):
    """Return whether a social task completion belongs to the community category."""
    task = getattr(completion, 'task', None)
    category = getattr(task, 'category', None)
    return bool(category and category.slug == 'community')


class ContributionDiscordXPState(BaseModel):
    """
    Per-award Discord XP distribution state for community points. Each row
    tracks exactly one source: a community contribution or a community social
    task completion. This intentionally tracks award rows, not user aggregates,
    so each portal award has a clear manual Discord distribution status and
    audit trail.
    """
    STATUS_PENDING = 'pending'
    STATUS_DISTRIBUTED = 'distributed'
    STATUS_NEEDS_REVIEW = 'needs_review'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_DISTRIBUTED, 'Distributed'),
        (STATUS_NEEDS_REVIEW, 'Needs review'),
    ]

    contribution = models.OneToOneField(
        Contribution,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='discord_xp_state',
    )
    social_task_completion = models.OneToOneField(
        'social_tasks.SocialTaskCompletion',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='discord_xp_state',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    awarded_amount = models.PositiveIntegerField(default=0)
    distributed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    distributed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='discord_xp_states_distributed',
    )
    last_copied_at = models.DateTimeField(null=True, blank=True)
    last_copied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='discord_xp_states_copied',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'distributed_at'], name='contrib_xp_status_dist_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(contribution__isnull=False) & Q(social_task_completion__isnull=True)) |
                    (Q(contribution__isnull=True) & Q(social_task_completion__isnull=False))
                ),
                name='discord_xp_state_single_source',
            ),
        ]

    @property
    def recipient(self):
        if self.contribution_id:
            return self.contribution.user
        return self.social_task_completion.user

    @property
    def target_amount(self):
        if self.contribution_id:
            return int(self.contribution.frozen_global_points or 0)
        return int(self.social_task_completion.points_awarded or 0)

    @property
    def pending_amount(self):
        return max(self.target_amount - int(self.awarded_amount or 0), 0)

    @property
    def command(self):
        amount = self.pending_amount
        connection = getattr(self.recipient, 'discordconnection', None)
        username = getattr(connection, 'platform_username', '') if connection else ''
        if not username or amount <= 0:
            return ''
        username = username.lstrip('@')
        return f"/give-xp member:@{username} amount:{amount}"

    def clean(self):
        super().clean()
        if bool(self.contribution_id) == bool(self.social_task_completion_id):
            raise ValidationError(
                'Discord XP state must reference exactly one of contribution or social task completion.'
            )
        if self.contribution_id and not is_community_contribution(self.contribution):
            raise ValidationError('Discord XP state can only be created for community contributions.')
        if self.social_task_completion_id and not is_community_social_task_completion(self.social_task_completion):
            raise ValidationError('Discord XP state can only be created for community social task completions.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def refresh_status_from_contribution(self, save=True):
        """
        Reconcile state against the current frozen portal points (contribution
        frozen_global_points or social task points_awarded).
        Point reductions below manually-distributed XP are not auto-correctable
        in Discord, so they move to needs_review for steward visibility.
        """
        target = self.target_amount
        awarded = int(self.awarded_amount or 0)
        next_status = self.status

        if awarded > target:
            next_status = self.STATUS_NEEDS_REVIEW
        elif awarded == target:
            next_status = self.STATUS_DISTRIBUTED
        elif self.status != self.STATUS_NEEDS_REVIEW:
            next_status = self.STATUS_PENDING

        if next_status != self.status:
            self.status = next_status
            if save:
                self.save(update_fields=['status', 'updated_at'])

        return self.status

    def __str__(self):
        if self.contribution_id:
            return f"Discord XP for contribution {self.contribution_id}: {self.status}"
        return f"Discord XP for social task completion {self.social_task_completion_id}: {self.status}"


class DiscordXPDistributionEvent(BaseModel):
    """Audit row for manual Discord XP command copy/distribution actions."""
    ACTION_COPIED = 'copied'
    ACTION_DISTRIBUTED = 'distributed'
    ACTION_UNSET = 'unset'

    ACTION_CHOICES = [
        (ACTION_COPIED, 'Copied command'),
        (ACTION_DISTRIBUTED, 'Marked distributed'),
        (ACTION_UNSET, 'Unset distributed'),
    ]

    state = models.ForeignKey(
        ContributionDiscordXPState,
        on_delete=models.CASCADE,
        related_name='events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='discord_xp_distribution_events_made',
    )
    amount = models.PositiveIntegerField()
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at'], name='xp_event_action_created_idx'),
            models.Index(fields=['state', 'created_at'], name='xp_event_state_created_idx'),
        ]

    def __str__(self):
        return f"Discord XP event {self.id} for state {self.state_id}: {self.action}"


def sync_discord_xp_state_for_contribution(contribution):
    """
    Ensure only community contributions have Discord XP state.
    Non-community states are deleted defensively if a contribution changes type.
    """
    if not contribution.pk:
        return None

    if not is_community_contribution(contribution):
        ContributionDiscordXPState.objects.filter(contribution=contribution).delete()
        return None

    state, _ = ContributionDiscordXPState.objects.get_or_create(
        contribution=contribution,
        defaults={
            'status': ContributionDiscordXPState.STATUS_PENDING,
            'awarded_amount': 0,
        },
    )
    state.refresh_status_from_contribution(save=True)
    return state


@receiver(post_save, sender=Contribution)
def sync_contribution_discord_xp_state(sender, instance, **kwargs):
    sync_discord_xp_state_for_contribution(instance)


def sync_discord_xp_state_for_social_task_completion(completion):
    """
    Ensure only community social task completions have Discord XP state.
    Mirrors sync_discord_xp_state_for_contribution for the social task source.
    """
    if not completion.pk:
        return None

    if not is_community_social_task_completion(completion):
        ContributionDiscordXPState.objects.filter(social_task_completion=completion).delete()
        return None

    state, _ = ContributionDiscordXPState.objects.get_or_create(
        social_task_completion=completion,
        defaults={
            'status': ContributionDiscordXPState.STATUS_PENDING,
            'awarded_amount': 0,
        },
    )
    state.refresh_status_from_contribution(save=True)
    return state


# Lazy string sender: social_tasks already depends on contributions (Category
# FK), so contributions must not import social_tasks models at load time.
@receiver(post_save, sender='social_tasks.SocialTaskCompletion')
def sync_social_task_completion_discord_xp_state(sender, instance, **kwargs):
    sync_discord_xp_state_for_social_task_completion(instance)


class SubmittedContribution(BaseModel):
    """
    Represents a contribution submission that needs staff review.
    Once accepted, it will be converted to an actual Contribution.
    """
    PROPOSAL_STATUS_PENDING_REVIEW = 'pending_review'
    PROPOSAL_STATUS_QUESTIONED = 'questioned'
    PROPOSAL_REVIEW_STATUS_CHOICES = [
        (PROPOSAL_STATUS_PENDING_REVIEW, 'Pending Review'),
        (PROPOSAL_STATUS_QUESTIONED, 'Questioned'),
    ]

    # Use UUID for public-facing URLs
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic fields
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_contributions'
    )
    contribution_type = models.ForeignKey(
        ContributionType,
        on_delete=models.CASCADE,
        related_name='submitted_contributions'
    )
    mission = models.ForeignKey(
        'Mission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text='Mission that prompted this submission (optional)'
    )
    project_contribution = models.ForeignKey(
        'Contribution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='milestone_submissions',
        help_text='Accepted Projects contribution this milestone submission belongs to'
    )
    milestone_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Sequential milestone version within the linked project contribution'
    )
    contribution_date = models.DateTimeField(
        help_text="Date when the contribution was made"
    )
    notes = models.TextField(blank=True)
    title = models.CharField(max_length=200, blank=True, default='', help_text="Optional title for the submission")

    # State management
    STATE_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('canceled', 'Canceled'),
        ('more_info_needed', 'More Information Needed')
    ]
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default='pending'
    )
    
    # Proposed points for automatic submissions
    proposed_points = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Pre-calculated points for automatic submissions (e.g., node upgrades)"
    )
    
    # Review fields
    staff_reply = models.TextField(
        blank=True,
        help_text="Response from staff member"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_submissions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Assignment field - who should review this submission
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_submissions',
        help_text="Steward assigned to review this submission"
    )

    # Proposal fields - filled by stewards with 'propose' permission
    proposed_action = models.CharField(
        max_length=20,
        choices=[('accept', 'Accept'), ('reject', 'Reject'), ('more_info', 'More Info')],
        null=True,
        blank=True,
        help_text="Proposed review action"
    )
    proposed_contribution_type = models.ForeignKey(
        ContributionType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposed_submissions',
        help_text="Proposed contribution type for acceptance"
    )
    proposed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposed_contributions',
        help_text="Proposed user to assign the contribution to"
    )
    proposed_staff_reply = models.TextField(
        blank=True,
        help_text="Proposed staff reply message"
    )
    proposed_create_highlight = models.BooleanField(
        default=False,
        help_text="Whether to create a highlight for the contribution"
    )
    proposed_highlight_title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Proposed highlight title"
    )
    proposed_highlight_description = models.TextField(
        blank=True,
        help_text="Proposed highlight description"
    )
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submission_proposals',
        help_text="Steward who made the proposal"
    )
    proposed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the proposal was made"
    )
    proposed_confidence = models.CharField(
        max_length=10,
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        null=True,
        blank=True,
        help_text="Confidence level of the proposal"
    )
    proposed_template = models.ForeignKey(
        'stewards.ReviewTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proposed_submissions',
        help_text="Review template used for the proposal"
    )
    proposal_review_status = models.CharField(
        max_length=20,
        choices=PROPOSAL_REVIEW_STATUS_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text="Internal review status for the active proposal"
    )
    proposal_review_feedback = models.TextField(
        blank=True,
        help_text="Feedback sent to the proposer when a proposal is questioned"
    )
    proposal_questioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questioned_submission_proposals',
        help_text="Steward who questioned the active proposal"
    )
    proposal_questioned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the active proposal was questioned"
    )
    escalated_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the active proposal was escalated to a top-level steward.",
    )

    # Link to actual contribution when accepted
    converted_contribution = models.ForeignKey(
        'Contribution',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='source_submission'
    )

    # Internal flag for stewards to mark submissions worth revisiting.
    # Not exposed to submitters; used only for steward filtering.
    is_interesting = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Internal-only flag stewards can toggle to mark a submission as interesting."
    )
    gate_reviewed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True once AI review has checked this submission for automated gate rejects."
    )

    # Appeal fields - submitter can appeal a rejected submission once
    has_appeal = models.BooleanField(
        default=False,
        help_text="True once the submitter has appealed a rejection. Each submission can only be appealed once."
    )
    appeal_reason = models.TextField(
        blank=True,
        help_text="Reason provided by the submitter when appealing a rejection."
    )
    appealed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the submitter appealed the rejection."
    )

    # Edit tracking
    last_edited_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user} - {self.contribution_type} - {self.state}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Submitted Contribution"
        verbose_name_plural = "Submitted Contributions"
        indexes = [
            models.Index(fields=['created_at'], name='sub_created_idx'),
            models.Index(fields=['state', 'created_at'], name='sub_state_created_idx'),
            models.Index(fields=['state', 'reviewed_at'], name='sub_state_reviewed_idx'),
            models.Index(
                fields=['user', 'contribution_type', 'created_at'],
                name='sub_user_type_week_idx',
            ),
        ]


class SubmissionNote(BaseModel):
    """
    Internal CRM note on a submitted contribution.
    Visible to stewards only, not to the submitting user.
    Auto-generated notes record proposal history.
    """
    submitted_contribution = models.ForeignKey(
        SubmittedContribution,
        on_delete=models.CASCADE,
        related_name='internal_notes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submission_notes'
    )
    message = models.TextField()
    is_proposal = models.BooleanField(
        default=False,
        help_text="True for auto-generated proposal notes"
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured data: action, points, staff_reply, template_id, flags, confidence"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        prefix = "[Proposal] " if self.is_proposal else ""
        return f"{prefix}{self.user} on {self.submitted_contribution} at {self.created_at}"


class SubmissionStateTransition(BaseModel):
    """
    Append-only log of submission lifecycle events.

    Row state on SubmittedContribution is overwritten in place and re-open
    paths (resubmit, appeal, add-evidence) clear reviewed_by/reviewed_at, so
    this log is the only durable record of every state change and of
    review-field destruction. Rows are never updated or deleted.
    """
    EVENT_SUBMITTED = 'submitted'
    EVENT_REVIEW = 'review'
    EVENT_BULK_REJECT = 'bulk_reject'
    EVENT_GATE_REJECT = 'gate_reject'
    EVENT_EDITED = 'edited'
    EVENT_CANCELED = 'canceled'
    EVENT_APPEAL = 'appeal'
    EVENT_EVIDENCE_ADDED = 'evidence_added'
    EVENT_ESCALATED = 'escalated'
    EVENT_ADMIN = 'admin'
    EVENT_CHOICES = [
        (EVENT_SUBMITTED, 'Submitted'),
        (EVENT_REVIEW, 'Steward Review'),
        (EVENT_BULK_REJECT, 'Bulk Reject'),
        (EVENT_GATE_REJECT, 'AI Gate Reject'),
        (EVENT_EDITED, 'Edited by Submitter'),
        (EVENT_CANCELED, 'Canceled by Submitter'),
        (EVENT_APPEAL, 'Appeal'),
        (EVENT_EVIDENCE_ADDED, 'Evidence Added'),
        (EVENT_ESCALATED, 'Escalated'),
        (EVENT_ADMIN, 'Admin Edit'),
    ]

    submitted_contribution = models.ForeignKey(
        SubmittedContribution,
        on_delete=models.CASCADE,
        related_name='state_transitions'
    )
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    from_state = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="State before the event; empty for the initial submission"
    )
    to_state = models.CharField(max_length=20)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='submission_state_transitions',
        help_text="Who caused the event: submitter, steward, AI steward, or admin"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submitted_contribution', 'created_at'], name='sub_trans_sub_created_idx'),
            models.Index(fields=['event', 'created_at'], name='sub_trans_event_created_idx'),
        ]

    def __str__(self):
        return f"{self.event}: {self.from_state or '(new)'} -> {self.to_state} on {self.submitted_contribution_id}"

    @classmethod
    def record(cls, submission, event, from_state, actor=None, to_state=None):
        return cls.objects.create(
            submitted_contribution=submission,
            event=event,
            from_state=from_state or '',
            to_state=to_state if to_state is not None else submission.state,
            actor=actor,
        )


@receiver(post_save, sender=SubmittedContribution)
def log_submission_created(sender, instance, created, **kwargs):
    """Log the initial 'submitted' transition for every new submission."""
    # raw=True means fixture/loaddata replay: the dump already contains the
    # real transition rows, so synthesizing one here would corrupt the log.
    if created and not kwargs.get('raw', False):
        SubmissionStateTransition.record(
            instance,
            SubmissionStateTransition.EVENT_SUBMITTED,
            from_state='',
            actor=instance.user,
        )


class ProjectMilestoneReview(BaseModel):
    """
    Latest structured Builder Project rubric review for a submitted
    contribution. This can come from a proposal or a final steward decision.
    The existing SubmittedContribution proposed_* fields remain the queue
    summary; this record is the detailed rubric source of truth.
    """
    ACTION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('more_info', 'More Info'),
    ]
    CONFIDENCE_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    REVIEW_FLOW_CHOICES = [
        (ContributionType.REVIEW_FLOW_BUILDER_PROJECT, 'Builder Project'),
    ]

    submitted_contribution = models.OneToOneField(
        SubmittedContribution,
        on_delete=models.CASCADE,
        related_name='project_milestone_review',
    )
    proposer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_milestone_reviews',
    )
    review_flow = models.CharField(
        max_length=30,
        choices=REVIEW_FLOW_CHOICES,
        default=ContributionType.REVIEW_FLOW_BUILDER_PROJECT,
        editable=False,
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    confidence = models.CharField(
        max_length=10,
        choices=CONFIDENCE_CHOICES,
        null=True,
        blank=True,
    )
    gate_failures = models.JSONField(default=list, blank=True)
    sections = models.JSONField(default=dict, blank=True)
    extras = models.JSONField(default=list, blank=True)
    overall_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Builder Project Review"
        verbose_name_plural = "Builder Project Reviews"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(review_flow=ContributionType.REVIEW_FLOW_BUILDER_PROJECT),
                name='project_milestone_review_builder_flow',
            ),
        ]

    def __str__(self):
        return f"{self.submitted_contribution_id} - {self.action}"

    def clean(self):
        super().clean()
        if self.review_flow != ContributionType.REVIEW_FLOW_BUILDER_PROJECT:
            raise ValidationError({
                'review_flow': 'Project reviews must use the builder_project review flow.'
            })
        if self.submitted_contribution_id:
            contribution_types = [
                self.submitted_contribution.contribution_type,
                self.submitted_contribution.proposed_contribution_type,
            ]
            has_builder_project_type = any(
                contribution_type
                and contribution_type.review_flow == ContributionType.REVIEW_FLOW_BUILDER_PROJECT
                for contribution_type in contribution_types
            )
            if not has_builder_project_type:
                raise ValidationError({
                    'submitted_contribution': (
                        'Project reviews are only valid for Builder Project submissions or proposals.'
                    )
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class ReviewProposal(BaseModel):
    """Proposal snapshot enriched over time with question, decision, and reward metadata."""

    SOURCE_AI = 'ai'
    SOURCE_HUMAN = 'human'
    SOURCE_CHOICES = [
        (SOURCE_AI, 'AI'),
        (SOURCE_HUMAN, 'Human'),
    ]

    submitted_contribution = models.ForeignKey(
        SubmittedContribution,
        on_delete=models.CASCADE,
        related_name='review_proposals',
    )
    proposer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_proposal_snapshots',
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    service_account_name = models.CharField(max_length=255, blank=True, default='')

    action = models.CharField(max_length=20, choices=ProjectMilestoneReview.ACTION_CHOICES)
    points = models.PositiveIntegerField(null=True, blank=True)
    staff_reply = models.TextField(blank=True)
    confidence = models.CharField(
        max_length=10,
        choices=ProjectMilestoneReview.CONFIDENCE_CHOICES,
        null=True,
        blank=True,
    )
    gate_failures = models.JSONField(default=list, blank=True)
    sections = models.JSONField(default=dict, blank=True)
    extras = models.JSONField(default=list, blank=True)
    overall_reason = models.TextField(blank=True)
    synthesis = models.TextField(blank=True)

    questioned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questioned_review_proposal_snapshots',
    )
    questioned_at = models.DateTimeField(null=True, blank=True)
    question_feedback = models.TextField(blank=True)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='decided_review_proposal_snapshots',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    final_action = models.CharField(
        max_length=20,
        choices=ProjectMilestoneReview.ACTION_CHOICES,
        null=True,
        blank=True,
    )
    final_points = models.PositiveIntegerField(null=True, blank=True)
    final_sections = models.JSONField(default=dict, blank=True)
    reward_points = models.PositiveIntegerField(null=True, blank=True)
    reward_contribution = models.ForeignKey(
        'Contribution',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_reward_proposals',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submitted_contribution', 'created_at']),
            models.Index(fields=['proposer', 'decided_at']),
        ]

    def __str__(self):
        return f"{self.submitted_contribution_id} - {self.source} - {self.action}"


class AIReviewFeedback(BaseModel):
    """A steward's revisable, proposal-specific AI review assessment."""

    PROPOSAL_SOURCE_REVIEW = 'review_proposal'
    PROPOSAL_SOURCE_NOTE = 'submission_note'
    PROPOSAL_SOURCE_CHOICES = [
        (PROPOSAL_SOURCE_REVIEW, 'Review proposal'),
        (PROPOSAL_SOURCE_NOTE, 'Submission note'),
    ]
    VERDICT_CHOICES = [
        ('agree', 'Agree'),
        ('agree_with_corrections', 'Agree with corrections'),
        ('disagree', 'Disagree'),
    ]
    DECISION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('more_info', 'Request more information'),
        ('skip', 'Skip'),
    ]

    submitted_contribution = models.ForeignKey(
        SubmittedContribution,
        on_delete=models.CASCADE,
        related_name='ai_feedback',
    )
    review_proposal = models.ForeignKey(
        ReviewProposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_feedback',
    )
    proposal_source = models.CharField(
        max_length=20,
        choices=PROPOSAL_SOURCE_CHOICES,
    )
    proposal_source_id = models.PositiveBigIntegerField()
    proposal_ref = models.DateTimeField()
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_review_feedback',
    )
    verdict = models.CharField(max_length=30, choices=VERDICT_CHOICES)
    correct_decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        blank=True,
        default='',
    )
    gate_failures = models.JSONField(default=list, blank=True)
    criteria = models.JSONField(default=dict, blank=True)
    error_claims = models.JSONField(default=list, blank=True)
    reviewed_commit_sha = models.CharField(max_length=40, blank=True, default='')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'submitted_contribution',
                    'reviewer',
                    'proposal_source',
                    'proposal_source_id',
                ],
                name='unique_ai_feedback_source_reviewer',
            ),
        ]
        indexes = [
            models.Index(fields=['updated_at'], name='ai_feedback_updated_idx'),
        ]

    def __str__(self):
        return f'{self.submitted_contribution_id} - {self.reviewer_id} - {self.verdict}'


class Evidence(BaseModel):
    """
    Represents evidence for a contribution or submitted contribution.
    Can be text, a URL, or a file upload.
    """
    # Nullable FKs to both models
    contribution = models.ForeignKey(
        'Contribution',
        on_delete=models.CASCADE,
        related_name='evidence_items',
        null=True,
        blank=True
    )
    submitted_contribution = models.ForeignKey(
        'SubmittedContribution',
        on_delete=models.CASCADE,
        related_name='evidence_items',
        null=True,
        blank=True
    )
    
    description = models.TextField(blank=True, help_text="Description of the evidence")
    url = models.URLField(
        blank=True,
        help_text="Link to external evidence",
        # Evidence links are rendered as anchors across the portal: only
        # web URLs are acceptable (no ftp/file/custom schemes).
        validators=[URLValidator(schemes=['http', 'https'])],
    )
    url_type = models.ForeignKey(
        'EvidenceURLType',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='evidence_items',
        help_text="Auto-detected URL type for this evidence"
    )
    normalized_url = models.CharField(
        max_length=2000, blank=True, db_index=True,
        help_text="Normalized URL for fast duplicate detection"
    )
    file = models.FileField(upload_to=evidence_file_path, blank=True, null=True, help_text="DEPRECATED: File uploads are not currently supported. Use URL instead.")

    def save(self, *args, **kwargs):
        if self.url:
            from .url_utils import detect_url_type, normalize_url
            if self.url_type_id is None:
                self.url_type = detect_url_type(self.url)
            self.normalized_url = normalize_url(self.url)
        else:
            self.normalized_url = ''
        super().save(*args, **kwargs)

    def __str__(self):
        if self.contribution:
            return f"Evidence for {self.contribution}"
        elif self.submitted_contribution:
            return f"Evidence for submitted: {self.submitted_contribution}"
        return "Evidence (unlinked)"
    
    def clean(self):
        """Validate that at least one of description, url, or file is provided."""
        super().clean()
        
        # Validate that evidence belongs to exactly one parent
        if self.contribution and self.submitted_contribution:
            raise ValidationError("Evidence can only belong to either a contribution or a submitted contribution, not both.")
        if not self.contribution and not self.submitted_contribution:
            raise ValidationError("Evidence must belong to either a contribution or a submitted contribution.")
        
        # Validate that at least one evidence type is provided
        if not self.description and not self.url and not self.file:
            raise ValidationError("At least one of description, URL, or file must be provided for evidence.")
        
    class Meta:
        verbose_name = "Evidence"
        verbose_name_plural = "Evidence Items"


class EvidenceURLType(BaseModel):
    """
    Defines a category of evidence URL with pattern-matching rules.
    Examples: X Post, GitHub PR, YouTube Video, Medium Article, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    url_patterns = models.JSONField(
        default=list,
        help_text="List of regex patterns to match URLs of this type"
    )
    is_generic = models.BooleanField(
        default=False,
        help_text="If True, this is the fallback type for unrecognized URLs"
    )
    order = models.PositiveIntegerField(default=0)
    handle_extract_pattern = models.CharField(
        max_length=500,
        blank=True,
        help_text="Regex with named group 'handle' to extract owner/handle from URL"
    )
    ownership_social_account = models.CharField(
        max_length=20,
        blank=True,
        help_text="Social account type for ownership checks: 'twitter' or 'github'"
    )
    allow_duplicate = models.BooleanField(
        default=False,
        help_text="If True, URLs of this type are exempt from duplicate "
                  "checking against other submissions and contributions. "
                  "Useful for shared resources like GitHub repositories."
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Evidence URL Type"
        verbose_name_plural = "Evidence URL Types"

    def __str__(self):
        return self.name


class BlocklistedURL(BaseModel):
    """
    URL prefixes that are not valid evidence for submissions.
    Managed via Django admin. The review_submissions command checks
    all evidence URLs against these prefixes.
    """
    url_prefix = models.URLField(
        unique=True,
        help_text="URL prefix to block (e.g. https://genlayer.com). "
                  "Matches the prefix and any subpaths.",
    )
    reason = models.CharField(
        max_length=200,
        blank=True,
        help_text="Why this URL is blocklisted (for internal reference).",
    )

    class Meta:
        verbose_name = "Blocklisted URL"
        verbose_name_plural = "Blocklisted URLs"
        ordering = ['url_prefix']

    def clean(self):
        super().clean()
        # Normalize: strip query params, fragments, and trailing slash
        # so admin-entered prefixes match the same normalization applied
        # to submission URLs during review.
        if self.url_prefix:
            self.url_prefix = (
                self.url_prefix.split('?')[0].split('#')[0].rstrip('/')
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url_prefix


class Mission(BaseModel):
    """
    Represents a mission to be featured on the dashboard and contribution type pages.
    Staff can create missions with custom descriptions and time periods.
    """
    name = models.CharField(
        max_length=200,
        help_text="Name of the mission"
    )
    description = models.TextField(
        help_text="Description of the mission (supports Markdown)"
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this mission becomes active (optional)"
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this mission expires (optional)"
    )
    contribution_type = models.ForeignKey(
        ContributionType,
        on_delete=models.CASCADE,
        related_name='missions',
        help_text="The contribution type this mission is related to"
    )
    max_submissions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Maximum number of non-rejected, non-canceled submissions allowed "
            "for this mission. Leave blank for unlimited."
        ),
    )
    max_submissions_per_user = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Maximum number of non-rejected, non-canceled submissions allowed "
            "per user for this mission. Leave blank for unlimited."
        ),
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Mission"
        verbose_name_plural = "Missions"

    def is_active(self):
        """
        Check if this mission is currently active based on start/end dates.
        """
        from django.utils import timezone
        now = timezone.now()

        # If start_date is set and we haven't reached it yet, not active
        if self.start_date and now < self.start_date:
            return False

        # If end_date is set and we've passed it, not active
        if self.end_date and now > self.end_date:
            return False

        return True

    def get_submission_count(self):
        """
        Count submissions that consume mission capacity.

        Rejected and canceled submissions do not consume capacity so a bad or
        withdrawn submission can reopen a slot.
        """
        annotated_count = getattr(self, 'submission_count', None)
        if annotated_count is not None:
            return annotated_count
        return self.submissions.exclude(
            state__in=['rejected', 'canceled']
        ).count()

    def submissions_remaining(self):
        if self.max_submissions is None:
            return None
        return max(self.max_submissions - self.get_submission_count(), 0)

    def is_full(self):
        return (
            self.max_submissions is not None
            and self.get_submission_count() >= self.max_submissions
        )

    def get_user_submission_count(self, user):
        """
        Count submissions from a specific user that consume mission capacity.
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        annotated_count = getattr(self, 'user_submission_count', None)
        if annotated_count is not None:
            return annotated_count
        return self.submissions.filter(user=user).exclude(
            state__in=['rejected', 'canceled']
        ).count()

    def user_submissions_remaining(self, user):
        if self.max_submissions_per_user is None:
            return None

        submission_count = self.get_user_submission_count(user)
        if submission_count is None:
            return None

        return max(self.max_submissions_per_user - submission_count, 0)

    def is_full_for_user(self, user):
        if self.max_submissions_per_user is None:
            return False

        submission_count = self.get_user_submission_count(user)
        if submission_count is None:
            return False

        return submission_count >= self.max_submissions_per_user

    def __str__(self):
        return f"{self.name} - {self.contribution_type.name}"


class ContributionHighlight(BaseModel):
    """
    Represents a highlighted contribution to be featured on the dashboard and contribution type pages.
    Staff can select specific contributions to highlight with custom descriptions.
    """
    contribution = models.ForeignKey(
        'Contribution',
        on_delete=models.CASCADE,
        related_name='highlights'
    )
    title = models.CharField(
        max_length=200,
        help_text="Short title for the highlight"
    )
    description = models.TextField(
        help_text="Detailed description of why this contribution is noteworthy"
    )
    
    class Meta:
        ordering = ['-created_at', '-contribution__contribution_date']
        verbose_name = "Contribution Highlight"
        verbose_name_plural = "Contribution Highlights"
    
    def __str__(self):
        return f"{self.title} - {self.contribution.user.name or self.contribution.user.address[:8]}"
    
    @classmethod
    def get_active_highlights(cls, contribution_type=None, user=None, limit=5):
        """
        Get highlights, optionally filtered by contribution type or user.
        Ordered by highlight creation date (newest featured first), then
        contribution date as a fallback.
        
        Args:
            contribution_type: Optional ContributionType to filter by
            user: Optional User to filter by
            limit: Maximum number of highlights to return (default 5)
        """
        queryset = cls.objects.all().order_by('-created_at', '-contribution__contribution_date')
        
        # Filter by contribution type if provided
        if contribution_type:
            queryset = queryset.filter(contribution__contribution_type=contribution_type)
        
        # Filter by user if provided
        if user:
            queryset = queryset.filter(contribution__user=user)
        
        # Select related for optimization
        queryset = queryset.select_related(
            'contribution',
            'contribution__user',
            'contribution__contribution_type'
        )

        return queryset[:limit]


class StartupRequest(BaseModel):
    """
    Represents a startup idea/opportunity for the community to pursue.
    Displayed in the builder contributions section as informational content.
    """
    title = models.CharField(
        max_length=200,
        help_text="Title of the startup request"
    )
    description = models.TextField(
        help_text="Full description (supports Markdown)"
    )
    short_description = models.CharField(
        max_length=300,
        help_text="Brief description shown in listing (plain text)"
    )
    documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of document objects: [{title, url, type}]"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this startup request is currently visible"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Startup Request"
        verbose_name_plural = "Startup Requests"

    def __str__(self):
        return self.title

    @classmethod
    def get_active_requests(cls):
        """
        Get all active startup requests ordered by display order.
        """
        return cls.objects.filter(is_active=True).order_by('order', '-created_at')


class FeaturedContent(BaseModel):
    """
    Featured content for the home page: hero banners, featured builds, community highlights.
    Managed via admin panel.
    """
    CONTENT_TYPE_CHOICES = [
        ('hero', 'Hero Banner'),
        # Legacy portal builds are kept for compatibility; new project profiles live in projects.Project.
        ('build', 'Featured Build'),
        ('community', 'Featured Community'),
        ('validator_steward', 'Featured Validator/Steward'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('idle', 'Idle'),
    ]
    HERO_PLACEMENT_ALL = 'all'
    HERO_PLACEMENT_CHOICES = [
        (HERO_PLACEMENT_ALL, 'All hero surfaces'),
        ('overview', 'Overview'),
        ('builder', 'Builder dashboard'),
        ('validator', 'Validator dashboard'),
        ('community', 'Community dashboard'),
    ]
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    author = models.CharField(max_length=200, blank=True)
    contribution = models.ForeignKey(
        'Contribution', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='featured_items'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='featured_items'
    )
    hero_image_url = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for hero image')
    hero_image_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for hero image')
    hero_image_url_tablet = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for tablet hero image (768-1023px). Falls back to hero_image_url if empty.')
    hero_image_tablet_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for tablet hero image')
    hero_image_url_mobile = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for mobile hero image (<768px). Falls back to hero_image_url if empty.')
    hero_image_mobile_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for mobile hero image')
    user_profile_image_url = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for user profile image')
    user_profile_image_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for user profile image')
    url = models.URLField(max_length=500, blank=True)
    hero_placements = models.JSONField(
        default=default_featured_hero_placements,
        blank=True,
        help_text=(
            "Hero banner placements. Use 'all' to show everywhere, or select "
            "specific surfaces such as overview, builder, validator, and community."
        )
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'title'],
                name='unique_featured_content_type_title',
            ),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()}: {self.title}"

    def get_link(self):
        if self.contribution_id:
            return f"/badge/{self.contribution_id}"
        return self.url or None

    @classmethod
    def normalize_hero_placements(cls, placements):
        if not isinstance(placements, list):
            return []
        valid = {choice[0] for choice in cls.HERO_PLACEMENT_CHOICES}
        normalized = []
        for placement in placements:
            if placement in valid and placement not in normalized:
                normalized.append(placement)
        if cls.HERO_PLACEMENT_ALL in normalized:
            return [cls.HERO_PLACEMENT_ALL]
        return normalized

    def clean(self):
        super().clean()
        if not isinstance(self.hero_placements, list):
            raise ValidationError({'hero_placements': 'Hero placements must be a list.'})

        valid = {choice[0] for choice in self.HERO_PLACEMENT_CHOICES}
        invalid = [placement for placement in self.hero_placements if placement not in valid]
        if invalid:
            raise ValidationError({
                'hero_placements': f"Invalid hero placement value(s): {', '.join(invalid)}"
            })
        self.hero_placements = self.normalize_hero_placements(self.hero_placements)

    def shows_in_placement(self, placement):
        placements = self.normalize_hero_placements(self.hero_placements)
        return self.HERO_PLACEMENT_ALL in placements or placement in placements


class Alert(BaseModel):
    """
    System-wide alert banners displayed on all pages.
    Managed via Django admin.
    """
    ALERT_TYPE_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    ]
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPE_CHOICES, default='info')
    icon = models.CharField(max_length=50, blank=True, help_text="Optional icon name (frontend defaults by type)")
    text = models.TextField(help_text="Alert message text")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower numbers appear first)")
    start_date = models.DateTimeField(null=True, blank=True, help_text="When this alert becomes visible (optional)")
    end_date = models.DateTimeField(null=True, blank=True, help_text="When this alert expires (optional)")

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"

    def __str__(self):
        return f"[{self.get_alert_type_display()}] {self.text[:50]}"

    @classmethod
    def get_active_alerts(cls):
        now = timezone.now()
        return cls.objects.filter(
            is_active=True
        ).filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gt=now)
        )
