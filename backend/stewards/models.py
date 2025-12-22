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


class WorkingGroup(BaseModel):
    """
    A working group that participants can be members of.
    """
    name = models.CharField(max_length=200)
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
