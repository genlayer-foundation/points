from django.db import models
from django.conf import settings
from utils.models import BaseModel


class Creator(BaseModel):
    """
    Community profile for users participating in community activities.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='creator'
    )

    def __str__(self):
        return f"{self.user.email} - Creator"


class CommunityPostProof(BaseModel):
    """Step 5 of the community journey: the verified X post tagging GenLayer
    with the user's generated code. One per user."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='community_post_proof',
    )
    post_url = models.URLField()
    tweet_id = models.CharField(max_length=40, blank=True)
    verified_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - community X post"
