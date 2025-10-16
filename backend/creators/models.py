from django.db import models
from django.conf import settings
from utils.models import BaseModel


class Creator(BaseModel):
    """
    Creator profile - for users who focus on referrals.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creator'
    )

    def __str__(self):
        return f"{self.user.email} - Creator"
