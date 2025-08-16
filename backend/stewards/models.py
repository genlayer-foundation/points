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