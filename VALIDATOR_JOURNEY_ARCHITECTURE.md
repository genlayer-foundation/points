# Validator Journey Architecture Documentation

## Overview
The Validator Journey feature implements a multi-tiered leaderboard system that tracks users' progression from waitlist to active validator status. This document provides a detailed technical breakdown of how the system works at the model, view, and function level.

## Core Concept
The system replaces the previous category-based leaderboard with a type-based system that determines user placement based on their badges and profiles rather than contribution categories.

## Backend Architecture

### 1. Data Models (`backend/leaderboard/models.py`)

#### 1.1 LeaderboardEntry Model
**Purpose**: Represents a user's position on a specific leaderboard type.

**Key Fields**:
- `user`: ForeignKey to User model
- `type`: CharField with choices ['validator', 'builder', 'validator-waitlist']
  - Database column: `leaderboard_type` (preserved for backwards compatibility)  FIX: remove it
- `total_points`: PositiveIntegerField - sum of user's frozen global points
- `rank`: PositiveIntegerField - user's position on the leaderboard
FIX: - `last-update`: date

**Key Methods**:
- `update_points_without_ranking()`: Updates user's total points without recalculating ranks
- `determine_user_leaderboards(user)`: Class method that determines which leaderboards a user belongs to
- `update_leaderboard_ranks(leaderboard_type)`: Class method that recalculates ranks for a specific leaderboard

**Unique Constraint**: `(user, type)` - ensures one entry per user per leaderboard type

#### 1.2 Leaderboard Type Rules (`TYPES_RULES` dictionary)
**Location**: Top of `leaderboard/models.py`

**Structure**: Dictionary mapping leaderboard types to lambda functions that determine membership.

```python
TYPES_RULES = {
    'validator': lambda user: (
        # Has validator badge OR is in Validator model  FIX: only has validator badge
        Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator'
        ).exists() or 
        hasattr(user, 'validator_profile')
    ),
    'builder': lambda user: (
        # Has builder profile
        hasattr(user, 'builder_profile') FIX: has builder contribution
    ),
    'validator-waitlist': lambda user: (
        # Has validator-waitlist badge but NOT validator badge/profile FIX: only badge
        Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator-waitlist'
        ).exists() and 
        not Contribution.objects.filter(
            user=user,
            contribution_type__slug='validator'
        ).exists() and
        not hasattr(user, 'validator_profile') FIX: remove this last check
    ),
FIX: add an extra one: validator-waitlist-graduation
     when it has both validator-waitlist and validator, points are fixed at the moment of graduation
}
```

**Logic Flow**:
1. Each rule is a lambda function that takes a user object
2. Returns boolean indicating if user belongs to that leaderboard
3. Validator-waitlist specifically excludes users who have graduated to validator FIX: this is OK, when a validator graduates it should be included in validator-waitlist-graduation and removed from validator-waitlist

#### 1.3 Validator Model (`backend/validators/models.py`)
**Enhanced Fields**:
- `points_at_waitlist_graduation`: IntegerField - captures user's points when graduating from waitlist FIX: remove, we have it from the leaderboard
- `node_version`: CharField - inherited from NodeVersionMixin

**Graduation Tracking**:
- When a Validator object is created, system can optionally record the user's current points FIX: when assigning validator contributionFIX: wwen assigning validator rcntributionFIX: when assigning validator rcntribution
- Used for "Recently Graduated" feature to show progression FIX: we now have a leaderbaord for this

### 2. Signal Handlers (`backend/leaderboard/models.py`)

#### 2.1 `update_leaderboard_on_contribution` Signal
**Trigger**: `post_save` on Contribution model
**Location**: Lines 216-233

**Function Flow**:
1. Triggered when any contribution is saved
2. Calls `update_user_leaderboard_entry(user)` FIX: it's plural now
3. Logs point calculations for debugging

#### 2.2 `update_user_leaderboard_entry` Function
**Location**: Lines 235-268
**Purpose**: Core function that manages user's leaderboard placements

**Algorithm**:
```python
def update_user_leaderboard_entry(user):
    # Step 1: Calculate total points once
    total_points = sum(Contribution.objects.filter(user=user).values_list('frozen_global_points', flat=True))
    
    # Step 2: Determine eligible leaderboards using TYPES_RULES
    user_leaderboards = LeaderboardEntry.determine_user_leaderboards(user)
    
    # Step 3: Remove from ineligible leaderboards
    LeaderboardEntry.objects.filter(user=user).exclude(
        type__in=user_leaderboards
    ).delete()
    
    # Step 4: Update or create entries for eligible leaderboards
    for leaderboard_type in user_leaderboards:
        LeaderboardEntry.objects.update_or_create(
            user=user,
            type=leaderboard_type,
            defaults={'total_points': total_points}
        )
    
    # Step 5: Recalculate ranks for affected leaderboards
    for leaderboard_type in user_leaderboards:
        LeaderboardEntry.update_leaderboard_ranks(leaderboard_type)
    
    # Step 6: Handle graduation case
    if 'validator' in user_leaderboards:
        LeaderboardEntry.update_leaderboard_ranks('validator-waitlist')
```FIX: this is wrong. each leaderboard type should have a function to update points that get's a contribution and another for calculating the rank, most are based on points, graduation is based on date.

**Key Points**:
- User appears on ALL leaderboards they qualify for
- Same total points used across all leaderboards FIX: THIS IS WRONG. each leaderboard has it's amount of points
- Automatic removal from waitlist when graduating to validator
- Rank recalculation is deferred to avoid performance issues

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
    
    # Legacy support for 'category' param FIX: remove this
    category_slug = self.request.query_params.get('category')
    if category_slug and not leaderboard_type:
        # Map category to type for backwards compatibility
        ...
    
    return queryset.order_by('rank') FIX: allow to other by -rank or rank decending
```

##### `validator_waitlist_stats()` Action (Lines 249-291)
**Endpoint**: `/api/v1/leaderboard/validator-waitlist-stats/`
**Purpose**: Provides statistics for waitlist dashboard

**Returns**:
```python
{
    'total_participants': count of waitlist users,
    'total_contributions': sum of contributions from waitlist users, FIX: add another with the amount of graduated contributions in total
    'total_points': sum of points from waitlist users, FIX: same, count amount of points for gradiation
    'total_graduated': count of users who graduated,
    'graduation_rate': percentage of users who graduated, FIX: remove this
    'active_validators': total validator count FIX: remove this
}
```

##### `recently_graduated()` Action (Lines 293-335)
**Endpoint**: `/api/v1/leaderboard/recently-graduated/`
**Purpose**: Shows users who recently moved from waitlist to validator

**Algorithm**: FIX: we now use leaderbaord graduation type, we don't need a special function, remove this
1. Query validators with `points_at_waitlist_graduation` not null
2. Get current points from validator leaderboard
3. Calculate points gained since graduation
4. Return top 10 most recent graduates

**Response Structure**:
```python
{
    'user': {
        'id': user_id,
        'name': user_name,
        'address': wallet_address
    },
    'graduated_date': timestamp,
    'points_at_graduation': points when graduated,
    'current_points': current total points,
    'points_gained_since': difference,
    'days_since_graduation': days elapsed
}
```

### 4. Contribution System Integration

#### 4.1 Contribution Highlights (`backend/contributions/views.py`)
**Modified Method**: `highlights()` action (Lines 302-350)

**New Parameter**: `waitlist_only=true`
- Filters highlights to only show contributions from waitlist users
- Excludes users who have graduated to validator status FIX: keep them, but only contribution from before graduation for each, fix the implentation

**Implementation**:
```python
if waitlist_only:
    # Get users with validator-waitlist contribution
    waitlist_type = ContributionType.objects.filter(slug='validator-waitlist').first()
    waitlist_users = Contribution.objects.filter(
        contribution_type=waitlist_type
    ).values_list('user_id', flat=True).distinct()
    
    # Exclude users who are validators
    validator_users = Validator.objects.values_list('user_id', flat=True).distinct()
    waitlist_only_users = set(waitlist_users) - set(validator_users)
    
    # Filter highlights
    queryset = queryset.filter(contribution__user_id__in=waitlist_only_users)
```

## Frontend Architecture

### 1. Waitlist Route (`frontend/src/routes/Waitlist.svelte`) FIX all this based on backened changes

#### 1.1 State Management
**Key State Variables**:
```javascript
let waitlistUsers = $state([]);      // All waitlist participants
let newestWaitlistUsers = $state([]); // 5 most recent joiners
let recentlyGraduated = $state([]);   // Recently graduated validators
let featuredContributions = $state([]); // Highlighted contributions
let statistics = $state({});          // Waitlist statistics
```

#### 1.2 Data Fetching Functions FIX: show the base with loaders and fill each section as they arrive

##### `fetchWaitlistData()` (Lines 51-140)
**Purpose**: Main data loading function

**Process**:
1. Fetches waitlist leaderboard entries via `leaderboardAPI.getWaitlistOnly()`
2. Fetches statistics via `leaderboardAPI.getWaitlistStats()`
3. Fetches all users for enrichment
4. Fetches waitlist contributions for join dates
5. Enriches and combines data
6. Sorts by rank and extracts newest members

**Data Enrichment**:
```javascript
waitlistUsers = rawEntries.map(entry => {
    const userDetails = entry.user_details || {};
    const fullUser = allUsers.find(u => 
        u.address?.toLowerCase() === userDetails.address?.toLowerCase()
    );
    const waitlistContribution = findWaitlistContribution(userDetails);
    
    return {
        address: userDetails.address,
        isWaitlisted: true,
        user: fullUser || userDetails,
        score: entry.total_points,
        waitlistRank: entry.rank,
        nodeVersion: fullUser?.validator?.node_version,
        matchesTarget: fullUser?.validator?.matches_target,
        joinedWaitlist: waitlistContribution?.contribution_date
    };
});
```

##### `fetchRecentlyGraduated()` (Lines 142-156)
**Purpose**: Loads recently graduated validators
**API Call**: `leaderboardAPI.getRecentlyGraduated()`

##### `fetchFeaturedContributions()` (Lines 158-177)
**Purpose**: Loads highlighted contributions from waitlist users
**API Call**: `contributionsAPI.getHighlights({ waitlist_only: true, limit: 5 })`

#### 1.3 UI Components

**Layout Structure**:
1. **Stats Cards** (Lines 204-223): Three cards showing participants, contributions, points
2. **Race to Testnet** (Lines 228-283): Top 10 waitlist participants by rank
3. **Recently Graduated** (Lines 286-340): Users who graduated to validator
4. **Featured Contributions** (Lines 346-386): Highlighted waitlist contributions
5. **Newest Participants** (Lines 390-439): 5 most recent waitlist joiners
6. **Full Waitlist Table** (Lines 443-584): Complete participant list with details

### 2. API Integration (`frontend/src/lib/api.js`)

#### 2.1 Leaderboard API Extensions
**New Endpoints**:
```javascript
leaderboardAPI = {
    // Get waitlist-only leaderboard
    getWaitlistOnly: () => api.get('/leaderboard/', { params: { type: 'validator-waitlist' } }),
    
    // Get waitlist statistics
    getWaitlistStats: () => api.get('/leaderboard/validator-waitlist-stats/'),
    
    // Get recently graduated validators
    getRecentlyGraduated: () => api.get('/leaderboard/recently-graduated/'),
    
    // Legacy support with type mapping
    getLeaderboard: (params) => {
        if (params && params.category) {
            params.type = params.category;
            delete params.category;
        }
        return api.get('/leaderboard/', { params });
    }
}
```

## Data Flow Scenarios

### Scenario 1: User Joins Waitlist
1. User receives 'validator-waitlist' contribution/badge
2. `update_leaderboard_on_contribution` signal fires
3. `update_user_leaderboard_entry` called:
   - Determines user qualifies for 'validator-waitlist' leaderboard
   - Creates LeaderboardEntry with type='validator-waitlist'
   - Recalculates waitlist ranks
4. User appears on waitlist page

### Scenario 2: User Graduates to Validator
1. Validator profile created for user OR user receives 'validator' badge
2. Signal fires, `update_user_leaderboard_entry` called:
   - TYPES_RULES['validator'] returns True
   - TYPES_RULES['validator-waitlist'] returns False (excluded by rules)
   - Creates/updates validator leaderboard entry
   - Deletes waitlist leaderboard entry
   - Recalculates both leaderboard ranks
3. Optional: `points_at_waitlist_graduation` recorded on Validator model
4. User appears in "Recently Graduated" section
5. User removed from waitlist, appears on validator leaderboard

### Scenario 3: Points Update
1. User earns new contribution
2. Signal recalculates total points
3. All user's leaderboard entries updated with new total
4. Ranks recalculated for affected leaderboards
5. User maintains position on all qualified leaderboards

FIX: add scenario of recalculating everything. There;s a script that get's called from the admin (shortcut).

## Database Migrations

### Migration Strategy (0010-0012)
1. **0010_add_leaderboard_type.py**: Adds `leaderboard_type` field
2. **0011_migrate_to_leaderboard_types.py**: Data migration (not shown)
3. **0012_finalize_leaderboard_types.py**: Cleanup and constraints

**Key Changes**:
- Added `leaderboard_type` field with choices
- Maintained `category` field temporarily for backwards compatibility
- Changed unique constraint from `(user, category)` to `(user, leaderboard_type)`
- Category field marked as deprecated

## Performance Considerations

### Optimizations
1. **Batch Operations**: Ranks updated in bulk after all entries modified
2. **Deferred Ranking**: `update_points_without_ranking()` for batch updates
3. **Query Optimization**: Select_related and prefetch_related used extensively
4. **Caching**: Points calculated once and reused across leaderboards

### Potential Issues
1. **N+1 Queries**: Rules checking can cause multiple queries per user  FIX: get a report of where this happens both in front and backend g: get a report of twere this happens both in front and backend g: get a report of twere this happens both in front and backend
2. **Rank Recalculation**: O(n log n) for each leaderboard type
3. **Signal Cascades**: Multiple contributions can trigger redundant updates

## Error Handling

### Known Edge Cases
1. **Simultaneous Badges**: User with both waitlist and validator badges FIX: each it's own points, builder from category builder, validator, from category validator, validator-waitinglist from category validator
   - Resolution: Validator takes precedence, removed from waitlist
2. **Missing Profiles**: User without any qualifying criteria
   - Resolution: No leaderboard entries created
3. **Points at Graduation**: Not always captured FIX: should always be OK
   - Resolution: Field is nullable, feature degrades gracefully

## Testing Recommendations

### Critical Test Cases
1. **Graduation Flow**: Verify user moves from waitlist to validator
2. **Points Consistency**: Same total across all leaderboards
3. **Rank Accuracy**: No gaps or duplicates in rankings
4. **Rule Evaluation**: TYPES_RULES correctly identify user types
5. **API Filtering**: Type parameter correctly filters results
6. **Frontend State**: Waitlist page correctly shows only waitlist users
FIX: add re calculate ranks function, test ti works fine in different scenarios

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
Validator.objects.create(
    user=user1,
    points_at_waitlist_graduation=user1.leaderboard_entries.first().total_points
)

# Verify leaderboard changes
assert not LeaderboardEntry.objects.filter(user=user1, type='validator-waitlist').exists()
assert LeaderboardEntry.objects.filter(user=user1, type='validator').exists()
```

## Configuration Requirements

### Backend Settings
- No special configuration required
- Uses existing Django settings
- Database must support JSON fields for future extensions

### Frontend Environment
- No new environment variables
- Uses existing VITE_API_URL

## Future Improvements

### Suggested Enhancements
1. **Real-time Updates**: WebSocket for live leaderboard changes FIX: NO
2. **Graduation Ceremony**: Special UI/animation for graduations FIX: NO
3. **Historical Tracking**: Store complete journey history FIX: NO
4. **Batch Graduations**: Admin tool for promoting multiple users FIX: NO
5. **Customizable Rules**: Admin-configurable qualification criteria FIX: NO
6. **Performance Metrics**: Track graduation velocity and success rates FIX: NO

### Technical Debt
1. **Category Field**: Remove deprecated category field after migration period
2. **Rule Functions**: Move to database-configurable rules FIX: NO
3. **Caching Layer**: Add Redis for leaderboard caching FIX: NO
4. **API Versioning**: Prepare for v2 with cleaner type-based design FIX: NO
