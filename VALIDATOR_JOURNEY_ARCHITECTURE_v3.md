# Validator Journey Architecture Documentation v3 - Implementation Guide

## Overview
The Validator Journey feature implements a multi-tiered leaderboard system that tracks users' progression from waitlist to active validator status. This version represents the correct implementation with proper point tracking, graduation handling, and performance optimizations.

## Core Design Principles
1. **Badge-Based Membership**: Leaderboard placement determined by contribution badges
2. **Category-Specific Points**: Each leaderboard calculates points from specific contribution categories
3. **Frozen Graduation Points**: Points are frozen when users graduate from waitlist to validator
4. **Independent Leaderboards**: Each type has its own point calculation and ranking logic

## Backend Implementation

### 1. Data Models (`backend/leaderboard/models.py`)

#### 1.1 LeaderboardEntry Model - REQUIRED CHANGES
```python
class LeaderboardEntry(BaseModel):
    """
    Represents a user's position on a specific leaderboard type.
    Each leaderboard has independent point calculations.
    """
    LEADERBOARD_TYPES = [
        ('validator', 'Validator'),
        ('builder', 'Builder'), 
        ('validator-waitlist', 'Validator Waitlist'),
        ('validator-waitlist-graduation', 'Validator Waitlist Graduation'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='leaderboard_entries'
    )
    type = models.CharField(
        max_length=50,
        choices=LEADERBOARD_TYPES,
        db_column='type',  # Remove db_column override
        help_text="Type of leaderboard this entry belongs to"
    )
    total_points = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    last_update = models.DateTimeField(auto_now=True)  # ADD THIS FIELD
    
    # For graduation leaderboard - store graduation date
    graduation_date = models.DateTimeField(null=True, blank=True)  # ADD THIS FIELD
    
    class Meta:
        ordering = ['-total_points', 'user__name']
        verbose_name_plural = 'Leaderboard entries'
        unique_together = ['user', 'type']
```

#### 1.2 Leaderboard Type Rules - COMPLETE REWRITE
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

FIX: do this and use .keys when using a list of types:
```

LEADERBOARD_TYPES = {
    'validator': {
        'participants': lambda user: has_contribution_badge(user, 'validator'),
        'points_calculator': lambda...
```

TYPES_RULES = {
    'validator': lambda user: has_contribution_badge(user, 'validator'),
    'builder': lambda user: has_category_contributions(user, 'builder'),
    'validator-waitlist': lambda user: (
        has_contribution_badge(user, 'validator-waitlist') and 
        not has_contribution_badge(user, 'validator')
    ),
    'validator-waitlist-graduation': lambda user: (
        has_contribution_badge(user, 'validator-waitlist') and
        has_contribution_badge(user, 'validator')
    )
}

# Point calculation functions for each leaderboard type
POINT_CALCULATORS = {
    'validator': lambda user: calculate_category_points(user, 'validator'),
    'builder': lambda user: calculate_category_points(user, 'builder'),
    'validator-waitlist': lambda user: calculate_waitlist_points(user),
    'validator-waitlist-graduation': lambda user: None  # Points frozen at graduation
}

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
```

#### 1.3 Updated Signal Handlers - COMPLETE REWRITE
```python
@receiver(post_save, sender=Contribution)
def update_leaderboard_on_contribution(sender, instance, created, **kwargs):
    """
    When a contribution is saved, update all affected leaderboard entries.
    """
    # Call the plural version
    update_user_leaderboard_entries(instance.user)

def update_user_leaderboard_entries(user):
    """
    Core function that manages all of a user's leaderboard placements.
    Handles graduation, point calculations, and rank updates.
    """
    from contributions.models import Contribution
    from django.utils import timezone
    
    # Step 1: Determine which leaderboards user qualifies for
    qualified_leaderboards = []
    for leaderboard_type, rule_func in TYPES_RULES.items():
        if rule_func(user):
            qualified_leaderboards.append(leaderboard_type)
    
    FIX: Do this in the calculate points function of the types, don't special case graduation.
    # Step 2: Handle graduation case FIRST
    if 'validator-waitlist-graduation' in qualified_leaderboards:
        grad_entry = LeaderboardEntry.objects.filter(
            user=user,
            type='validator-waitlist-graduation'
        ).first()
        
        if not grad_entry:
            # New graduation! Freeze points from waitlist
            waitlist_points = calculate_waitlist_points(user)
            
            # Get graduation date from validator contribution
            grad_contrib = Contribution.objects.filter(
                user=user,
                contribution_type__slug='validator'
            ).order_by('contribution_date').first()
            
            LeaderboardEntry.objects.create(
                user=user,
                type='validator-waitlist-graduation',
                total_points=waitlist_points,
                graduation_date=grad_contrib.contribution_date if grad_contrib else timezone.now()
            )
    
    # Step 3: Remove from leaderboards user no longer qualifies for
    LeaderboardEntry.objects.filter(user=user).exclude(
        type__in=qualified_leaderboards
    ).delete()
    FIX: we need to keep track which where deleted to update the ranks
    
    # Step 4: Update or create entries for each qualified leaderboard
    for leaderboard_type in qualified_leaderboards:
        if leaderboard_type == 'validator-waitlist-graduation': FIX: the points_calculation will return no changes, so don't special case it
            # Skip - points are frozen
            continue
        
        # Calculate points for this leaderboard type
        calculator = POINT_CALCULATORS.get(leaderboard_type)
        if calculator:
            points = calculator(user)
            
            LeaderboardEntry.objects.update_or_create(
                user=user,
                type=leaderboard_type,
                defaults={'total_points': points}
            )
    
    # Step 5: Update ranks for affected leaderboard types
    for leaderboard_type in qualified_leaderboards:
        update_leaderboard_type_ranks(leaderboard_type)
    
    # Also update waitlist ranks if user graduated (they were removed) FIX: with the fix above this is not necesarry
    if 'validator-waitlist-graduation' in qualified_leaderboards:
        update_leaderboard_type_ranks('validator-waitlist')

def update_leaderboard_type_ranks(leaderboard_type):
    """
    Update ranks for a specific leaderboard type.
    Graduation leaderboard is ranked by date, others by points.
    """
    if leaderboard_type == 'validator-waitlist-graduation':
        # Rank by graduation date (most recent first)
        entries = LeaderboardEntry.objects.filter(
            type=leaderboard_type,
            user__visible=True
        ).order_by('-graduation_date', 'user__name')
    else:
        # Rank by points (highest first)
        entries = LeaderboardEntry.objects.filter(
            type=leaderboard_type,
            user__visible=True
        ).order_by('-total_points', 'user__name')
    
    # Bulk update ranks
    for i, entry in enumerate(entries, 1):
        entry.rank = i
    
    # Use bulk_update for efficiency
    LeaderboardEntry.objects.bulk_update(entries, ['rank'])
    
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
        for leaderboard_type, _ in LeaderboardEntry.LEADERBOARD_TYPES:
            update_leaderboard_type_ranks(leaderboard_type)
        
        return f"Recalculated {users.count()} users across all leaderboards"
```

### 2. Validator Model Changes (`backend/validators/models.py`)

#### 2.1 Remove Graduation Points Field
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
    
    # REMOVE: points_at_waitlist_graduation field
    # This is now handled by the graduation leaderboard
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
```

### 3. API Views Updates (`backend/leaderboard/views.py`)

#### 3.1 LeaderboardViewSet - REQUIRED CHANGES
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
    ordering_fields = ['rank', 'total_points', 'updated_at']
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
```

### 4. Contribution Highlights Update (`backend/contributions/views.py`)

#### 4.1 Waitlist Highlights with Graduation Filtering
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

#### 5.1 New Migration for Leaderboard Changes
```python
# backend/leaderboard/migrations/0013_add_graduation_leaderboard.py

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
        
        # Update choices to include graduation
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
                ],
                db_column='type'
            ),
        ),
        
        # Remove deprecated fields
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

#### 1.1 Progressive Loading Implementation
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
    // Load all sections in parallel
    Promise.all([
      fetchStatistics(),
      fetchWaitlistUsers(),
      fetchGraduatedUsers(),
      fetchFeaturedContributions()
    ]);
  });
  
  async function fetchStatistics() {
    try {
      const response = await leaderboardAPI.getWaitlistStats();
      statistics = response.data;
    } catch (error) {
      console.error('Failed to load statistics:', error);
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
    } finally {
      sectionsLoading.waitlist = false;
    }
  }
  
  async function fetchGraduatedUsers() {
    try {
      const response = await leaderboardAPI.getLeaderboardByType(
        'validator-waitlist-graduation',
        'desc'  // Most recent graduations first
      );
      graduatedUsers = response.data || [];
    } catch (error) {
      console.error('Failed to load graduated users:', error);
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
    } finally {
      sectionsLoading.featured = false;
    }
  }
</script>

<!-- Progressive rendering with skeleton loaders -->
<div class="space-y-6">
  <!-- Stats Section -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    {#if sectionsLoading.stats}
      <!-- Skeleton loaders -->
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
        color="amber"
      />
      <StatCard 
        title="Total Graduated" 
        value={statistics.total_graduated || 0}
        color="green"
      />
      <StatCard 
        title="Total Points" 
        value={statistics.total_points || 0}
        color="purple"
      />
    {/if}
  </div>
  
  <!-- Continue with other sections using similar pattern -->
</div>
```

### 2. API Integration Updates (`frontend/src/lib/api.js`)

#### 2.1 Updated Leaderboard API
```javascript
export const leaderboardAPI = {
  // Get specific leaderboard type with optional ordering
  getLeaderboardByType: (type, order = 'asc') => 
    api.get('/leaderboard/', { params: { type, order } }),
  
  // Get waitlist statistics
  getWaitlistStats: () => 
    api.get('/leaderboard/validator-waitlist-stats/'),
  
  // Main leaderboard function (no legacy category support)
  getLeaderboard: (params) => 
    api.get('/leaderboard/', { params }),
  
  // Admin recalculation
  recalculateAll: () => 
    api.post('/leaderboard/recalculate/')
};
```

## Performance Optimizations

### 1. Query Optimization Strategy

#### 1.1 Prefetch Pattern for Rules Evaluation
```python
def evaluate_user_leaderboards_batch(users):
    """
    Evaluate leaderboard memberships for multiple users efficiently.
    """
    from contributions.models import Contribution
    
    # Prefetch all contributions for all users in one query
    user_contributions = {}
    contributions = Contribution.objects.filter(
        user__in=users
    ).select_related(
        'contribution_type',
        'contribution_type__category'
    ).values(
        'user_id',
        'contribution_type__slug',
        'contribution_type__category__slug',
        'frozen_global_points',
        'contribution_date'
    )
    
    # Group by user
    for contrib in contributions:
        user_id = contrib['user_id']
        if user_id not in user_contributions:
            user_contributions[user_id] = []
        user_contributions[user_id].append(contrib)
    
    # Evaluate rules for each user using cached data
    results = {}
    for user in users:
        user_data = user_contributions.get(user.id, [])
        results[user.id] = evaluate_rules_with_cache(user, user_data)
    
    return results
```

#### 1.2 Bulk Rank Updates
```python
def bulk_update_ranks(leaderboard_type):
    """
    Efficiently update ranks using bulk operations.
    """
    from django.db import connection
    
    # Use raw SQL for maximum efficiency
    with connection.cursor() as cursor:
        if leaderboard_type == 'validator-waitlist-graduation':
            order_by = 'graduation_date DESC'
        else:
            order_by = 'total_points DESC'
        
        cursor.execute(f"""
            UPDATE leaderboard_leaderboardentry
            SET rank = subquery.new_rank
            FROM (
                SELECT 
                    id,
                    ROW_NUMBER() OVER (ORDER BY {order_by}, user_id) as new_rank
                FROM leaderboard_leaderboardentry
                WHERE type = %s
                AND user_id IN (
                    SELECT id FROM users_user WHERE visible = true
                )
            ) as subquery
            WHERE leaderboard_leaderboardentry.id = subquery.id
        """, [leaderboard_type])
```

### 2. N+1 Query Prevention

#### 2.1 Backend N+1 Solutions
```python
# Problem areas and solutions:

# 1. TYPES_RULES evaluation
# Solution: Batch prefetch contributions before evaluation
users = User.objects.prefetch_related(
    'contributions__contribution_type__category'
)

# 2. Point calculations
# Solution: Single aggregated query per user
from django.db.models import Sum, Q, Case, When

points_by_category = Contribution.objects.filter(
    user=user
).values(
    'contribution_type__category__slug'
).annotate(
    total=Sum('frozen_global_points')
)

# 3. Rank updates
# Solution: Use bulk_update or raw SQL
LeaderboardEntry.objects.bulk_update(entries, ['rank'], batch_size=1000)
```

#### 2.2 Frontend N+1 Solutions
```javascript
// Problem: Enriching user data
// Solution: Batch fetch and create lookup map

async function enrichUserData(leaderboardEntries) {
  // Get all unique user IDs
  const userIds = [...new Set(leaderboardEntries.map(e => e.user_id))];
  
  // Batch fetch user details
  const userResponse = await usersAPI.getUsers({ 
    ids: userIds.join(',') 
  });
  
  // Create lookup map
  const userMap = new Map(
    userResponse.data.map(user => [user.id, user])
  );
  
  // Enrich entries
  return leaderboardEntries.map(entry => ({
    ...entry,
    user: userMap.get(entry.user_id) || entry.user_details
  }));
}
```

## Testing Suite

### 1. Core Test Cases
```python
# backend/leaderboard/tests/test_graduation.py

from django.test import TestCase
from django.utils import timezone
from users.models import User
from contributions.models import Contribution, ContributionType
from leaderboard.models import LeaderboardEntry, update_user_leaderboard_entries

class GraduationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create(email='test@example.com')
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
    
    def test_graduation_flow(self):
        """Test complete graduation flow from waitlist to validator"""
        # Add to waitlist
        Contribution.objects.create(
            user=self.user,
            contribution_type=self.waitlist_type,
            points=10,
            frozen_global_points=10
        )
        
        # Should be on waitlist
        self.assertTrue(
            LeaderboardEntry.objects.filter(
                user=self.user,
                type='validator-waitlist'
            ).exists()
        )
        
        # Graduate to validator
        Contribution.objects.create(
            user=self.user,
            contribution_type=self.validator_type,
            points=5,
            frozen_global_points=5
        )
        
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
        self.assertEqual(grad_entry.total_points, 10)  # Frozen points
    
    def test_recalculation(self):
        """Test admin recalculation function"""
        from leaderboard.models import recalculate_all_leaderboards
        
        # Create test data
        for i in range(5):
            user = User.objects.create(email=f'user{i}@test.com')
            Contribution.objects.create(
                user=user,
                contribution_type=self.waitlist_type,
                points=10 * (i + 1),
                frozen_global_points=10 * (i + 1)
            )
        
        # Recalculate
        result = recalculate_all_leaderboards()
        
        # Verify all entries created with correct ranks
        entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist'
        ).order_by('rank')
        
        self.assertEqual(entries.count(), 5)
        for i, entry in enumerate(entries):
            self.assertEqual(entry.rank, i + 1)
```

## Summary of Key Changes

### What Was Fixed:
1. **Proper Leaderboard Types**: Added graduation leaderboard with frozen points
2. **Correct Point Calculations**: Each leaderboard calculates points from specific categories
3. **Graduation Handling**: Points frozen at graduation, proper state transitions
4. **Performance Optimizations**: Bulk operations, prefetching, N+1 query prevention
5. **Progressive Loading**: Frontend loads sections independently
6. **Admin Recalculation**: Complete rebuild function for data consistency
7. **Proper Testing**: Comprehensive test cases for graduation flow

### What Was Removed:
1. Deprecated category field
2. `points_at_waitlist_graduation` from Validator model
3. Legacy category parameter support
4. `recently_graduated` special endpoint (now uses graduation leaderboard)
5. Unnecessary future features (real-time updates, Redis caching, etc.)

### Database Changes Required:
1. Add `last_update` field to LeaderboardEntry
2. Add `graduation_date` field to LeaderboardEntry
3. Add 'validator-waitlist-graduation' to type choices
4. Remove category field from LeaderboardEntry
5. Remove `points_at_waitlist_graduation` from Validator

This implementation provides a clean, efficient, and maintainable validator journey system with proper state management and performance optimizations.
