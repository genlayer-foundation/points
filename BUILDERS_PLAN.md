# Multi-Category User System - Implementation Plan

## Architecture Decision

Using **Option 2: Separate Apps with Individual Profile Models**

Each category (Validator, Builder, Steward) has:
- Its own Django app
- Its own Profile model with OneToOne relationship to User
- Its own specific fields and logic

## Backend Structure

### Models

#### categories/models.py
```python
class Category(BaseModel):
    """Define a user category (Validator, Builder, Steward)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    profile_model = models.CharField(max_length=100)  # e.g., "validators.Validator"
```

#### validators/models.py
```python
class Validator(BaseModel):
    """Validator profile - OneToOne with User"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='validator')
    node_version = models.CharField(max_length=100, blank=True, null=True)
    # ... existing validator fields and logic ...
```

#### builders/models.py
```python
class Builder(BaseModel):
    """Builder profile - OneToOne with User"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='builder')
    github_username = models.CharField(max_length=100, blank=True)
    primary_language = models.CharField(max_length=50, blank=True)
    repositories_contributed = models.IntegerField(default=0)
    pull_requests_merged = models.IntegerField(default=0)
```

#### stewards/models.py
```python
class Steward(BaseModel):
    """Steward profile - OneToOne with User"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='steward')
    twitter_handle = models.CharField(max_length=100, blank=True)
    discord_handle = models.CharField(max_length=100, blank=True)
    events_organized = models.IntegerField(default=0)
    blog_posts_published = models.IntegerField(default=0)
    community_members_helped = models.IntegerField(default=0)
```

### User Model Updates
Common fields stay on the User model:
- email
- name
- address
- visible

### How Profiles Are Created
When a user makes their first contribution in a category:
1. Check if profile exists for that category
2. If not, create the profile automatically
3. User now has that profile (validator, builder, or steward)

A user can have all three profiles simultaneously.

## Frontend Transformation

### Current State
- Everything is built for validators only
- Views assume single user type
- Components are validator-specific

### Target State
- Same page shows all profiles a user has
- Hardcoded sections for each profile type
- Each section only shows if user has that profile

### Implementation Steps

#### 1. Profile Page Transformation

**Current** (single profile):
```svelte
<!-- routes/Profile.svelte -->
<div>
  <h1>Validator Profile</h1>
  <input bind:value={nodeVersion} />
</div>
```

**New** (multiple profiles):
```svelte
<!-- routes/Profile.svelte -->
<script>
  let user = {}; // From API
  let hasValidator = !!user.validator;
  let hasBuilder = !!user.builder;
  let hasSteward = !!user.steward;
</script>

<div class="profile-container">
  {#if hasValidator}
    <section class="validator-section">
      <h2>Validator Profile</h2>
      <div class="field">
        <label>Node Version</label>
        <input bind:value={user.validator.node_version} />
      </div>
    </section>
  {/if}
  
  {#if hasBuilder}
    <section class="builder-section">
      <h2>Builder Profile</h2>
      <div class="field">
        <label>GitHub Username</label>
        <input bind:value={user.builder.github_username} />
      </div>
      <div class="field">
        <label>Primary Language</label>
        <input bind:value={user.builder.primary_language} />
      </div>
    </section>
  {/if}
  
  {#if hasSteward}
    <section class="steward-section">
      <h2>Steward Profile</h2>
      <div class="field">
        <label>Twitter Handle</label>
        <input bind:value={user.steward.twitter_handle} />
      </div>
      <div class="field">
        <label>Discord Handle</label>
        <input bind:value={user.steward.discord_handle} />
      </div>
    </section>
  {/if}
  
  {#if !hasValidator && !hasBuilder && !hasSteward}
    <p>You don't have any profiles yet. Start contributing to join a category!</p>
  {/if}
</div>
```

#### 2. Leaderboard Page Transformation

**Current** (single leaderboard):
```svelte
<!-- routes/Leaderboard.svelte -->
<LeaderboardTable data={validatorLeaderboard} />
```

**New** (tabbed leaderboards):
```svelte
<!-- routes/Leaderboard.svelte -->
<script>
  let activeTab = 'validators';
</script>

<div class="tabs">
  <button class:active={activeTab === 'validators'} on:click={() => activeTab = 'validators'}>
    Validators
  </button>
  <button class:active={activeTab === 'builders'} on:click={() => activeTab = 'builders'}>
    Builders
  </button>
  <button class:active={activeTab === 'stewards'} on:click={() => activeTab = 'stewards'}>
    Stewards
  </button>
</div>

{#if activeTab === 'validators'}
  <ValidatorLeaderboard />
{:else if activeTab === 'builders'}
  <BuilderLeaderboard />
{:else if activeTab === 'stewards'}
  <StewardLeaderboard />
{/if}
```

#### 3. Dashboard Transformation

**New** (shows all user's categories):
```svelte
<!-- routes/Dashboard.svelte -->
<script>
  import { onMount } from 'svelte';
  
  let userProfiles = {};
  
  onMount(async () => {
    const response = await fetch('/api/v1/users/me/');
    const data = await response.json();
    userProfiles = {
      validator: data.validator,
      builder: data.builder,
      steward: data.steward
    };
  });
</script>

<div class="dashboard">
  <h1>My Dashboard</h1>
  
  <div class="profiles-grid">
    {#if userProfiles.validator}
      <div class="profile-card validator">
        <h2>Validator</h2>
        <p>Node: {userProfiles.validator.node_version}</p>
        <p>Points: {userProfiles.validator.total_points}</p>
        <p>Rank: #{userProfiles.validator.rank}</p>
      </div>
    {/if}
    
    {#if userProfiles.builder}
      <div class="profile-card builder">
        <h2>Builder</h2>
        <p>GitHub: {userProfiles.builder.github_username}</p>
        <p>Points: {userProfiles.builder.total_points}</p>
        <p>Rank: #{userProfiles.builder.rank}</p>
      </div>
    {/if}
    
    {#if userProfiles.steward}
      <div class="profile-card steward">
        <h2>Steward</h2>
        <p>Events: {userProfiles.steward.events_organized}</p>
        <p>Points: {userProfiles.steward.total_points}</p>
        <p>Rank: #{userProfiles.steward.rank}</p>
      </div>
    {/if}
  </div>
</div>
```

#### 4. API Response Structure

```json
// GET /api/v1/users/me/
{
  "id": 1,
  "email": "user@example.com",
  "name": "John Doe",
  "address": "0x...",
  "validator": {
    "node_version": "1.2.3",
    "total_points": 150,
    "rank": 5
  },
  "builder": {
    "github_username": "johndoe",
    "primary_language": "Python",
    "repositories_contributed": 3,
    "total_points": 200,
    "rank": 3
  },
  "steward": null  // User doesn't have steward profile
}
```

#### 5. Components to Create

Hardcoded components for each category:

```
components/
├── validators/
│   ├── ValidatorProfile.svelte
│   ├── ValidatorLeaderboard.svelte
│   └── ValidatorStats.svelte
├── builders/
│   ├── BuilderProfile.svelte
│   ├── BuilderLeaderboard.svelte
│   └── BuilderStats.svelte
└── stewards/
    ├── StewardProfile.svelte
    ├── StewardLeaderboard.svelte
    └── StewardStats.svelte
```

### CSS Organization

```css
/* Each category gets its own color theme */
.validator-section {
  --primary-color: #4CAF50;
  border-left: 4px solid var(--primary-color);
}

.builder-section {
  --primary-color: #2196F3;
  border-left: 4px solid var(--primary-color);
}

.steward-section {
  --primary-color: #FF9800;
  border-left: 4px solid var(--primary-color);
}
```

## API Endpoints

```
# User profiles
GET /api/v1/users/me/                    # Returns user with all profiles
GET /api/v1/users/{id}/                  # Returns user with all profiles

# Category-specific profile updates
PATCH /api/v1/validators/me/             # Update validator profile
PATCH /api/v1/builders/me/               # Update builder profile  
PATCH /api/v1/stewards/me/               # Update steward profile

# Leaderboards
GET /api/v1/leaderboard/validators/      # Validator leaderboard
GET /api/v1/leaderboard/builders/        # Builder leaderboard
GET /api/v1/leaderboard/stewards/        # Steward leaderboard

# Contributions
GET /api/v1/contributions/?category=validator
GET /api/v1/contributions/?category=builder
GET /api/v1/contributions/?category=steward
```

## Implementation Order

1. Create Django apps (validators, builders, stewards)
2. Move Validator model from users to validators app
3. Create Builder and Steward models
4. Update User serializer to include all profiles
5. Create separate API endpoints for each profile type
6. Update frontend Profile page to show all profiles
7. Create tabbed leaderboard view
8. Update dashboard to show all user's profiles
9. Create category-specific components

## Key Points

- **No UserRole model** - having a profile means you're in that category
- **Direct profile access** - `user.validator`, `user.builder`, `user.steward`
- **Hardcoded frontend** - explicit sections for each category
- **Profile duplication is intentional** - each profile is independent
- **Common fields stay on User** - only category-specific fields in profiles