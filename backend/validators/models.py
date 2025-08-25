from django.db import models
from django.conf import settings
from django.utils import timezone
from utils.models import BaseModel
from .node_version import NodeVersionMixin


class Validator(NodeVersionMixin, BaseModel):
    """
    Represents a validator with their node version information.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='validator'
    )
    # node_version field is inherited from NodeVersionMixin
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
    
    # Methods clean_version, version_matches_or_higher, and save are inherited from NodeVersionMixin