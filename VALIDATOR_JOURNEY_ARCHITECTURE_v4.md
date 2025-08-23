# Validator Journey Architecture Documentation v4 - Final Implementation

## Overview
The Validator Journey feature implements a multi-tiered leaderboard system that tracks users' progression from waitlist to active validator status. This version represents the final implementation with unified configuration, proper point tracking, and graduation handling.

## Core Design Principles
1. **Badge-Based Membership**: Leaderboard placement determined by contribution badges
2. **Category-Specific Points**: Each leaderboard calculates points from specific contribution categories
3. **Frozen Graduation Points**: Points are frozen when users graduate from waitlist to validator
4. **Independent Leaderboards**: Each type has its own point calculation and ranking logic
5. **Unified Configuration**: Single source of truth for leaderboard types and their behavior

## Backend Implementation

### 1. Data Models (`backend/leaderboard/models.py`)

#### 1.1 LeaderboardEntry Model
```python
class LeaderboardEntry(BaseModel):
    """
    Represents a user's position on a specific leaderboard type.
    Each leaderboard has independent point calculations.
    """
    # Choices defined dynamically from LEADERBOARD_CONFIG
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
```

#### 1.2 Unified Leaderboard Configuration
```python
# At top of leaderboard/models.py

def has_contribution_badge(user, slug):
    """Helper to check if user has a specific contribution badge"""
    from contributions.models import Contribution
    return Contribution.objects.filter(
        user=user,
        contribution_type__slug=slug
    ).exists()

def has_category_contributions(user, category_slug):
    """Helper to check if user has contributions in a category"""
    from contributions.models import Contribution
    return Contribution.objects.filter(
        user=user,
        contribution_type__category__slug=category_slug
    ).exists()

def calculate_category_points(user, category_slug):
    """Calculate total points from a specific category"""
    from contributions.models import Contribution
    from django.db.models import Sum
    
    return Contribution.objects.filter(
        user=user,
        contribution_type__category__slug=category_slug
    ).aggregate(
        total=Sum('frozen_global_points')
    )['total'] or 0

def calculate_waitlist_points(user):
    """Calculate validator category points before graduation date"""
    from contributions.models import Contribution
    from django.db.models import Sum
    
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
    
    return query.aggregate(total=Sum('frozen_global_points'))['total'] or 0

def calculate_graduation_points(user):
    """
    For graduation leaderboard - returns existing frozen points or calculates them.
    Returns tuple of (points, should_update, graduation_date)
    """
    from contributions.models import Contribution
    from django.utils import timezone
    
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
```

#### 1.3 Updated Signal Handlers
```python
@receiver(post_save, sender=Contribution)
def update_leaderboard_on_contribution(sender, instance, created, **kwargs):
    """
    When a contribution is saved, update all affected leaderboard entries.
    """
    update_user_leaderboard_entries(instance.user)

def update_user_leaderboard_entries(user):
    """
    Core function that manages all of a user's leaderboard placements.
    Handles graduation, point calculations, and rank updates.
    """
    from django.utils import timezone
    
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
        update_leaderboard_type_ranks(leaderboard_type)

def update_leaderboard_type_ranks(leaderboard_type):
    """
    Update ranks for a specific leaderboard type.
    Uses configuration to determine ranking order.
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
    
    # Get visible user entries
    entries = list(
        LeaderboardEntry.objects.filter(
            type=leaderboard_type,
            user__visible=True
        ).order_by(*order_fields)
    )
    
    # Bulk update ranks
    for i, entry in enumerate(entries, 1):
        entry.rank = i
    
    if entries:
        LeaderboardEntry.objects.bulk_update(entries, ['rank'], batch_size=1000)
    
    # Set null rank for non-visible users
    LeaderboardEntry.objects.filter(
        type=leaderboard_type,
        user__visible=False
    ).update(rank=None)

def recalculate_all_leaderboards():
    """
    Admin command to recalculate all leaderboard entries from scratch.
    Called from admin panel shortcut.
    """
    from django.db import transaction
    from users.models import User
    
    with transaction.atomic():
        # Clear all existing entries
        LeaderboardEntry.objects.all().delete()
        
        # Get all users with any contributions
        users = User.objects.filter(
            contributions__isnull=False
        ).distinct().prefetch_related(
            'contributions__contribution_type__category'
        )
        
        # Process each user
        for user in users:
            update_user_leaderboard_entries(user)
        
        # Update ranks for all leaderboard types
        for leaderboard_type in LEADERBOARD_CONFIG.keys():
            update_leaderboard_type_ranks(leaderboard_type)
        
        return f"Recalculated {users.count()} users across {len(LEADERBOARD_CONFIG)} leaderboards"
```

### 2. Validator Model Changes (`backend/validators/models.py`)

```python
class Validator(NodeVersionMixin, BaseModel):
    """
    Represents a validator with their node version information.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='validator'
    )
    # node_version inherited from NodeVersionMixin
    
    # Note: points_at_waitlist_graduation removed - handled by graduation leaderboard
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
```

### 3. API Views Updates (`backend/leaderboard/views.py`)

```python
class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing leaderboards.
    """
    queryset = LeaderboardEntry.objects.filter(user__visible=True)
    serializer_class = LeaderboardEntrySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__name', 'user__address']
    ordering_fields = ['rank', 'total_points', 'last_update']
    ordering = ['rank']
    pagination_class = None
    
    def get_queryset(self):
        """
        Filter leaderboard by type and handle ordering.
        """
        queryset = super().get_queryset()
        
        # Get type from query params
        leaderboard_type = self.request.query_params.get('type')
        
        if leaderboard_type:
            queryset = queryset.filter(type=leaderboard_type)
        else:
            # Default to validator leaderboard
            queryset = queryset.filter(type='validator')
        
        # Handle rank ordering
        order = self.request.query_params.get('order', 'asc')
        if order == 'desc':
            return queryset.order_by('-rank')
        return queryset.order_by('rank')
    
    @action(detail=False, methods=['get'])
    def validator_waitlist_stats(self, request):
        """
        Get comprehensive statistics for the waitlist dashboard.
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        
        # Waitlist statistics
        waitlist_entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist',
            user__visible=True
        )
        
        # Graduation statistics
        graduation_entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist-graduation',
            user__visible=True
        )
        
        # Calculate statistics
        waitlist_stats = waitlist_entries.aggregate(
            total_participants=Count('id'),
            total_points=Sum('total_points')
        )
        
        graduation_stats = graduation_entries.aggregate(
            total_graduated=Count('id'),
            total_graduated_points=Sum('total_points')
        )
        
        # Get contribution counts
        waitlist_user_ids = waitlist_entries.values_list('user_id', flat=True)
        graduated_user_ids = graduation_entries.values_list('user_id', flat=True)
        
        waitlist_contributions = Contribution.objects.filter(
            user_id__in=waitlist_user_ids
        ).count()
        
        graduated_contributions = Contribution.objects.filter(
            user_id__in=graduated_user_ids
        ).count()
        
        return Response({
            'total_participants': waitlist_stats['total_participants'] or 0,
            'total_contributions': waitlist_contributions,
            'total_graduated_contributions': graduated_contributions,
            'total_points': waitlist_stats['total_points'] or 0,
            'total_graduated_points': graduation_stats['total_graduated_points'] or 0,
            'total_graduated': graduation_stats['total_graduated'] or 0
        })
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def recalculate(self, request):
        """
        Admin action to recalculate all leaderboards.
        """
        from leaderboard.models import recalculate_all_leaderboards
        
        result = recalculate_all_leaderboards()
        return Response({
            'message': result,
            'status': 'success'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get all available leaderboard types and their configuration.
        """
        from leaderboard.models import LEADERBOARD_CONFIG
        
        types_info = []
        for key, config in LEADERBOARD_CONFIG.items():
            types_info.append({
                'key': key,
                'name': config['name'],
                'ranking_order': config['ranking_order']
            })
        
        return Response(types_info)
```

### 4. Contribution Highlights Update (`backend/contributions/views.py`)

```python
@action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
def highlights(self, request):
    """
    Get contribution highlights with proper waitlist filtering.
    """
    from contributions.models import Category, ContributionType, Contribution
    from django.db.models import Q
    
    limit = int(request.query_params.get('limit', 10))
    category_slug = request.query_params.get('category')
    waitlist_only = request.query_params.get('waitlist_only', 'false').lower() == 'true'
    
    queryset = ContributionHighlight.objects.all()
    
    # Filter by category if provided
    if category_slug:
        try:
            category = Category.objects.get(slug=category_slug)
            queryset = queryset.filter(
                contribution__contribution_type__category=category
            )
        except Category.DoesNotExist:
            return Response([])
    
    if waitlist_only:
        # Get all users with waitlist badge
        waitlist_type = ContributionType.objects.filter(
            slug='validator-waitlist'
        ).first()
        
        if not waitlist_type:
            return Response([])
        
        waitlist_users = Contribution.objects.filter(
            contribution_type=waitlist_type
        ).values_list('user_id', flat=True).distinct()
        
        # Build complex query for graduated users
        validator_type = ContributionType.objects.filter(
            slug='validator'
        ).first()
        
        if validator_type:
            # Get graduation dates for each user
            graduation_dates = {}
            validator_contribs = Contribution.objects.filter(
                contribution_type=validator_type,
                user_id__in=waitlist_users
            ).values('user_id', 'contribution_date')
            
            for vc in validator_contribs:
                if vc['user_id'] not in graduation_dates:
                    graduation_dates[vc['user_id']] = vc['contribution_date']
            
            # Build Q objects for filtering
            q_filters = Q()
            for user_id in waitlist_users:
                if user_id in graduation_dates:
                    # Graduated - only show pre-graduation highlights
                    q_filters |= Q(
                        contribution__user_id=user_id,
                        contribution__contribution_date__lt=graduation_dates[user_id]
                    )
                else:
                    # Still on waitlist - show all highlights
                    q_filters |= Q(contribution__user_id=user_id)
            
            queryset = queryset.filter(q_filters)
        else:
            # No validator type, just filter by waitlist users
            queryset = queryset.filter(contribution__user_id__in=waitlist_users)
    
    # Order and limit
    highlights = queryset.select_related(
        'contribution__user',
        'contribution__contribution_type__category'
    ).order_by('-created_at')[:limit]
    
    serializer = ContributionHighlightSerializer(highlights, many=True)
    return Response(serializer.data)
```

### 5. Database Migrations

#### 5.1 Complete Leaderboard Migration
```python
# backend/leaderboard/migrations/0013_unified_leaderboard_system.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('leaderboard', '0012_finalize_leaderboard_types'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='leaderboardentry',
            name='last_update',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='leaderboardentry',
            name='graduation_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        
        # Update type field - remove db_column override
        migrations.AlterField(
            model_name='leaderboardentry',
            name='type',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('validator', 'Validator'),
                    ('builder', 'Builder'),
                    ('validator-waitlist', 'Validator Waitlist'),
                    ('validator-waitlist-graduation', 'Validator Waitlist Graduation'),
                ]
            ),
        ),
        
        # Remove deprecated category field
        migrations.RemoveField(
            model_name='leaderboardentry',
            name='category',
        ),
    ]
```

#### 5.2 Remove Validator Graduation Points
```python
# backend/validators/migrations/0006_remove_graduation_points.py

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('validators', '0005_remove_waitlist_graduation_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='validator',
            name='points_at_waitlist_graduation',
        ),
    ]
```

## Frontend Implementation

### 1. Updated Waitlist Route (`frontend/src/routes/Waitlist.svelte`)

```javascript
<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import api, { leaderboardAPI, contributionsAPI } from '../lib/api';
  
  // State with individual loading flags
  let waitlistUsers = $state([]);
  let graduatedUsers = $state([]);
  let featuredContributions = $state([]);
  let statistics = $state({});
  
  // Loading states for progressive rendering
  let sectionsLoading = $state({
    stats: true,
    waitlist: true,
    graduated: true,
    featured: true
  });
  
  onMount(() => {
    // Load all sections in parallel for better UX
    loadAllSections();
  });
  
  async function loadAllSections() {
    // Launch all fetches in parallel
    const promises = [
      fetchStatistics(),
      fetchWaitlistUsers(),
      fetchGraduatedUsers(),
      fetchFeaturedContributions()
    ];
    
    // Wait for all to complete (but each updates its own state)
    await Promise.allSettled(promises);
  }
  
  async function fetchStatistics() {
    try {
      const response = await leaderboardAPI.getWaitlistStats();
      statistics = response.data;
    } catch (error) {
      console.error('Failed to load statistics:', error);
      statistics = {
        total_participants: 0,
        total_graduated: 0,
        total_points: 0
      };
    } finally {
      sectionsLoading.stats = false;
    }
  }
  
  async function fetchWaitlistUsers() {
    try {
      const response = await leaderboardAPI.getLeaderboardByType('validator-waitlist');
      waitlistUsers = response.data || [];
    } catch (error) {
      console.error('Failed to load waitlist:', error);
      waitlistUsers = [];
    } finally {
      sectionsLoading.waitlist = false;
    }
  }
  
  async function fetchGraduatedUsers() {
    try {
      // Graduation leaderboard is sorted by date (most recent first)
      const response = await leaderboardAPI.getLeaderboardByType(
        'validator-waitlist-graduation'
      );
      graduatedUsers = response.data || [];
    } catch (error) {
      console.error('Failed to load graduated users:', error);
      graduatedUsers = [];
    } finally {
      sectionsLoading.graduated = false;
    }
  }
  
  async function fetchFeaturedContributions() {
    try {
      const response = await contributionsAPI.getHighlights({
        waitlist_only: true,
        limit: 5
      });
      featuredContributions = response.data || [];
    } catch (error) {
      console.error('Failed to load featured contributions:', error);
      featuredContributions = [];
    } finally {
      sectionsLoading.featured = false;
    }
  }
  
  // Helper functions
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch {
      return dateString;
    }
  }
  
  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }
</script>

<!-- Progressive rendering with skeleton loaders -->
<div class="space-y-6">
  <h1 class="text-2xl font-bold text-gray-900">
    Validator Waitlist Journey
  </h1>
  
  <!-- Stats Section with skeleton loaders -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    {#if sectionsLoading.stats}
      {#each [1, 2, 3] as _}
        <div class="bg-white rounded-lg p-6 animate-pulse">
          <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div class="h-8 bg-gray-200 rounded w-1/2"></div>
        </div>
      {/each}
    {:else}
      <StatCard 
        title="Waitlist Participants" 
        value={statistics.total_participants || 0}
        icon="users"
        color="amber"
      />
      <StatCard 
        title="Total Graduated" 
        value={statistics.total_graduated || 0}
        icon="graduation"
        color="green"
      />
      <StatCard 
        title="Total Points" 
        value={statistics.total_points || 0}
        icon="points"
        color="purple"
      />
    {/if}
  </div>
  
  <!-- Main content sections -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Waitlist Rankings -->
    <section>
      <h2 class="text-lg font-semibold mb-4">Race to Testnet Asimov</h2>
      {#if sectionsLoading.waitlist}
        <LoadingSkeleton type="list" items={5} />
      {:else if waitlistUsers.length === 0}
        <EmptyState message="No participants in the waitlist yet" />
      {:else}
        <LeaderboardList 
          entries={waitlistUsers.slice(0, 10)} 
          showRank={true}
          type="waitlist"
        />
      {/if}
    </section>
    
    <!-- Recently Graduated -->
    <section>
      <h2 class="text-lg font-semibold mb-4">Recently Graduated</h2>
      {#if sectionsLoading.graduated}
        <LoadingSkeleton type="list" items={5} />
      {:else if graduatedUsers.length === 0}
        <EmptyState message="No graduations yet" />
      {:else}
        <GraduationList 
          entries={graduatedUsers.slice(0, 10)}
          showDate={true}
        />
      {/if}
    </section>
  </div>
  
  <!-- Featured Contributions -->
  <section>
    <h2 class="text-lg font-semibold mb-4">Featured Contributions</h2>
    {#if sectionsLoading.featured}
      <LoadingSkeleton type="cards" items={3} />
    {:else if featuredContributions.length === 0}
      <EmptyState message="No featured contributions yet" />
    {:else}
      <ContributionGrid contributions={featuredContributions} />
    {/if}
  </section>
</div>
```

### 2. API Integration Updates (`frontend/src/lib/api.js`)

```javascript
export const leaderboardAPI = {
  // Get specific leaderboard type
  getLeaderboardByType: (type) => 
    api.get('/leaderboard/', { params: { type } }),
  
  // Get leaderboard with custom ordering
  getLeaderboard: (params) => 
    api.get('/leaderboard/', { params }),
  
  // Get waitlist statistics
  getWaitlistStats: () => 
    api.get('/leaderboard/validator-waitlist-stats/'),
  
  // Get available leaderboard types
  getTypes: () => 
    api.get('/leaderboard/types/'),
  
  // Admin recalculation
  recalculateAll: () => 
    api.post('/leaderboard/recalculate/')
};
```

## Performance Optimizations

### 1. Batch Processing for Rules Evaluation

```python
def evaluate_users_batch(users):
    """
    Evaluate leaderboard memberships for multiple users efficiently.
    """
    from contributions.models import Contribution
    from django.db.models import Prefetch
    
    # Prefetch all contributions with related data
    users = users.prefetch_related(
        Prefetch(
            'contributions',
            queryset=Contribution.objects.select_related(
                'contribution_type',
                'contribution_type__category'
            )
        )
    )
    
    results = {}
    for user in users:
        # Evaluate using prefetched data
        qualified = []
        for leaderboard_type, config in LEADERBOARD_CONFIG.items():
            if config['participants'](user):
                qualified.append(leaderboard_type)
        results[user.id] = qualified
    
    return results
```

### 2. Optimized Rank Updates

```python
def bulk_update_all_ranks():
    """
    Update ranks for all leaderboard types in a single pass.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Update each leaderboard type
        for leaderboard_type, config in LEADERBOARD_CONFIG.items():
            if config['ranking_order'] == '-graduation_date':
                order_clause = 'graduation_date DESC NULLS LAST, user_id'
            else:
                order_clause = 'total_points DESC, user_id'
            
            cursor.execute("""
                WITH ranked AS (
                    SELECT 
                        id,
                        ROW_NUMBER() OVER (ORDER BY %s) as new_rank
                    FROM leaderboard_leaderboardentry
                    WHERE type = %s
                    AND user_id IN (
                        SELECT id FROM users_user WHERE visible = true
                    )
                )
                UPDATE leaderboard_leaderboardentry
                SET rank = ranked.new_rank
                FROM ranked
                WHERE leaderboard_leaderboardentry.id = ranked.id
            """ % (order_clause, '%s'), [leaderboard_type])
```

## Testing Suite

### Core Test Cases

```python
# backend/leaderboard/tests/test_unified_system.py

from django.test import TestCase
from django.utils import timezone
from users.models import User
from contributions.models import Contribution, ContributionType, Category
from leaderboard.models import (
    LeaderboardEntry, 
    LEADERBOARD_CONFIG,
    update_user_leaderboard_entries,
    recalculate_all_leaderboards
)

class UnifiedLeaderboardTestCase(TestCase):
    def setUp(self):
        # Create categories
        self.validator_category = Category.objects.create(
            slug='validator',
            name='Validator'
        )
        self.builder_category = Category.objects.create(
            slug='builder',
            name='Builder'
        )
        
        # Create contribution types
        self.waitlist_type = ContributionType.objects.create(
            slug='validator-waitlist',
            name='Validator Waitlist',
            category=self.validator_category
        )
        self.validator_type = ContributionType.objects.create(
            slug='validator',
            name='Validator',
            category=self.validator_category
        )
        
        self.user = User.objects.create(
            email='test@example.com',
            visible=True
        )
    
    def test_configuration_integrity(self):
        """Test that all configured leaderboards work correctly"""
        for key, config in LEADERBOARD_CONFIG.items():
            self.assertIn('name', config)
            self.assertIn('participants', config)
            self.assertIn('points_calculator', config)
            self.assertIn('ranking_order', config)
            self.assertTrue(callable(config['participants']))
            self.assertTrue(callable(config['points_calculator']))
    
    def test_graduation_flow(self):
        """Test complete graduation flow with frozen points"""
        # Add to waitlist with points
        Contribution.objects.create(
            user=self.user,
            contribution_type=self.waitlist_type,
            points=10,
            frozen_global_points=10,
            contribution_date=timezone.now()
        )
        
        # Update leaderboards
        update_user_leaderboard_entries(self.user)
        
        # Should be on waitlist only
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user,
                type='validator-waitlist'
            ).exists()
        )
        self.assertFalse(
            LeaderboardEntry.objects.filter(
                user=self.user,
                type='validator-waitlist-graduation'
            ).exists()
        )
        
        # Graduate to validator
        grad_date = timezone.now()
        Contribution.objects.create(
            user=self.user,
            contribution_type=self.validator_type,
            points=5,
            frozen_global_points=5,
            contribution_date=grad_date
        )
        
        # Update leaderboards again
        update_user_leaderboard_entries(self.user)
        
        # Should be on graduation and validator, not waitlist
        self.assertFalse(
            LeaderboardEntry.objects.filter(
                user=self.user,
                type='validator-waitlist'
            ).exists()
        )
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user,
                type='validator'
            ).exists()
        )
        
        grad_entry = LeaderboardEntry.objects.get(
            user=self.user,
            type='validator-waitlist-graduation'
        )
        self.assertEqual(grad_entry.total_points, 10)  # Frozen at graduation
        self.assertEqual(grad_entry.graduation_date, grad_date)
        
        # Add more validator contributions
        Contribution.objects.create(
            user=self.user,
            contribution_type=self.validator_type,
            points=20,
            frozen_global_points=20,
            contribution_date=timezone.now()
        )
        
        update_user_leaderboard_entries(self.user)
        
        # Graduation points should remain frozen
        grad_entry.refresh_from_db()
        self.assertEqual(grad_entry.total_points, 10)
        
        # Validator leaderboard should have updated points
        validator_entry = LeaderboardEntry.objects.get(
            user=self.user,
            type='validator'
        )
        self.assertEqual(validator_entry.total_points, 25)  # 5 + 20
    
    def test_affected_leaderboards_tracking(self):
        """Test that removed leaderboards get rank updates"""
        # Create multiple users
        users = []
        for i in range(3):
            user = User.objects.create(
                email=f'user{i}@test.com',
                visible=True
            )
            users.append(user)
            
            # All start on waitlist
            Contribution.objects.create(
                user=user,
                contribution_type=self.waitlist_type,
                points=10 * (i + 1),
                frozen_global_points=10 * (i + 1)
            )
            update_user_leaderboard_entries(user)
        
        # Verify initial ranks
        entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist'
        ).order_by('rank')
        self.assertEqual(entries.count(), 3)
        
        # Graduate middle user
        Contribution.objects.create(
            user=users[1],
            contribution_type=self.validator_type,
            points=5,
            frozen_global_points=5
        )
        update_user_leaderboard_entries(users[1])
        
        # Check waitlist was reranked after removal
        entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist'
        ).order_by('rank')
        self.assertEqual(entries.count(), 2)
        self.assertEqual(entries[0].rank, 1)
        self.assertEqual(entries[1].rank, 2)
    
    def test_recalculation(self):
        """Test complete recalculation function"""
        # Create test data
        for i in range(5):
            user = User.objects.create(
                email=f'test{i}@example.com',
                visible=True
            )
            Contribution.objects.create(
                user=user,
                contribution_type=self.waitlist_type,
                points=10 * (i + 1),
                frozen_global_points=10 * (i + 1)
            )
        
        # Recalculate everything
        result = recalculate_all_leaderboards()
        
        # Verify result message
        self.assertIn('5 users', result)
        self.assertIn(str(len(LEADERBOARD_CONFIG)), result)
        
        # Verify entries created with correct ranks
        entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist'
        ).order_by('rank')
        
        self.assertEqual(entries.count(), 5)
        for i, entry in enumerate(entries):
            self.assertEqual(entry.rank, i + 1)
```

## Summary of v4 Improvements

### Key Architectural Changes:
1. **Unified Configuration**: Single `LEADERBOARD_CONFIG` dictionary controls all leaderboard behavior
2. **No Special Cases**: Graduation handling integrated into points calculator
3. **Affected Leaderboards Tracking**: Properly updates ranks for removed leaderboards
4. **Clean Separation**: Each leaderboard type has clear participants and points functions
5. **Configuration-Driven Ranking**: Ranking order specified in configuration

### Technical Improvements:
1. **Removed Special Cases**: No `if leaderboard_type == 'validator-waitlist-graduation'` checks
2. **Dynamic Choices**: Leaderboard types derived from configuration
3. **Bulk Operations**: Efficient rank updates using bulk_update
4. **Proper Freezing**: Graduation points calculator returns update flag
5. **Clean API**: New `/types` endpoint exposes available leaderboards

### Database Changes:
1. Remove `db_column` override from type field
2. Add `last_update` and `graduation_date` fields
3. Remove deprecated `category` field
4. Remove `points_at_waitlist_graduation` from Validator

This implementation provides a maintainable, extensible system where new leaderboard types can be added by simply updating the `LEADERBOARD_CONFIG` dictionary.