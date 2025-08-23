# Validator Journey Architecture Documentation v2

## Overview
The Validator Journey feature implements a multi-tiered leaderboard system that tracks users' progression from waitlist to active validator status. This document provides a detailed technical breakdown of how the system works at the model, view, and function level.

## Core Concept
The system uses a type-based leaderboard system that determines user placement based on their contributions/badges. Each leaderboard type has its own point calculation and ranking system.

## Backend Architecture

### 1. Data Models (`backend/leaderboard/models.py`)

#### 1.1 LeaderboardEntry Model
**Purpose**: Represents a user's position on a specific leaderboard type.

**Key Fields**:
- `user`: ForeignKey to User model
- `type`: CharField with choices ['validator', 'builder', 'validator-waitlist', 'validator-waitlist-graduation']
- `total_points`: PositiveIntegerField - points specific to this leaderboard type
- `rank`: PositiveIntegerField - user's position on the leaderboard
- `last_update`: DateTimeField - timestamp of last update

**Key Methods**:
- `update_points_without_ranking()`: Updates user's total points without recalculating ranks
- `determine_user_leaderboards(user)`: Class method that determines which leaderboards a user belongs to
- `update_leaderboard_ranks(leaderboard_type)`: Class method that recalculates ranks for a specific leaderboard
- `update_points(contribution)`: Updates points based on contribution type
- `calculate_rank()`: Calculates rank based on leaderboard-specific logic

**Unique Constraint**: `(user, type)` - ensures one entry per user per leaderboard type

#### 1.2 Leaderboard Type Rules (`TYPES_RULES` dictionary)
**Location**: Top of `leaderboard/models.py`

**Structure**: Dictionary mapping leaderboard types to lambda functions that determine membership.

```python
TYPES_RULES = {
    'validator': lambda user: (
        # Has validator badge only
        Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator'
        ).exists()
    ),
    'builder': lambda user: (
        # Has builder contribution
        Contribution.objects.filter(
            user=user,
            contribution_type__category__slug='builder'
        ).exists()
    ),
    'validator-waitlist': lambda user: (
        # Has validator-waitlist badge but NOT validator badge
        Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator-waitlist'
        ).exists() and 
        not Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator'
        ).exists()
    ),
    'validator-waitlist-graduation': lambda user: (
        # Has both validator-waitlist and validator badges
        Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator-waitlist'
        ).exists() and
        Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator'
        ).exists()
    )
}
```

**Logic Flow**:
1. Each rule is a lambda function that takes a user object
2. Returns boolean indicating if user belongs to that leaderboard
3. Validator-waitlist excludes graduated users (they move to validator-waitlist-graduation)
4. Graduation leaderboard shows users with both badges

#### 1.3 Points Calculation
**Important**: Each leaderboard type has its own point calculation:
- `validator`: Points from validator category contributions
- `builder`: Points from builder category contributions  
- `validator-waitlist`: Points from validator category contributions (before graduation)
- `validator-waitlist-graduation`: Points frozen at graduation moment

#### 1.4 Validator Model (`backend/validators/models.py`)
**Fields**:
- `node_version`: CharField - inherited from NodeVersionMixin

**Graduation Tracking**:
- When validator contribution is assigned, system captures current waitlist points
- Points are frozen in validator-waitlist-graduation leaderboard entry

### 2. Signal Handlers (`backend/leaderboard/models.py`)

#### 2.1 `update_leaderboard_on_contribution` Signal
**Trigger**: `post_save` on Contribution model
**Location**: Lines 216-233

**Function Flow**:
1. Triggered when any contribution is saved
2. Calls `update_user_leaderboard_entries(user)` (plural)
3. Logs point calculations for debugging

#### 2.2 `update_user_leaderboard_entries` Function
**Location**: Lines 235-268
**Purpose**: Core function that manages user's leaderboard placements

**Algorithm**:
```python
def update_user_leaderboard_entries(user):
    # Step 1: Determine eligible leaderboards using TYPES_RULES
    user_leaderboards = LeaderboardEntry.determine_user_leaderboards(user)
    
    # Step 2: Remove from ineligible leaderboards
    LeaderboardEntry.objects.filter(user=user).exclude(
        type__in=user_leaderboards
    ).delete()
    
    # Step 3: Handle graduation case first
    if 'validator-waitlist-graduation' in user_leaderboards:
        # Check if graduation entry exists
        grad_entry = LeaderboardEntry.objects.filter(
            user=user, 
            type='validator-waitlist-graduation'
        ).first()
        
        if not grad_entry:
            # New graduation - freeze points from waitlist
            waitlist_entry = LeaderboardEntry.objects.filter(
                user=user,
                type='validator-waitlist'
            ).first()
            
            if waitlist_entry:
                LeaderboardEntry.objects.create(
                    user=user,
                    type='validator-waitlist-graduation',
                    total_points=waitlist_entry.total_points,
                    last_update=timezone.now()
                )
    
    # Step 4: Update points for each leaderboard type
    for leaderboard_type in user_leaderboards:
        if leaderboard_type == 'validator-waitlist-graduation':
            continue  # Points are frozen at graduation
            
        # Calculate points based on leaderboard type
        if leaderboard_type == 'validator':
            points = calculate_validator_points(user)
        elif leaderboard_type == 'builder':
            points = calculate_builder_points(user)
        elif leaderboard_type == 'validator-waitlist':
            points = calculate_waitlist_points(user)
        
        LeaderboardEntry.objects.update_or_create(
            user=user,
            type=leaderboard_type,
            defaults={
                'total_points': points,
                'last_update': timezone.now()
            }
        )
    
    # Step 5: Recalculate ranks for affected leaderboards
    for leaderboard_type in user_leaderboards:
        update_leaderboard_type_ranks(leaderboard_type)
```

**Helper Functions**:
```python
def calculate_validator_points(user):
    """Calculate points from validator category contributions"""
    return Contribution.objects.filter(
        user=user,
        contribution_type__category__slug='validator'
    ).aggregate(total=Sum('frozen_global_points'))['total'] or 0

def calculate_builder_points(user):
    """Calculate points from builder category contributions"""
    return Contribution.objects.filter(
        user=user,
        contribution_type__category__slug='builder'
    ).aggregate(total=Sum('frozen_global_points'))['total'] or 0

def calculate_waitlist_points(user):
    """Calculate points from validator category before graduation"""
    # Get graduation date if exists
    grad_contribution = Contribution.objects.filter(
        user=user,
        contribution_type__slug='validator'
    ).first()
    
    query = Contribution.objects.filter(
        user=user,
        contribution_type__category__slug='validator'
    )
    
    if grad_contribution:
        # Only count contributions before graduation
        query = query.filter(
            contribution_date__lt=grad_contribution.contribution_date
        )
    
    return query.aggregate(total=Sum('frozen_global_points'))['total'] or 0

def update_leaderboard_type_ranks(leaderboard_type):
    """Update ranks for a specific leaderboard type"""
    if leaderboard_type == 'validator-waitlist-graduation':
        # Rank by graduation date (most recent first)
        entries = LeaderboardEntry.objects.filter(
            type=leaderboard_type
        ).order_by('-last_update')
    else:
        # Rank by points
        entries = LeaderboardEntry.objects.filter(
            type=leaderboard_type
        ).order_by('-total_points', 'user__name')
    
    for i, entry in enumerate(entries):
        entry.rank = i + 1
        entry.save(update_fields=['rank'])
```

**Key Points**:
- User appears on ALL leaderboards they qualify for
- Each leaderboard has its own point calculation
- Graduation freezes points in graduation leaderboard
- Rank calculation varies by leaderboard type

### 3. API Views (`backend/leaderboard/views.py`)

#### 3.1 LeaderboardViewSet
**Location**: Lines 40-337
**Purpose**: Main API endpoint for leaderboard data

**Key Methods**:

##### `get_queryset()` (Lines 58-83)
**Function**: Filters leaderboard by type parameter
```python
def get_queryset(self):
    queryset = super().get_queryset()
    
    # Get type from query params
    leaderboard_type = self.request.query_params.get('type')
    
    if leaderboard_type:
        queryset = queryset.filter(type=leaderboard_type)
    else:
        # Default to validator leaderboard
        queryset = queryset.filter(type='validator')
    
    # Get ordering parameter
    order = self.request.query_params.get('order', 'asc')
    if order == 'desc':
        return queryset.order_by('-rank')
    return queryset.order_by('rank')
```

##### `validator_waitlist_stats()` Action (Lines 249-291)
**Endpoint**: `/api/v1/leaderboard/validator-waitlist-stats/`
**Purpose**: Provides statistics for waitlist dashboard

**Returns**:
```python
{
    'total_participants': count of waitlist users,
    'total_contributions': sum of contributions from waitlist users,
    'total_graduated_contributions': sum of contributions from graduated users,
    'total_points': sum of points from waitlist users,
    'total_graduated_points': sum of points in graduation leaderboard,
    'total_graduated': count of users who graduated
}
```

### 4. Contribution System Integration

#### 4.1 Contribution Highlights (`backend/contributions/views.py`)
**Modified Method**: `highlights()` action (Lines 302-350)

**New Parameter**: `waitlist_only=true`
- Shows contributions from waitlist users
- For graduated users, only shows contributions from before graduation

**Implementation**:
```python
if waitlist_only:
    # Get users with validator-waitlist contribution
    waitlist_type = ContributionType.objects.filter(slug='validator-waitlist').first()
    waitlist_users = Contribution.objects.filter(
        contribution_type=waitlist_type
    ).values_list('user_id', flat=True).distinct()
    
    # Get graduated users and their graduation dates
    graduated_users = {}
    validator_contributions = Contribution.objects.filter(
        contribution_type__slug='validator',
        user_id__in=waitlist_users
    ).select_related('user')
    
    for vc in validator_contributions:
        graduated_users[vc.user_id] = vc.contribution_date
    
    # Build query for highlights
    q_objects = Q()
    for user_id in waitlist_users:
        if user_id in graduated_users:
            # Graduated user - only show pre-graduation contributions
            q_objects |= Q(
                contribution__user_id=user_id,
                contribution__contribution_date__lt=graduated_users[user_id]
            )
        else:
            # Still on waitlist - show all contributions
            q_objects |= Q(contribution__user_id=user_id)
    
    queryset = queryset.filter(q_objects)
```

### 5. Admin Recalculation Script

**Purpose**: Recalculate all leaderboard entries and ranks

```python
def recalculate_all_leaderboards():
    """
    Admin command to recalculate all leaderboard entries.
    Called from admin shortcuts.
    """
    from django.db import transaction
    
    with transaction.atomic():
        # Step 1: Clear all existing entries
        LeaderboardEntry.objects.all().delete()
        
        # Step 2: Process each user
        users = User.objects.filter(
            contributions__isnull=False
        ).distinct()
        
        for user in users:
            update_user_leaderboard_entries(user)
        
        # Step 3: Update ranks for each leaderboard type
        for leaderboard_type in ['validator', 'builder', 'validator-waitlist', 'validator-waitlist-graduation']:
            update_leaderboard_type_ranks(leaderboard_type)
        
        print(f"Recalculated {users.count()} users across all leaderboards")
```

## Frontend Architecture

### 1. Waitlist Route (`frontend/src/routes/Waitlist.svelte`)

#### 1.1 State Management with Progressive Loading
**Key State Variables**:
```javascript
let waitlistUsers = $state([]);      // All waitlist participants
let newestWaitlistUsers = $state([]); // 5 most recent joiners
let graduatedUsers = $state([]);      // Graduated validators (from graduation leaderboard)
let featuredContributions = $state([]); // Highlighted contributions
let statistics = $state({});          // Waitlist statistics

// Loading states for progressive rendering
let statsLoading = $state(true);
let waitlistLoading = $state(true);
let graduatedLoading = $state(true);
let featuredLoading = $state(true);
```

#### 1.2 Progressive Loading Pattern
```javascript
onMount(async () => {
    // Load sections independently for better UX
    fetchStatistics();      // Fast - loads first
    fetchWaitlistData();    // Main data
    fetchGraduatedUsers();  // Secondary data
    fetchFeaturedContributions(); // Enhancement data
});
```

#### 1.3 Data Fetching Functions

##### `fetchWaitlistData()`
**Purpose**: Load waitlist participants
```javascript
async function fetchWaitlistData() {
    waitlistLoading = true;
    const response = await leaderboardAPI.getLeaderboardByType('validator-waitlist');
    waitlistUsers = response.data;
    
    // Extract newest joiners
    newestWaitlistUsers = [...waitlistUsers]
        .sort((a, b) => new Date(b.last_update) - new Date(a.last_update))
        .slice(0, 5);
    
    waitlistLoading = false;
}
```

##### `fetchGraduatedUsers()`
**Purpose**: Load graduated validators from graduation leaderboard
```javascript
async function fetchGraduatedUsers() {
    graduatedLoading = true;
    const response = await leaderboardAPI.getLeaderboardByType('validator-waitlist-graduation');
    graduatedUsers = response.data;
    graduatedLoading = false;
}
```

### 2. API Integration (`frontend/src/lib/api.js`)

#### 2.1 Leaderboard API
```javascript
leaderboardAPI = {
    // Get specific leaderboard type
    getLeaderboardByType: (type, order = 'asc') => 
        api.get('/leaderboard/', { params: { type, order } }),
    
    // Get waitlist statistics
    getWaitlistStats: () => 
        api.get('/leaderboard/validator-waitlist-stats/'),
    
    // Main leaderboard function
    getLeaderboard: (params) => {
        return api.get('/leaderboard/', { params });
    }
}
```

## Data Flow Scenarios

### Scenario 1: User Joins Waitlist
1. User receives 'validator-waitlist' contribution
2. `update_leaderboard_on_contribution` signal fires
3. `update_user_leaderboard_entries` called:
   - Determines user qualifies for 'validator-waitlist' leaderboard
   - Calculates points from validator category contributions
   - Creates LeaderboardEntry with type='validator-waitlist'
   - Recalculates waitlist ranks by points
4. User appears on waitlist page

### Scenario 2: User Graduates to Validator
1. User receives 'validator' contribution
2. Signal fires, `update_user_leaderboard_entries` called:
   - TYPES_RULES['validator'] returns True
   - TYPES_RULES['validator-waitlist-graduation'] returns True
   - TYPES_RULES['validator-waitlist'] returns False
   - Creates validator leaderboard entry with validator points
   - Creates graduation entry with frozen waitlist points
   - Deletes waitlist leaderboard entry
   - Recalculates ranks (points for validator, date for graduation)
3. User appears in graduation leaderboard sorted by graduation date
4. User removed from waitlist, appears on validator leaderboard

### Scenario 3: Points Update
1. User earns new contribution
2. Signal determines which leaderboards are affected
3. Points recalculated based on contribution category:
   - Validator contributions → validator and waitlist leaderboards
   - Builder contributions → builder leaderboard
4. Graduation leaderboard points remain frozen
5. Ranks recalculated for affected leaderboards

### Scenario 4: Admin Recalculation
1. Admin triggers recalculation from admin panel
2. `recalculate_all_leaderboards()` function called
3. All leaderboard entries deleted and rebuilt
4. Each user processed to determine leaderboard memberships
5. Points calculated per leaderboard type
6. Ranks recalculated for all leaderboards

## Performance Considerations

### Optimizations
1. **Batch Operations**: Ranks updated in bulk after all entries modified
2. **Deferred Ranking**: `update_points_without_ranking()` for batch updates
3. **Query Optimization**: Select_related and prefetch_related used extensively
4. **Separate Point Calculations**: Each leaderboard calculates its own points

### N+1 Query Analysis

**Backend Potential N+1 Issues**:
1. `TYPES_RULES` evaluation - Each rule may query contributions table
   - **Fix**: Prefetch all user contributions once, pass to rules
2. `update_user_leaderboard_entries` - Multiple point calculations
   - **Fix**: Single aggregated query for all contribution types
3. Rank calculation - Loading each entry separately
   - **Fix**: Use bulk_update for rank updates

**Frontend Potential N+1 Issues**:
1. User enrichment in waitlist data - Fetching each user separately
   - **Fix**: Batch fetch all users, create lookup map
2. Contribution fetching for dates - Individual queries per user
   - **Fix**: Single query with user_id__in filter

### Potential Issues
1. **Rules Evaluation**: Multiple queries per user during rule checking
2. **Rank Recalculation**: O(n log n) for each leaderboard type
3. **Signal Cascades**: Multiple contributions can trigger redundant updates

## Error Handling

### Known Edge Cases
1. **Simultaneous Badges**: User with both waitlist and validator badges
   - Resolution: Appears in graduation leaderboard with frozen points
2. **Missing Profiles**: User without any qualifying criteria
   - Resolution: No leaderboard entries created
3. **Points at Graduation**: Always captured when validator badge assigned
   - Resolution: Frozen in graduation leaderboard entry

## Testing Recommendations

### Critical Test Cases
1. **Graduation Flow**: Verify user moves from waitlist to graduation leaderboard
2. **Points Consistency**: Different points per leaderboard type
3. **Rank Accuracy**: No gaps or duplicates in rankings
4. **Rule Evaluation**: TYPES_RULES correctly identify user types
5. **API Filtering**: Type parameter correctly filters results
6. **Frontend State**: Waitlist page shows waitlist and graduated users correctly
7. **Recalculation Function**: Test admin recalculation in various scenarios:
   - Empty database
   - Single user with multiple contributions
   - Multiple users with various badges
   - Users at different journey stages

### Test Data Setup
```python
# Create waitlist user
user1 = User.objects.create(email='waitlist@test.com')
Contribution.objects.create(
    user=user1,
    contribution_type=ContributionType.objects.get(slug='validator-waitlist'),
    points=10
)

# Graduate user to validator
validator_contrib = Contribution.objects.create(
    user=user1,
    contribution_type=ContributionType.objects.get(slug='validator'),
    points=5
)

# Verify leaderboard changes
assert not LeaderboardEntry.objects.filter(user=user1, type='validator-waitlist').exists()
assert LeaderboardEntry.objects.filter(user=user1, type='validator').exists()
assert LeaderboardEntry.objects.filter(user=user1, type='validator-waitlist-graduation').exists()

# Verify frozen points
grad_entry = LeaderboardEntry.objects.get(user=user1, type='validator-waitlist-graduation')
assert grad_entry.total_points == 10  # Frozen at graduation

# Test recalculation
from leaderboard.admin import recalculate_all_leaderboards
recalculate_all_leaderboards()
assert LeaderboardEntry.objects.filter(user=user1).count() == 2  # validator and graduation
```

## Configuration Requirements

### Backend Settings
- No special configuration required
- Uses existing Django settings

### Frontend Environment
- No new environment variables
- Uses existing VITE_API_URL

## Technical Debt

### Immediate Tasks
1. **Remove deprecated fields**: 
   - Remove `category` field from LeaderboardEntry
   - Remove database column preservation for `leaderboard_type`
   - Remove `points_at_waitlist_graduation` from Validator model

### Code Cleanup
1. **Remove legacy support**: Remove category parameter handling in views
2. **Consolidate point calculations**: Create centralized point calculation service
3. **Optimize queries**: Implement prefetch patterns to eliminate N+1 queries