from django.db import models
from django.conf import settings


class Action(models.Model):
    """
    Represents different types of actions that participants can perform.
    Examples: Node Runner, Uptime, Asimov, Blog Post, etc.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Participant(models.Model):
    """
    Represents a participant in the GenLayer Testnet Program.
    Extends the User model with additional fields.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participant')
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.email
    
    @property
    def total_points(self):
        """Calculate the total global points for this participant."""
        badges = self.badges.all()
        return sum(badge.points * badge.action.multiplier for badge in badges)


class Badge(models.Model):
    """
    Represents a badge awarded to a participant for completing an action.
    Each badge has action points associated with it.
    """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='badges')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, related_name='badges')
    points = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    evidence_url = models.URLField(blank=True)
    multiplier_at_issuance = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.participant} - {self.action} - {self.points}pts"
    
    def save(self, *args, **kwargs):
        # Record the multiplier at the time of issuance
        if not self.multiplier_at_issuance:
            self.multiplier_at_issuance = self.action.multiplier
        super().save(*args, **kwargs)


class Leaderboard(models.Model):
    """
    Represents a snapshot of the global leaderboard at a point in time.
    For historical tracking purposes.
    """
    name = models.CharField(max_length=100)
    snapshot_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.snapshot_date.strftime('%Y-%m-%d')}"


class LeaderboardEntry(models.Model):
    """
    Represents a participant's position on a leaderboard snapshot.
    """
    leaderboard = models.ForeignKey(Leaderboard, on_delete=models.CASCADE, related_name='entries')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='leaderboard_entries')
    position = models.PositiveIntegerField()
    total_points = models.PositiveIntegerField()
    
    class Meta:
        unique_together = ['leaderboard', 'participant']
        ordering = ['position']

    def __str__(self):
        return f"{self.leaderboard} - #{self.position} {self.participant}"