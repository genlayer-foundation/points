from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
from utils.models import BaseModel
from contributions.models import ContributionType, Contribution, Category


# Helper functions for leaderboard configuration
def has_contribution_badge(user, slug):
    """Helper to check if user has a specific contribution badge"""
    return Contribution.objects.filter(
        user=user,
        contribution_type__slug=slug
    ).exists()


def has_category_contributions(user, category_slug):
    """Helper to check if user has contributions in a category"""
    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug=category_slug
    )
    # Exclude Builder Welcome from builder category checks
    if category_slug == 'builder':
        query = query.exclude(contribution_type__slug='builder-welcome')
    return query.exists()


def calculate_category_points(user, category_slug):
    """Calculate total points from a specific category"""
    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug=category_slug
    )
    # Exclude Builder Welcome from builder category points
    if category_slug == 'builder':
        query = query.exclude(contribution_type__slug='builder-welcome')
    return query.aggregate(
        total=Sum('frozen_global_points')
    )['total'] or 0


def calculate_waitlist_points(user):
    """
    Calculate waitlist points including both contributions and referral points.
    Formula: contribution_points + referral_points (simple sum, easy to adjust)
    """
    # Find graduation contribution if exists
    grad_contrib = Contribution.objects.filter(
        user=user,
        contribution_type__slug='validator'
    ).order_by('contribution_date').first()

    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug='validator'
    )

    if grad_contrib:
        # Only count contributions before graduation
        query = query.filter(contribution_date__lt=grad_contrib.contribution_date)

    contribution_points = query.aggregate(total=Sum('frozen_global_points'))['total'] or 0

    # Calculate referral points
    if grad_contrib:
        # For graduated users: calculate referral points ONLY from contributions before graduation
        from users.models import User
        referred_user_ids = User.objects.filter(referred_by=user).values_list('id', flat=True)

        if referred_user_ids:
            builder_referral = int((Contribution.objects.filter(
                user_id__in=referred_user_ids,
                contribution_type__category__slug='builder',
                contribution_date__lt=grad_contrib.contribution_date
            ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

            validator_referral = int((Contribution.objects.filter(
                user_id__in=referred_user_ids,
                contribution_type__category__slug='validator',
                contribution_date__lt=grad_contrib.contribution_date
            ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

            referral_points = builder_referral + validator_referral
        else:
            referral_points = 0
    else:
        # For current waitlist users: use total referral points from ReferralPoints table
        try:
            referral_points = user.referral_points.builder_points + user.referral_points.validator_points
        except ReferralPoints.DoesNotExist:
            referral_points = 0

    return contribution_points + referral_points


def calculate_graduation_points(user):
    """
    For graduation leaderboard - returns existing frozen points or calculates them.
    Returns tuple of (points, should_update, graduation_date)
    """
    # Import here to avoid circular dependency
    from leaderboard.models import LeaderboardEntry
    
    # Check if already has graduation entry
    existing_entry = LeaderboardEntry.objects.filter(
        user=user,
        type='validator-waitlist-graduation'
    ).first()
    
    if existing_entry:
        # Points already frozen, no update needed
        return existing_entry.total_points, False, existing_entry.graduation_date
    
    # New graduation - calculate points to freeze
    waitlist_points = calculate_waitlist_points(user)
    
    # Get graduation date from validator contribution
    grad_contrib = Contribution.objects.filter(
        user=user,
        contribution_type__slug='validator'
    ).order_by('contribution_date').first()
    
    graduation_date = grad_contrib.contribution_date if grad_contrib else timezone.now()
    
    return waitlist_points, True, graduation_date


# Unified configuration for all leaderboard types
LEADERBOARD_CONFIG = {
    'validator': {
        'name': 'Validator',
        'participants': lambda user: has_contribution_badge(user, 'validator'),
        'points_calculator': lambda user: calculate_category_points(user, 'validator'),
        'ranking_order': '-total_points',  # Highest points first
    },
    'builder': {
        'name': 'Builder',
        'participants': lambda user: has_category_contributions(user, 'builder'),
        'points_calculator': lambda user: calculate_category_points(user, 'builder'),
        'ranking_order': '-total_points',
    },
    'validator-waitlist': {
        'name': 'Validator Waitlist',
        'participants': lambda user: (
            has_contribution_badge(user, 'validator-waitlist') and 
            not has_contribution_badge(user, 'validator')
        ),
        'points_calculator': lambda user: calculate_waitlist_points(user),
        'ranking_order': '-total_points',
    },
    'validator-waitlist-graduation': {
        'name': 'Validator Waitlist Graduation',
        'participants': lambda user: (
            has_contribution_badge(user, 'validator-waitlist') and
            has_contribution_badge(user, 'validator')
        ),
        'points_calculator': lambda user: calculate_graduation_points(user),
        'ranking_order': '-graduation_date',  # Most recent graduations first
    }
}


class GlobalLeaderboardMultiplier(BaseModel):
    """
    Tracks the history of multiplier values over time for contribution types.
    
    Each contribution type can have multiple multiplier values over time,
    and this model keeps track of when each value became active.
    """
    contribution_type = models.ForeignKey(
        ContributionType,
        on_delete=models.CASCADE,
        related_name='multipliers'
    )
    multiplier_value = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    valid_from = models.DateTimeField()
    description = models.CharField(max_length=255, blank=True, help_text="Reason for this multiplier value")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-valid_from']
        get_latest_by = 'valid_from'
    
    def __str__(self):
        return f"{self.contribution_type.name}: {self.multiplier_value}x (from {self.valid_from.strftime('%Y-%m-%d %H:%M')})"
    
    def clean(self):
        """Validate the multiplier data."""
        super().clean()
        
        # Ensure multiplier_value is positive
        if self.multiplier_value <= 0:
            raise ValidationError("Multiplier value must be positive")
            
    def save(self, *args, **kwargs):
        """
        Override save to validate the multiplier.
        """
        self.clean()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_current_multiplier_value(cls, contribution_type):
        """
        Get the current multiplier value for this contribution type.
        Returns the value of the most recent period, or 1.0 if none exists.
        """
        latest_multiplier = cls.objects.filter(
            contribution_type=contribution_type
        ).order_by('-valid_from').first()
        
        if latest_multiplier:
            return latest_multiplier.multiplier_value
        return 1.0
    
    @classmethod
    def get_active_for_type(cls, contribution_type, at_date=None):
        """
        Get the active multiplier for a given contribution type at a specific date.
        If no date is provided, uses the current date/time.
        
        Returns a tuple of (multiplier_obj, multiplier_value)
        Raises DoesNotExist if no multiplier exists for the contribution type or
        if no period exists for the given date.
        """
        at_date = at_date or timezone.now()
        
        # Find the multiplier that is valid at the given date
        # (the most recent multiplier that started before or at the given date)
        multiplier = cls.objects.filter(
            contribution_type=contribution_type,
            valid_from__lte=at_date
        ).order_by('-valid_from').first()
            
        if not multiplier:
            raise cls.DoesNotExist(
                f"No multiplier exists for contribution type '{contribution_type}' at {at_date}"
            )
            
        return multiplier, multiplier.multiplier_value


class LeaderboardEntry(BaseModel):
    """
    Represents a user's position on a specific leaderboard type.
    Each leaderboard has independent point calculations.
    """
    # Generate choices from configuration
    LEADERBOARD_TYPES = [(key, config['name']) for key, config in LEADERBOARD_CONFIG.items()]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='leaderboard_entries'
    )
    type = models.CharField(
        max_length=50,
        choices=LEADERBOARD_TYPES,
        help_text="Type of leaderboard this entry belongs to"
    )
    total_points = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    last_update = models.DateTimeField(auto_now=True)
    
    # For graduation leaderboard - store graduation date
    graduation_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-total_points', 'user__name']
        verbose_name_plural = 'Leaderboard entries'
        unique_together = ['user', 'type']
    
    def __str__(self):
        leaderboard_name = self.get_type_display() if self.type else "Unknown"
        return f"{self.user} - {leaderboard_name} - {self.total_points} points - Rank: {self.rank or 'Not ranked'}"
    
    def update_points_without_ranking(self):
        """
        Update this leaderboard entry's total points based on the user's contributions.
        This method does NOT update ranks - useful for batch operations where ranks 
        should be updated once at the end.
        """
        config = LEADERBOARD_CONFIG.get(self.type)
        if not config:
            return self.total_points
        
        calculator = config['points_calculator']
        
        if self.type == 'validator-waitlist-graduation':
            # Special handling for graduation
            points, should_update, _ = calculator(self.user)
            if should_update:
                self.total_points = points
                self.save(update_fields=['total_points'])
        else:
            self.total_points = calculator(self.user)
            self.save(update_fields=['total_points'])
        
        return self.total_points
    
    @classmethod
    def determine_user_leaderboards(cls, user):
        """
        Determine which leaderboards a user should appear on based on LEADERBOARD_CONFIG.
        Returns a list of leaderboard type strings.
        """
        user_leaderboards = []
        for leaderboard_type, config in LEADERBOARD_CONFIG.items():
            if config['participants'](user):
                user_leaderboards.append(leaderboard_type)
        return user_leaderboards

    @classmethod
    def update_leaderboard_ranks(cls, leaderboard_type):
        """
        Update ranks for all users in a specific leaderboard type.
        Only visible users are ranked.
        Uses user join date as tie-breaker for equal points (older users rank higher).
        """
        if leaderboard_type not in LEADERBOARD_CONFIG:
            return

        config = LEADERBOARD_CONFIG[leaderboard_type]
        ranking_order = config['ranking_order']

        # First, set all non-visible users' ranks to null
        cls.objects.filter(
            type=leaderboard_type,
            user__visible=False
        ).update(rank=None)

        # Get visible entries with user data
        entries = list(
            cls.objects.filter(
                type=leaderboard_type,
                user__visible=True
            ).select_related('user')
        )

        if not entries:
            return

        # Sort based on ranking type
        if ranking_order == '-total_points':
            # Sort by points (desc), then user join date (asc), then name
            # Older users (who joined earlier) get better rank when points are tied
            entries.sort(key=lambda e: (
                -e.total_points,  # Higher points first
                e.user.date_joined,  # Earlier join date first (older users)
                e.user.name  # Alphabetical by name as final tie-breaker
            ))
        elif ranking_order == '-graduation_date':
            # Sort by graduation date, then user join date, then name
            entries.sort(key=lambda e: (
                -(e.graduation_date.timestamp() if e.graduation_date else 0),
                e.user.date_joined,
                e.user.name
            ))
        else:
            # Default sorting by name
            entries.sort(key=lambda e: e.user.name)

        # Assign consecutive ranks
        for i, entry in enumerate(entries, 1):
            entry.rank = i

        if entries:
            cls.objects.bulk_update(entries, ['rank'], batch_size=1000)


# Signal handlers
@receiver(post_save, sender=GlobalLeaderboardMultiplier)
def log_multiplier_creation(sender, instance, created, **kwargs):
    """
    When a new multiplier is created, log it for debugging purposes.
    """
    if created:
        print(f"New global multiplier: {instance.contribution_type.name} - "
              f"{instance.multiplier_value}x valid from {instance.valid_from.strftime('%Y-%m-%d %H:%M')}")


@receiver(post_save, sender=Contribution)
def update_leaderboard_on_contribution(sender, instance, created, **kwargs):
    """
    When a contribution is saved, update all affected leaderboard entries.
    Also updates referrer's referral points if the user was referred.
    """
    # Only update if points have changed or it's a new contribution
    if created or kwargs.get('update_fields') is None or 'points' in kwargs.get('update_fields', []):
        # Log the contribution's point calculation
        contribution_date_str = instance.contribution_date.strftime('%Y-%m-%d %H:%M') if instance.contribution_date else "N/A"
        print(f"Contribution saved: {instance.points} points × {instance.multiplier_at_creation} = "
              f"{instance.frozen_global_points} global points (contribution date: {contribution_date_str})")
    
    # Update the user's leaderboard entries
    update_user_leaderboard_entries(instance.user)

    # Update referrer's referral points if applicable
    if instance.user.referred_by:
        update_referrer_points(instance)


def update_user_leaderboard_entries(user):
    """
    Core function that manages all of a user's leaderboard placements.
    Handles graduation, point calculations, and rank updates.
    """
    # Step 1: Determine which leaderboards user qualifies for
    qualified_leaderboards = []
    for leaderboard_type, config in LEADERBOARD_CONFIG.items():
        if config['participants'](user):
            qualified_leaderboards.append(leaderboard_type)
    
    # Step 2: Track which leaderboards were removed (for rank updates)
    existing_entries = set(
        LeaderboardEntry.objects.filter(user=user).values_list('type', flat=True)
    )
    removed_leaderboards = existing_entries - set(qualified_leaderboards)
    
    # Step 3: Remove from leaderboards user no longer qualifies for
    if removed_leaderboards:
        LeaderboardEntry.objects.filter(
            user=user,
            type__in=removed_leaderboards
        ).delete()
    
    # Step 4: Update or create entries for each qualified leaderboard
    for leaderboard_type in qualified_leaderboards:
        config = LEADERBOARD_CONFIG[leaderboard_type]
        calculator = config['points_calculator']
        
        if leaderboard_type == 'validator-waitlist-graduation':
            # Special handling for graduation (frozen points)
            points, should_update, graduation_date = calculator(user)
            
            if should_update:
                # Create or update graduation entry
                LeaderboardEntry.objects.update_or_create(
                    user=user,
                    type=leaderboard_type,
                    defaults={
                        'total_points': points,
                        'graduation_date': graduation_date
                    }
                )
            # If not should_update, entry already exists with frozen points
        else:
            # Regular leaderboard update
            points = calculator(user)
            
            LeaderboardEntry.objects.update_or_create(
                user=user,
                type=leaderboard_type,
                defaults={'total_points': points}
            )
    
    # Step 5: Update ranks for all affected leaderboards
    affected_leaderboards = set(qualified_leaderboards) | removed_leaderboards
    for leaderboard_type in affected_leaderboards:
        LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)


class ReferralPoints(BaseModel):
    """
    Tracks referral points earned from referred users' contributions.
    Separate from LeaderboardEntry to work regardless of referrer's own status.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_points'
    )
    builder_points = models.PositiveIntegerField(
        default=0,
        help_text="10% of referred users' builder contributions"
    )
    validator_points = models.PositiveIntegerField(
        default=0,
        help_text="10% of referred users' validator contributions"
    )

    class Meta:
        verbose_name = "Referral Points"
        verbose_name_plural = "Referral Points"

    def __str__(self):
        return f"{self.user.email} - B:{self.builder_points} V:{self.validator_points}"


def update_referrer_points(contribution):
    """
    Incrementally update referral points when a referred user makes a contribution.
    Performance: O(1) - only adds 10% of the new contribution.
    """
    referrer = contribution.user.referred_by
    if not referrer:
        return

    # Get or create referral points record
    rp, _ = ReferralPoints.objects.get_or_create(user=referrer)

    # Get the contribution category
    category_slug = contribution.contribution_type.category.slug if contribution.contribution_type.category else None

    # Increment appropriate category by 10% of contribution points
    points_to_add = int(contribution.frozen_global_points * 0.1)

    if category_slug == 'builder':
        rp.builder_points += points_to_add
        rp.save(update_fields=['builder_points'])
    elif category_slug == 'validator':
        rp.validator_points += points_to_add
        rp.save(update_fields=['validator_points'])
    else:
        # No category means no points added, no need to update leaderboard
        return

    # CRITICAL: Update referrer's validator-waitlist leaderboard entry
    # This prevents LeaderboardEntry.total_points from being stale
    # Only check if referrer is on validator-waitlist to avoid unnecessary work
    if LeaderboardEntry.objects.filter(user=referrer, type='validator-waitlist').exists():
        # Update only the validator-waitlist leaderboard (not all leaderboards)
        # This is more efficient than update_user_leaderboard_entries(referrer)
        # which would check all 4 leaderboard types
        config = LEADERBOARD_CONFIG['validator-waitlist']
        calculator = config['points_calculator']
        points = calculator(referrer)

        LeaderboardEntry.objects.update_or_create(
            user=referrer,
            type='validator-waitlist',
            defaults={'total_points': points}
        )

        # Update ranks for validator-waitlist leaderboard
        # Note: This is still expensive (updates all users in waitlist)
        # but necessary for correctness
        LeaderboardEntry.update_leaderboard_ranks('validator-waitlist')


@transaction.atomic
def recalculate_referrer_points(referrer):
    """
    Update referral points when referred user makes contribution.
    Efficiently calculates points per category.
    """
    from users.models import User

    referred_user_ids = User.objects.filter(referred_by=referrer).values_list('id', flat=True)
    if not referred_user_ids:
        return

    rp, _ = ReferralPoints.objects.get_or_create(user=referrer)

    # Calculate builder points
    rp.builder_points = int((Contribution.objects.filter(
        user_id__in=referred_user_ids,
        contribution_type__category__slug='builder'
    ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

    # Calculate validator points
    rp.validator_points = int((Contribution.objects.filter(
        user_id__in=referred_user_ids,
        contribution_type__category__slug='validator'
    ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

    rp.save(update_fields=['builder_points', 'validator_points'])


def update_all_ranks():
    """
    Update the ranks for all leaderboard types.
    
    Users with the same points will have consecutive ranks.
    For example: if two users have 100 points, they will be ranked 1 and 2,
    not both as rank 1.
    
    Only visible users are ranked. Non-visible users get null rank.
    """
    # Update each leaderboard type
    for leaderboard_type in LEADERBOARD_CONFIG.keys():
        LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)


def recalculate_all_leaderboards():
    """
    Recalculate all leaderboard entries and referral points from scratch.

    Optimized implementation that loads all data once and processes in Python,
    reducing database queries from thousands to ~15 regardless of data size.
    """
    from collections import defaultdict
    from django.db import transaction

    with transaction.atomic():
        # Clear all existing calculated data
        LeaderboardEntry.objects.all().delete()
        ReferralPoints.objects.all().delete()

        # Load ALL contribution data in a single query
        contributions = list(Contribution.objects.select_related(
            'contribution_type__category'
        ).values(
            'id',
            'user_id',
            'user__referred_by_id',
            'user__visible',
            'contribution_type__slug',
            'contribution_type__category__slug',
            'contribution_date',
            'frozen_global_points'
        ))

        if not contributions:
            return "Recalculated 0 users across 0 leaderboards and 0 referrers"

        # Build data structures in Python
        user_contributions = defaultdict(list)
        referrer_contributions = defaultdict(list)
        contribution_badges = defaultdict(set)
        user_ids = set()

        for contrib in contributions:
            user_id = contrib['user_id']
            user_ids.add(user_id)
            user_contributions[user_id].append(contrib)

            # Track badges (specific contribution type slugs)
            contrib_slug = contrib['contribution_type__slug']
            if contrib_slug:
                contribution_badges[user_id].add(contrib_slug)

            # Track contributions by referrer
            referrer_id = contrib['user__referred_by_id']
            if referrer_id:
                referrer_contributions[referrer_id].append(contrib)

        # Calculate and bulk create referral points
        referral_points_to_create = []

        for referrer_id, referred_contribs in referrer_contributions.items():
            builder_points = 0
            validator_points = 0

            for contrib in referred_contribs:
                category_slug = contrib['contribution_type__category__slug']
                points = contrib['frozen_global_points'] or 0

                if category_slug == 'builder':
                    builder_points += int(points * 0.1)
                elif category_slug == 'validator':
                    validator_points += int(points * 0.1)

            referral_points_to_create.append(ReferralPoints(
                user_id=referrer_id,
                builder_points=builder_points,
                validator_points=validator_points
            ))

        if referral_points_to_create:
            ReferralPoints.objects.bulk_create(referral_points_to_create, batch_size=1000)

        # Create referral points lookup for waitlist calculations
        referral_points_lookup = {rp.user_id: rp for rp in referral_points_to_create}

        # Determine user qualifications and calculate points
        entries_to_create = []

        for user_id in user_ids:
            user_contribs = user_contributions[user_id]
            user_badges = contribution_badges[user_id]

            # Determine which leaderboards this user qualifies for
            qualified_leaderboards = []

            # Validator leaderboard: has 'validator' badge
            if 'validator' in user_badges:
                qualified_leaderboards.append('validator')

            # Builder leaderboard: has builder category contributions (excluding builder-welcome)
            has_builder = False
            for contrib in user_contribs:
                if (contrib['contribution_type__category__slug'] == 'builder' and
                    contrib['contribution_type__slug'] != 'builder-welcome'):
                    has_builder = True
                    break
            if has_builder:
                qualified_leaderboards.append('builder')

            # Validator waitlist: has 'validator-waitlist' badge but NOT 'validator' badge
            if 'validator-waitlist' in user_badges and 'validator' not in user_badges:
                qualified_leaderboards.append('validator-waitlist')

            # Validator waitlist graduation: has both badges
            if 'validator-waitlist' in user_badges and 'validator' in user_badges:
                qualified_leaderboards.append('validator-waitlist-graduation')

            # Calculate points for each qualified leaderboard
            for leaderboard_type in qualified_leaderboards:
                points = 0
                graduation_date = None

                if leaderboard_type == 'validator':
                    # Sum all validator category contributions
                    for contrib in user_contribs:
                        if contrib['contribution_type__category__slug'] == 'validator':
                            points += contrib['frozen_global_points'] or 0

                elif leaderboard_type == 'builder':
                    # Sum builder category (excluding builder-welcome)
                    for contrib in user_contribs:
                        if (contrib['contribution_type__category__slug'] == 'builder' and
                            contrib['contribution_type__slug'] != 'builder-welcome'):
                            points += contrib['frozen_global_points'] or 0

                elif leaderboard_type == 'validator-waitlist':
                    # Sum all validator category contributions + referral points
                    for contrib in user_contribs:
                        if contrib['contribution_type__category__slug'] == 'validator':
                            points += contrib['frozen_global_points'] or 0

                    # Add referral points if user is a referrer
                    if user_id in referral_points_lookup:
                        rp = referral_points_lookup[user_id]
                        points += rp.builder_points + rp.validator_points

                elif leaderboard_type == 'validator-waitlist-graduation':
                    # Find graduation date (earliest validator contribution)
                    grad_date = None
                    for contrib in user_contribs:
                        if contrib['contribution_type__slug'] == 'validator':
                            contrib_date = contrib['contribution_date']
                            if grad_date is None or contrib_date < grad_date:
                                grad_date = contrib_date

                    graduation_date = grad_date

                    # Calculate waitlist points BEFORE graduation
                    for contrib in user_contribs:
                        if contrib['contribution_type__category__slug'] == 'validator':
                            if contrib['contribution_date'] < grad_date:
                                points += contrib['frozen_global_points'] or 0

                    # Add referral points from contributions BEFORE graduation
                    if user_id in referrer_contributions:
                        builder_referral = 0
                        validator_referral = 0

                        for referred_contrib in referrer_contributions[user_id]:
                            if referred_contrib['contribution_date'] < grad_date:
                                category = referred_contrib['contribution_type__category__slug']
                                contrib_points = referred_contrib['frozen_global_points'] or 0

                                if category == 'builder':
                                    builder_referral += int(contrib_points * 0.1)
                                elif category == 'validator':
                                    validator_referral += int(contrib_points * 0.1)

                        points += builder_referral + validator_referral

                # Create leaderboard entry
                entries_to_create.append(LeaderboardEntry(
                    user_id=user_id,
                    type=leaderboard_type,
                    total_points=points,
                    graduation_date=graduation_date
                ))

        # Bulk create leaderboard entries
        if entries_to_create:
            LeaderboardEntry.objects.bulk_create(entries_to_create, batch_size=1000)

        # Update ranks once per leaderboard
        for leaderboard_type in LEADERBOARD_CONFIG.keys():
            LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)

        return f"Recalculated {len(user_ids)} users across {len(LEADERBOARD_CONFIG)} leaderboards and {len(referral_points_to_create)} referrers"