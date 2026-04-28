from django.db import models
from django.db.models import Q
from django.conf import settings
from utils.models import BaseModel


class Steward(BaseModel):
    """
    Steward profile - empty for now, fields to be added later.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='steward'
    )

    def __str__(self):
        return f"{self.user.email} - Steward"


class StewardAssignment(BaseModel):
    """
    Role + scope assignment for a steward.

    Role:
      - 'full_review' grants accept/reject/request_more_info/propose
      - 'propose' grants propose only
    Scope is one of:
      - scope_category: all contribution types in a category
      - scope_type: a single contribution type
      - both null: global (all contribution types)

    Multiple assignments per steward are additive.
    """
    ROLE_FULL_REVIEW = 'full_review'
    ROLE_PROPOSE = 'propose'
    ROLE_CHOICES = [
        (ROLE_FULL_REVIEW, 'Full Review'),
        (ROLE_PROPOSE, 'Propose Only'),
    ]

    steward = models.ForeignKey(
        Steward,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    scope_category = models.ForeignKey(
        'contributions.Category',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='steward_assignments',
    )
    scope_type = models.ForeignKey(
        'contributions.ContributionType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='steward_assignments',
    )

    class Meta:
        ordering = ['steward', 'role']
        constraints = [
            models.CheckConstraint(
                condition=~(Q(scope_category__isnull=False) & Q(scope_type__isnull=False)),
                name='steward_assignment_scope_mutually_exclusive',
            ),
            models.UniqueConstraint(
                fields=['steward', 'role', 'scope_category', 'scope_type'],
                name='steward_assignment_unique',
            ),
        ]

    def __str__(self):
        if self.scope_type_id:
            scope = f"type:{self.scope_type}"
        elif self.scope_category_id:
            scope = f"category:{self.scope_category}"
        else:
            scope = "global"
        return f"{self.steward.user} - {self.get_role_display()} - {scope}"


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
