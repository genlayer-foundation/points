from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.conf import settings
from utils.models import BaseModel


class Steward(BaseModel):
    """
    Steward profile - empty for now, fields to be added later.
    One-to-one relationship with User.
    """
    TIER_REVIEWER = 1
    TIER_TOP_LEVEL = 2
    TIER_APEX = 3
    TIER_CHOICES = [
        (TIER_REVIEWER, 'Reviewer'),
        (TIER_TOP_LEVEL, 'Top-level steward'),
        (TIER_APEX, 'Apex steward'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='steward'
    )
    tier = models.PositiveSmallIntegerField(
        choices=TIER_CHOICES,
        default=TIER_REVIEWER,
    )
    can_review_feature_candidates = models.BooleanField(
        default=False,
        help_text="Can access the blind reviewer scoring view for interesting submissions.",
    )

    def __str__(self):
        return f"{self.user.email} - Steward"


class FeatureCandidateScore(BaseModel):
    """
    Blind score from one steward for one interesting submission.
    Aggregates are computed server-side and are never exposed to reviewers.
    """
    submission = models.ForeignKey(
        'contributions.SubmittedContribution',
        on_delete=models.CASCADE,
        related_name='feature_candidate_scores',
    )
    steward = models.ForeignKey(
        Steward,
        on_delete=models.CASCADE,
        related_name='feature_candidate_scores',
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        help_text="0 = not interesting, 1 = weak, 2 = good, 3 = strong.",
    )
    reason = models.TextField(
        max_length=2000,
        blank=True,
        default='',
        help_text="Reviewer note explaining what stood out for this score.",
    )

    class Meta:
        unique_together = ['submission', 'steward']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=0, score__lte=3),
                name='feature_candidate_score_score_range_0_3',
            ),
        ]
        indexes = [
            models.Index(fields=['submission', 'score']),
            models.Index(fields=['steward', 'updated_at']),
        ]
        ordering = ['submission', 'steward']

    def __str__(self):
        return f"{self.submission_id} - {self.steward.user.email} - {self.score}"


class StewardPermission(BaseModel):
    """
    Per-action, per-contribution-type permission for stewards.
    Controls what actions a steward can perform on submissions of each type.
    """
    ACTION_CHOICES = [
        ('propose', 'Propose'),
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('request_more_info', 'Request More Info'),
    ]
    steward = models.ForeignKey(
        Steward,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    contribution_type = models.ForeignKey(
        'contributions.ContributionType',
        on_delete=models.CASCADE,
        related_name='steward_permissions'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    class Meta:
        unique_together = ['steward', 'contribution_type', 'action']
        ordering = ['steward', 'contribution_type', 'action']

    def __str__(self):
        return f"{self.steward.user} - {self.contribution_type} - {self.action}"


class ReviewTemplate(BaseModel):
    """
    Admin-managed template messages for steward review workflows.
    """
    ACTION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('more_info', 'More Info'),
    ]
    label = models.CharField(max_length=100, help_text="Short label, e.g. 'Insufficient evidence'")
    text = models.TextField(help_text="Full template text to insert into reply fields")
    action = models.CharField(
        max_length=20, choices=ACTION_CHOICES, default='reject',
        help_text="Which review action this template is for",
    )

    class Meta:
        ordering = ['action', 'label']

    def __str__(self):
        return f"{self.get_action_display()}: {self.label}"


class WorkingGroup(BaseModel):
    """
    A working group that participants can be members of.
    """
    name = models.CharField(max_length=200)
    icon = models.CharField(max_length=10, blank=True, help_text="Emoji icon for the working group")
    description = models.TextField(blank=True, help_text="Description of the working group")
    discord_url = models.URLField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class WorkingGroupParticipant(BaseModel):
    """
    Links users to working groups (many-to-many relationship).
    """
    working_group = models.ForeignKey(
        WorkingGroup,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='working_group_memberships'
    )

    def __str__(self):
        return f"{self.user.name or self.user.address} - {self.working_group.name}"

    class Meta:
        unique_together = ['working_group', 'user']
        ordering = ['created_at']
