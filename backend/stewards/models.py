from django.db import models
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
    label = models.CharField(max_length=100, help_text="Short label, e.g. 'Insufficient evidence'")
    text = models.TextField(help_text="Full template text to insert into reply fields")

    class Meta:
        ordering = ['label']

    def __str__(self):
        return self.label


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
