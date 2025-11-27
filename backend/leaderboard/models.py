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
    # For builder category, check if user has a Builder record (completed journey)
    if category_slug == 'builder':
        return hasattr(user, 'builder') and user.builder is not None

    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug=category_slug
    )
    return query.exists()


def calculate_category_points(user, category_slug):
    """Calculate total points from a specific category, including all contribution types"""
    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug=category_slug
    )
    return query.aggregate(
        total=Sum('frozen_global_points')
    )['total'] or 0


def calculate_waitlist_points(user):
    """
    Calculate waitlist points including both contributions and referral points.
    Formula: contribution_points + referral_points (simple sum, easy to adjust)

    Anti-bot: Referral points only count contributions from referred users with real engagement:
    - Builder: referred user must be in Builder table
    - Validator: referred user must have other validator contributions besides validator-waitlist
    """
    from builders.models import Builder

    # Find graduation contribution if exists
    grad_contrib = Contribution.objects.filter(
        user=user,
        contribution_type__slug='validator'
    ).order_by('contribution_date').first()

    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug='validator'
    ).exclude(contribution_type__slug='validator')

    if grad_contrib:
        # Only count contributions before and on graduation day
        query = query.filter(contribution_date__lte=grad_contrib.contribution_date)

    contribution_points = query.aggregate(total=Sum('frozen_global_points'))['total'] or 0

    # Calculate referral points
    if grad_contrib:
        # For graduated users: calculate referral points ONLY from contributions before graduation
        # Anti-bot: Only count contributions from referred users with real engagement
        from users.models import User
        referred_user_ids = list(User.objects.filter(referred_by=user).values_list('id', flat=True))

        if referred_user_ids:
            # Get referred users who are in Builder table
            referred_builders = set(Builder.objects.filter(
                user_id__in=referred_user_ids
            ).values_list('user_id', flat=True))

            # Get referred users who have real validator contributions (not just validator-waitlist)
            # Note: Check for any real validator contribution, not just before graduation
            referred_with_real_validator = set(Contribution.objects.filter(
                user_id__in=referred_user_ids,
                contribution_type__category__slug='validator'
            ).exclude(
                contribution_type__slug='validator-waitlist'
            ).values_list('user_id', flat=True))

            # Builder referrals - only from referred users in Builder table
            builder_referral = int((Contribution.objects.filter(
                user_id__in=referred_builders,
                contribution_type__category__slug='builder',
                contribution_date__lte=grad_contrib.contribution_date
            ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

            # Validator referrals - only from referred users with real validator contributions
            validator_referral = int((Contribution.objects.filter(
                user_id__in=referred_with_real_validator,
                contribution_type__category__slug='validator',
                contribution_date__lte=grad_contrib.contribution_date
            ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

            referral_points = builder_referral + validator_referral
        else:
            referral_points = 0
    else:
        # For current waitlist users: use total referral points from ReferralPoints table
        # (which is already maintained with anti-bot filtering by update_referrer_points)
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
        'participants': lambda user: hasattr(user, 'validator'),  # Has Validator profile
        'points_calculator': lambda user: calculate_category_points(user, 'validator'),
        'ranking_order': '-total_points',  # Highest points first
    },
    'builder': {
        'name': 'Builder',
        'participants': lambda user: hasattr(user, 'builder'),  # Has Builder profile
        'points_calculator': lambda user: calculate_category_points(user, 'builder'),
        'ranking_order': '-total_points',
    },
    'validator-waitlist': {
        'name': 'Validator Waitlist',
        'participants': lambda user: (
            has_contribution_badge(user, 'validator-waitlist') and
            not hasattr(user, 'validator')  # Not graduated yet
        ),
        'points_calculator': lambda user: calculate_waitlist_points(user),
        'ranking_order': '-total_points',
    },
    'validator-waitlist-graduation': {
        'name': 'Validator Waitlist Graduation',
        'participants': lambda user: (
            has_contribution_badge(user, 'validator-waitlist') and
            hasattr(user, 'validator')  # Graduated
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
        """
        if leaderboard_type not in LEADERBOARD_CONFIG:
            return
        
        config = LEADERBOARD_CONFIG[leaderboard_type]
        ranking_order = config['ranking_order']
        
        # Build order_by fields based on configuration
        if ranking_order == '-graduation_date':
            order_fields = ['-graduation_date', 'user__name']
        elif ranking_order == '-total_points':
            order_fields = ['-total_points', 'user__name']
        else:
            order_fields = [ranking_order, 'user__name']
        
        # First, set all non-visible users' ranks to null
        cls.objects.filter(
            type=leaderboard_type,
            user__visible=False
        ).update(rank=None)
        
        # Then rank only visible users
        entries = list(
            cls.objects.filter(
                type=leaderboard_type,
                user__visible=True
            ).order_by(*order_fields)
        )
        
        # Bulk update ranks
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
    Update referral points when a referred user makes a contribution.

    Anti-bot: Only counts contributions from referred users with real engagement:
    - Builder: referred user must be in Builder table (uses mini-recalculation)
    - Validator: referred user must have other validator contributions besides validator-waitlist
    """
    from builders.models import Builder
    from users.models import User

    referrer = contribution.user.referred_by
    if not referrer:
        return

    # Get or create referral points record
    rp, _ = ReferralPoints.objects.get_or_create(user=referrer)

    # Get the contribution category and slug
    category_slug = contribution.contribution_type.category.slug if contribution.contribution_type.category else None
    contribution_slug = contribution.contribution_type.slug

    if category_slug == 'builder':
        # For builder contributions: recalculate all builder referral points
        # This ensures builder-welcome is only counted when user is in Builder table
        referred_user_ids = list(User.objects.filter(referred_by=referrer).values_list('id', flat=True))
        referred_builders = set(Builder.objects.filter(
            user_id__in=referred_user_ids
        ).values_list('user_id', flat=True))

        rp.builder_points = int((Contribution.objects.filter(
            user_id__in=referred_builders,
            contribution_type__category__slug='builder'
        ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)
        rp.save(update_fields=['builder_points'])

    elif category_slug == 'validator':
        # For validator contributions: use incremental logic with anti-bot check
        user = contribution.user
        points_to_add = int(contribution.frozen_global_points * 0.1)

        if contribution_slug == 'validator-waitlist':
            # Check if user has any OTHER validator contributions
            has_other_validator = Contribution.objects.filter(
                user=user,
                contribution_type__category__slug='validator'
            ).exclude(contribution_type__slug='validator-waitlist').exists()

            if not has_other_validator:
                # Don't count validator-waitlist until user has real engagement
                return
            # User has other contributions, count validator-waitlist
            rp.validator_points += points_to_add
        else:
            # Non-waitlist validator contribution - always count it
            rp.validator_points += points_to_add

            # Check if this is the first non-waitlist validator contribution
            # If so, retroactively add validator-waitlist points
            other_validator_count = Contribution.objects.filter(
                user=user,
                contribution_type__category__slug='validator'
            ).exclude(contribution_type__slug='validator-waitlist').count()

            if other_validator_count == 1:  # This is the first non-waitlist contribution
                waitlist_points = Contribution.objects.filter(
                    user=user,
                    contribution_type__slug='validator-waitlist'
                ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0
                if waitlist_points > 0:
                    rp.validator_points += int(waitlist_points * 0.1)

        rp.save(update_fields=['validator_points'])
    else:
        # No category means no points added, no need to update leaderboard
        return

    # CRITICAL: Update referrer's validator-waitlist leaderboard entry
    # This prevents LeaderboardEntry.total_points from being stale
    if LeaderboardEntry.objects.filter(user=referrer, type='validator-waitlist').exists():
        config = LEADERBOARD_CONFIG['validator-waitlist']
        calculator = config['points_calculator']
        points = calculator(referrer)

        LeaderboardEntry.objects.update_or_create(
            user=referrer,
            type='validator-waitlist',
            defaults={'total_points': points}
        )

        LeaderboardEntry.update_leaderboard_ranks('validator-waitlist')


def ensure_builder_status(user, reference_date):
    """
    Create missing builder-welcome, builder contributions and Builder profile.
    Used to auto-grant builder status to users who have builder contributions.
    """
    from builders.models import Builder

    try:
        welcome_type = ContributionType.objects.get(slug='builder-welcome')
        builder_type = ContributionType.objects.get(slug='builder')
    except ContributionType.DoesNotExist:
        return

    # Create Builder profile
    if not hasattr(user, 'builder'):
        Builder.objects.create(user=user)

    # (signals would create LeaderboardEntry records, causing duplicates during recalculation)
    contributions_to_create = []

    if not Contribution.objects.filter(user=user, contribution_type=welcome_type).exists():
        contributions_to_create.append(Contribution(
            user=user,
            contribution_type=welcome_type,
            points=20,
            contribution_date=timezone.now(),
            frozen_global_points=20
        ))

    if not Contribution.objects.filter(user=user, contribution_type=builder_type).exists():
        contributions_to_create.append(Contribution(
            user=user,
            contribution_type=builder_type,
            points=50,
            contribution_date=timezone.now(),
            frozen_global_points=50
        ))

    if contributions_to_create:
        Contribution.objects.bulk_create(contributions_to_create)


@transaction.atomic
def recalculate_referrer_points(referrer):
    """
    Update referral points when referred user makes contribution.
    Efficiently calculates points per category.

    Anti-bot: Only counts contributions from referred users with real engagement:
    - Builder: referred user must be in Builder table
    - Validator: referred user must have other validator contributions besides validator-waitlist
    """
    from users.models import User
    from builders.models import Builder

    referred_user_ids = list(User.objects.filter(referred_by=referrer).values_list('id', flat=True))
    if not referred_user_ids:
        return

    rp, _ = ReferralPoints.objects.get_or_create(user=referrer)

    # Get referred users who are in Builder table
    referred_builders = set(Builder.objects.filter(
        user_id__in=referred_user_ids
    ).values_list('user_id', flat=True))

    # Get referred users who have real validator contributions (not just validator-waitlist)
    referred_with_real_validator = set(Contribution.objects.filter(
        user_id__in=referred_user_ids,
        contribution_type__category__slug='validator'
    ).exclude(
        contribution_type__slug='validator-waitlist'
    ).values_list('user_id', flat=True))

    # Calculate builder points - only from referred users in Builder table
    rp.builder_points = int((Contribution.objects.filter(
        user_id__in=referred_builders,
        contribution_type__category__slug='builder'
    ).aggregate(Sum('frozen_global_points'))['frozen_global_points__sum'] or 0) * 0.1)

    # Calculate validator points - only from referred users with real validator contributions
    rp.validator_points = int((Contribution.objects.filter(
        user_id__in=referred_with_real_validator,
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
    Optimized admin command to recalculate all leaderboard entries and referral points from scratch.

    Performance: Reduces queries from ~26,000 to ~15 by:
    - Loading all data in single queries
    - Processing qualifications in Python
    - Using bulk operations
    - Updating ranks once per leaderboard

    Called from admin panel shortcut.
    """
    from django.db import transaction
    from users.models import User
    from builders.models import Builder
    from validators.models import Validator
    from collections import defaultdict

    with transaction.atomic():
        # Save existing graduation entries to preserve frozen points
        # OPEN QUESTION: Should we recalculate graduation snapshots instead of preserving them?
        # Current: Preserves existing snapshots (performance, stability)
        # Alternative: Recalculate all snapshots (ensures correctness if logic changed)
        existing_graduations = {
            entry.user_id: {
                'points': entry.total_points,
                'graduation_date': entry.graduation_date
            }
            for entry in LeaderboardEntry.objects.filter(type='validator-waitlist-graduation')
        }

        # Clear all existing calculated data (except graduation entries are preserved above)
        LeaderboardEntry.objects.all().delete()
        ReferralPoints.objects.all().delete()

        # STEP 1: Auto-grant builder status to users with builder contributions but no Builder profile
        # Load contributions to identify users who need builder status
        initial_contributions = list(Contribution.objects.select_related(
            'contribution_type__category'
        ).values(
            'user_id',
            'contribution_type__slug',
            'contribution_type__category__slug',
            'contribution_date'
        ))

        # Load current Builder profiles
        initial_builders_set = set(Builder.objects.values_list('user_id', flat=True))

        # Group contributions by user and find those needing builder status
        user_builder_contribs = defaultdict(list)
        for contrib in initial_contributions:
            if (contrib['contribution_type__category__slug'] == 'builder' and
                contrib['contribution_type__slug'] not in ['builder-welcome', 'builder']):
                user_builder_contribs[contrib['user_id']].append(contrib['contribution_date'])

        # Create builder status for users who need it
        for user_id, dates in user_builder_contribs.items():
            if user_id not in initial_builders_set:
                try:
                    user = User.objects.get(id=user_id)
                    earliest_date = min(dates)
                    ensure_builder_status(user, earliest_date)
                except User.DoesNotExist:
                    pass

        # STEP 2: Load ALL contribution data (including newly created)
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

        # Load Builder and Validator profiles to determine leaderboard qualification
        builders_set = set(Builder.objects.values_list('user_id', flat=True))
        validators_set = set(Validator.objects.values_list('user_id', flat=True))

        # Group contributions by user
        user_contributions = defaultdict(list)
        for contrib in contributions:
            user_contributions[contrib['user_id']].append(contrib)

        # Group contributions by referrer for referral point calculation
        referrer_contributions = defaultdict(list)
        for contrib in contributions:
            if contrib['user__referred_by_id']:
                referrer_contributions[contrib['user__referred_by_id']].append(contrib)

        # Track which users have which contribution badges
        user_badges = defaultdict(set)
        for contrib in contributions:
            user_badges[contrib['user_id']].add(contrib['contribution_type__slug'])

        # Track users who have validator contributions OTHER than validator-waitlist
        # Used for anti-bot filtering in referral calculations
        users_with_real_validator_contribs = set()
        for contrib in contributions:
            if (contrib['contribution_type__category__slug'] == 'validator' and
                contrib['contribution_type__slug'] != 'validator-waitlist'):
                users_with_real_validator_contribs.add(contrib['user_id'])

        # Prepare bulk operations
        entries_to_create = []
        referral_points_to_create = []

        # Process each user with contributions
        for user_id, user_contribs in user_contributions.items():
            # Determine which leaderboards this user qualifies for
            qualified_leaderboards = []

            # Validator leaderboard: has Validator profile
            if user_id in validators_set:
                qualified_leaderboards.append('validator')

            # Builder leaderboard: has Builder profile
            if user_id in builders_set:
                qualified_leaderboards.append('builder')

            # Validator waitlist: has 'validator-waitlist' badge but NO Validator profile
            if 'validator-waitlist' in user_badges[user_id] and user_id not in validators_set:
                qualified_leaderboards.append('validator-waitlist')

            # Validator waitlist graduation: has 'validator-waitlist' badge AND Validator profile
            if 'validator-waitlist' in user_badges[user_id] and user_id in validators_set:
                qualified_leaderboards.append('validator-waitlist-graduation')

            # Calculate points for each qualified leaderboard
            for leaderboard_type in qualified_leaderboards:
                points = 0
                graduation_date = None

                if leaderboard_type == 'validator':
                    # Sum ALL validator category contributions
                    for contrib in user_contribs:
                        if contrib['contribution_type__category__slug'] == 'validator':
                            points += contrib['frozen_global_points'] or 0

                elif leaderboard_type == 'builder':
                    # Sum ALL builder category contributions (including builder-welcome)
                    for contrib in user_contribs:
                        if contrib['contribution_type__category__slug'] == 'builder':
                            points += contrib['frozen_global_points'] or 0

                elif leaderboard_type == 'validator-waitlist':
                    # Sum all validator category contributions (excluding graduation marker) + referral points
                    for contrib in user_contribs:
                        if (contrib['contribution_type__category__slug'] == 'validator' and
                            contrib['contribution_type__slug'] != 'validator'):
                            points += contrib['frozen_global_points'] or 0

                    # Add referral points if user is a referrer
                    # Anti-bot: Only count contributions from referred users with real engagement
                    if user_id in referrer_contributions:
                        builder_referral = 0
                        validator_referral = 0

                        for referred_contrib in referrer_contributions[user_id]:
                            referred_user_id = referred_contrib['user_id']
                            category = referred_contrib['contribution_type__category__slug']
                            contrib_points = referred_contrib['frozen_global_points'] or 0

                            # Builder: only count if referred user is in Builder table
                            if category == 'builder' and referred_user_id in builders_set:
                                builder_referral += int(contrib_points * 0.1)
                            # Validator: only count if referred user has real validator contributions
                            elif category == 'validator' and referred_user_id in users_with_real_validator_contribs:
                                validator_referral += int(contrib_points * 0.1)

                        points += builder_referral + validator_referral

                elif leaderboard_type == 'validator-waitlist-graduation':
                    # Check if this user already has a frozen graduation entry
                    if user_id in existing_graduations:
                        # Use existing frozen values - points never change after graduation
                        points = existing_graduations[user_id]['points']
                        graduation_date = existing_graduations[user_id]['graduation_date']
                    else:
                        # New graduation - calculate points to freeze
                        # Find graduation date (earliest validator contribution)
                        grad_date = None
                        for contrib in user_contribs:
                            if contrib['contribution_type__slug'] == 'validator':
                                contrib_date = contrib['contribution_date']
                                if grad_date is None or contrib_date < grad_date:
                                    grad_date = contrib_date

                        graduation_date = grad_date

                        # Calculate waitlist points at graduation
                        # Include all validator contributions up to (but not after) graduation
                        if grad_date is not None:
                            for contrib in user_contribs:
                                if contrib['contribution_type__category__slug'] == 'validator':
                                    # Include contributions on or before graduation date
                                    # but exclude the 'validator' contribution itself (graduation marker)
                                    if (contrib['contribution_date'] <= grad_date and
                                        contrib['contribution_type__slug'] != 'validator'):
                                        points += contrib['frozen_global_points'] or 0

                            # Add referral points earned up to graduation
                            # Anti-bot: Only count contributions from referred users with real engagement
                            if user_id in referrer_contributions:
                                builder_referral = 0
                                validator_referral = 0

                                for referred_contrib in referrer_contributions[user_id]:
                                    if referred_contrib['contribution_date'] <= grad_date:
                                        referred_user_id = referred_contrib['user_id']
                                        category = referred_contrib['contribution_type__category__slug']
                                        contrib_points = referred_contrib['frozen_global_points'] or 0

                                        # Builder: only count if referred user is in Builder table
                                        if category == 'builder' and referred_user_id in builders_set:
                                            builder_referral += int(contrib_points * 0.1)
                                        # Validator: only count if referred user has real validator contributions
                                        elif category == 'validator' and referred_user_id in users_with_real_validator_contribs:
                                            validator_referral += int(contrib_points * 0.1)

                                points += builder_referral + validator_referral

                # Create entry
                entries_to_create.append(LeaderboardEntry(
                    user_id=user_id,
                    type=leaderboard_type,
                    total_points=points,
                    graduation_date=graduation_date
                ))

        # Calculate referral points for all referrers
        # Anti-bot: Only count contributions from referred users with real engagement
        for referrer_id, referred_contribs in referrer_contributions.items():
            builder_points = 0
            validator_points = 0

            for contrib in referred_contribs:
                referred_user_id = contrib['user_id']
                category = contrib['contribution_type__category__slug']
                contrib_points = contrib['frozen_global_points'] or 0

                # Builder: only count if referred user is in Builder table
                if category == 'builder' and referred_user_id in builders_set:
                    builder_points += int(contrib_points * 0.1)
                # Validator: only count if referred user has real validator contributions
                elif category == 'validator' and referred_user_id in users_with_real_validator_contribs:
                    validator_points += int(contrib_points * 0.1)

            referral_points_to_create.append(ReferralPoints(
                user_id=referrer_id,
                builder_points=builder_points,
                validator_points=validator_points
            ))

        # Bulk create leaderboard entries
        LeaderboardEntry.objects.bulk_create(entries_to_create, batch_size=500)

        # Bulk create referral points
        ReferralPoints.objects.bulk_create(referral_points_to_create, batch_size=500)

        # Update ranks once per leaderboard type
        for leaderboard_type in ['validator', 'builder', 'validator-waitlist', 'validator-waitlist-graduation']:
            LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)

        return f"Recalculated {len(user_contributions)} users across {len(LEADERBOARD_CONFIG)} leaderboards with {len(referral_points_to_create)} referrers"