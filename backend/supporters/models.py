from django.db import models
from django.conf import settings
from utils.models import BaseModel


class Supporter(BaseModel):
    """
    Supporter profile - for users who focus on referrals.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='supporter'
    )

    class Meta:
        db_table = 'creators_creator'  # Preserve original table name for compatibility

    def __str__(self):
        return f"{self.user.email} - Supporter"
