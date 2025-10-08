# Referral System Implementation

## Key Changes

### 1. Incremental Referral Points Updates
**File**: `backend/leaderboard/models.py:448-471`

When a referred user makes a contribution, referral points are updated incrementally (O(1)):
- Takes `contribution` parameter (not referrer)
- Adds 10% of contribution points to referrer's appropriate category
- No full recalculation on every contribution

### 2. Waitlist Ranking Formula
**File**: `backend/leaderboard/models.py:39-67` - `calculate_waitlist_points()`

**Current formula**: `contribution_points + referral_points`
- Sums validator contribution points + total referral points (builder + validator)
- **To modify formula**: Edit this function's return statement (line 67)

### 3. Admin Recalculation Commands

**Two separate methods** (not unified, but accessible from admin):

#### A. Recalculate Leaderboard Entries (includes referral points)
- **File**: `backend/leaderboard/models.py:517-550` - `recalculate_all_leaderboards()`
- **Admin**: Leaderboard Entries > Actions > "Recreate all leaderboards"
- **Order**: Deletes both ReferralPoints and LeaderboardEntry, then:
  1. Recalculates all ReferralPoints first
  2. Updates all LeaderboardEntry records (using fresh referral points)
  3. Updates ranks

#### B. Recalculate Referral Points Only
- **File**: `backend/leaderboard/admin.py:132-171`
- **Admin**: Referral Points > Actions > "Recalculate all referral points from scratch"
- **Command**: `python manage.py recalculate_referral_points [--dry-run]`
- **What it does**: Deletes and recalculates ReferralPoints only (doesn't touch LeaderboardEntry)

### 4. Referral Details in API
**Files**: `backend/users/serializers.py:446-515`, `backend/users/views.py:705-714`

- Added `referral_details` field to UserSerializer
- Queries contribution points directly from Contribution table (not LeaderboardEntry)
- Shows all referred users including those with 0 points

### 5. Frontend Referral Card Logic
**File**: `frontend/src/routes/Profile.svelte:1488-1621`

**Visibility**:
- Shows for users with roles (builder/validator/creator/steward)
- Hidden for welcome users (no role)

**Content based on referrals**:
- **Own profile, 0 referrals**: CTA only (no metrics)
- **Own profile, has referrals**: Metrics + ReferralSection + table
- **Other profile, any referrals**: Metrics only (+ table if >0)

### 6. Validator Entry Selection
**Files**: `backend/users/serializers.py:479-487`, `backend/users/views.py:705-714`

- Queries contributions directly (bypasses LeaderboardEntry)
- No longer relies on validator-waitlist-graduation logic
