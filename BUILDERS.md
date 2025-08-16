# Dynamic User Roles & Categories Feature Specification

## Overview
This document outlines the implementation of a dynamic user role system where users automatically gain roles/categories based on their contributions. These roles act as both user types and permissions, controlling field visibility and editability in user profiles.

## Core Concept
- **No fixed user types**: Users don't have a predefined type (validator, builder, etc.)
- **Dynamic role assignment**: Users gain roles by making contributions in specific categories
- **Roles as permissions**: Each role determines which profile fields are visible/editable
- **Multiple roles**: Users can have multiple roles simultaneously
- **Separate leaderboards**: Each category has its own competitive leaderboard

## App Structure

The feature introduces several new Django apps to maintain clean separation of concerns:

### New Apps
- **validators**: Contains Validator profile model (moved from users app)
- **builders**: Contains Builder profile model
- **stewards**: Contains Steward profile model

### Existing Apps Updates
- **contributions**: Add ContributionCategory model
- **users**: Add UserRole model, remove Validator model
- **leaderboard**: Add CategoryLeaderboard model

## Database Schema

### 1. ContributionCategory Model
```python
class ContributionCategory(BaseModel):
    """
    Defines a category/role like 'Validator', 'Builder', 'Ambassador', etc.
    Acts as both a grouping mechanism and a permission role.
    """
    name = models.CharField(max_length=100, unique=True)  # e.g., "Validator"
    slug = models.SlugField(unique=True)  # e.g., "validator"
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # For UI display
    order = models.IntegerField(default=0)  # Display order
    
    # Profile model configuration
    profile_model = models.CharField(max_length=100, blank=True)  # e.g., "users.Validator"
    
    # Permission fields - which profile fields this role can see/edit
    visible_fields = models.JSONField(default=list, blank=True)
    editable_fields = models.JSONField(default=list, blank=True)
```

### 2. Updated ContributionType Model
```python
class ContributionType(BaseModel):
    # Existing fields...
    category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.CASCADE,
        related_name='contribution_types'
    )
    # Remove any static 'applies_to' field
```

### 3. UserRole Model
```python
class UserRole(BaseModel):
    """
    Tracks which categories/roles a user has based on their contributions.
    Auto-calculated from contribution history.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    category = models.ForeignKey(ContributionCategory, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['user', 'category']
```

### 4. Category-Specific Profile Models in Separate Apps

Each category will have its own Django app with its profile model:

#### validators/models.py
```python
# Move existing Validator model from users/models.py to validators/models.py
from django.db import models
from django.conf import settings
from utils.models import BaseModel

class Validator(BaseModel):
    """
    Validator-specific profile fields.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='validator'
    )
    node_version = models.CharField(max_length=100, blank=True, null=True)
    # ... existing validator logic for version checking and auto-contributions ...
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
```

#### builders/models.py
```python
from django.db import models
from django.conf import settings
from utils.models import BaseModel

class Builder(BaseModel):
    """
    Builder-specific profile fields.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='builder'
    )
    github_username = models.CharField(max_length=100, blank=True)
    primary_language = models.CharField(max_length=50, blank=True)
    repositories_contributed = models.IntegerField(default=0)
    pull_requests_merged = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.email} - Builder"
```

#### stewards/models.py
```python
from django.db import models
from django.conf import settings
from utils.models import BaseModel

class Steward(BaseModel):
    """
    Steward-specific profile fields.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='steward'
    )
    twitter_handle = models.CharField(max_length=100, blank=True)
    discord_handle = models.CharField(max_length=100, blank=True)
    events_organized = models.IntegerField(default=0)
    blog_posts_published = models.IntegerField(default=0)
    community_members_helped = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.email} - Steward"
```

Profile models are created automatically when a user gains a role through contributions.

### 5. CategoryLeaderboard Model
```python
class CategoryLeaderboard(BaseModel):
    """
    Separate leaderboard for each category.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(ContributionCategory, on_delete=models.CASCADE)
    total_points = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'category']
        ordering = ['-total_points', 'user__name']
```

## Initial Categories Configuration

### Validator Category
- **Slug**: `validator`
- **Profile Model**: `validators.Validator`
- **Visible Fields**: `node_version`
- **Editable Fields**: `node_version`
- **Contribution Types**: 
  - Node Running
  - Uptime
  - Network Participation
  - Validator Setup
  - Node Upgrade

### Builder Category
- **Slug**: `builder`
- **Profile Model**: `builders.Builder`
- **Visible Fields**: `github_username`, `primary_language`, `repositories_contributed`, `pull_requests_merged`
- **Editable Fields**: `github_username`, `primary_language`
- **Contribution Types**:
  - Code Contribution
  - Bug Report
  - Documentation
  - Tool Development
  - Smart Contract Development

### Steward Category
- **Slug**: `steward`
- **Profile Model**: `stewards.Steward`
- **Visible Fields**: `twitter_handle`, `discord_handle`, `events_organized`, `blog_posts_published`, `community_members_helped`
- **Editable Fields**: `twitter_handle`, `discord_handle`
- **Contribution Types**:
  - Blog Post
  - Social Media Engagement
  - Community Event
  - Tutorial Creation
  - Community Support

## Business Logic

### Automatic Role and Profile Assignment
When a user makes a contribution:
1. System checks the contribution type's category
2. Creates UserRole entry for that user-category pair (if it doesn't exist)
3. Creates the corresponding profile model instance (e.g., Validator, Builder) if it doesn't exist
4. User automatically gains permissions for that category's fields

```python
@receiver(post_save, sender=Contribution)
def update_user_roles_and_profiles(sender, instance, created, **kwargs):
    """
    When a contribution is saved, ensure the user has the appropriate role and profile.
    """
    category = instance.contribution_type.category
    user = instance.user
    
    # Create or get UserRole
    UserRole.objects.get_or_create(user=user, category=category)
    
    # Create profile model instance if needed
    if category.profile_model:
        app_label, model_name = category.profile_model.split('.')
        ProfileModel = apps.get_model(app_label, model_name)
        ProfileModel.objects.get_or_create(user=user)
```

### Permission Checking
```python
# User model methods
def has_role(self, category_slug):
    """Check if user has a specific role."""
    return self.roles.filter(category__slug=category_slug).exists()

def can_view_field(self, field_name):
    """Check if user can view a specific field."""
    visible_fields = set()
    for role in self.roles.all():
        visible_fields.update(role.category.visible_fields)
    return field_name in visible_fields

def can_edit_field(self, field_name):
    """Check if user can edit a specific field."""
    editable_fields = set()
    for role in self.roles.all():
        editable_fields.update(role.category.editable_fields)
    return field_name in editable_fields
```

### Leaderboard Calculation
- Each category has its own leaderboard
- Points calculated only from contributions in that category
- Users appear on multiple leaderboards if they have multiple roles
- Rankings are category-specific

## API Endpoints

### New Endpoints
```
# Categories
GET /api/v1/categories/
GET /api/v1/categories/{slug}/
GET /api/v1/categories/{slug}/leaderboard/
GET /api/v1/categories/{slug}/contribution-types/

# User Roles
GET /api/v1/users/{id}/roles/
GET /api/v1/users/{id}/visible-fields/
GET /api/v1/users/{id}/editable-fields/

# Category-specific queries
GET /api/v1/leaderboard/?category=builder
GET /api/v1/contributions/?category=validator
```

### Modified Endpoints
```
# User profile returns role-based field visibility
GET /api/v1/users/me/
{
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["validator", "builder"],
    "visible_fields": ["node_version", "github_username", ...],
    "profile": {
        // Only includes fields user can view
    }
}

# Profile update only accepts editable fields
PATCH /api/v1/users/me/profile/
{
    "node_version": "1.2.3"  // Only if user has validator role
}
```

## Frontend Implementation

### Profile Component Logic
```javascript
// Check field visibility
const ProfileField = ({ fieldName, value, label }) => {
    const { user } = useAuth();
    
    if (!user.visible_fields.includes(fieldName)) {
        return null; // Don't render field
    }
    
    const isEditable = user.editable_fields.includes(fieldName);
    
    return (
        <div>
            <label>{label}</label>
            <input 
                value={value}
                disabled={!isEditable}
                onChange={...}
            />
        </div>
    );
};
```

### Leaderboard Views
```javascript
// Category selector for leaderboards
const LeaderboardView = () => {
    const [selectedCategory, setSelectedCategory] = useState('all');
    const categories = useCategories();
    
    return (
        <>
            <CategoryTabs 
                categories={categories}
                selected={selectedCategory}
                onChange={setSelectedCategory}
            />
            <LeaderboardTable category={selectedCategory} />
        </>
    );
};
```

## Migration Strategy

### Phase 1: Database Setup
1. Create new Django apps:
   - `validators` app (move existing Validator model here)
   - `builders` app (new Builder profile model)
   - `stewards` app (new Steward profile model)
2. Create new core models:
   - ContributionCategory (in contributions app - manages categories and permissions)
   - UserRole (in users app - links users to categories)
   - CategoryLeaderboard (in leaderboard app - separate leaderboards per category)
3. Move Validator model from users app to validators app
4. Create Builder model in builders app
5. Create Steward model in stewards app
6. Create "Validator" category pointing to validators.Validator
7. Assign all existing ContributionTypes to Validator category

### Phase 2: Data Migration
```python
def migrate_existing_data():
    # Create validator category
    validator = ContributionCategory.objects.create(
        name='Validator',
        slug='validator',
        profile_model='validators.Validator',
        visible_fields=['node_version'],
        editable_fields=['node_version']
    )
    
    # Assign existing contribution types to validator category
    ContributionType.objects.update(category=validator)
    
    # Create UserRoles for existing contributors
    for user in User.objects.filter(contributions__isnull=False).distinct():
        UserRole.objects.create(
            user=user,
            category=validator
        )
    
    # Validator profiles already exist - no need to migrate
    
    # Migrate leaderboard entries to CategoryLeaderboard
    for entry in LeaderboardEntry.objects.all():
        CategoryLeaderboard.objects.create(
            user=entry.user,
            category=validator,
            total_points=entry.total_points,
            rank=entry.rank
        )
```

### Phase 3: Add New Categories
1. Create Builder category with appropriate fields
2. Add new contribution types for builders
3. Create Steward category with appropriate fields
4. Add new contribution types for stewards

## Benefits

1. **Flexibility**: New categories can be added without code changes
2. **Automatic Permissions**: Users gain access to fields by contributing
3. **Clean Separation**: Each category has its own space and leaderboard
4. **Scalability**: System can grow with new categories and fields
5. **User Experience**: Users only see relevant fields in their profile
6. **No Manual Assignment**: Roles are earned, not assigned

## Security Considerations

1. **Field Validation**: Backend must validate field updates against user permissions
2. **API Security**: Filter response data based on requesting user's roles
3. **Admin Override**: Admins should be able to view/edit all fields

## Future Enhancements

1. **Role Requirements**: Minimum contributions needed to maintain active role
2. **Role Badges**: Visual indicators for user roles in UI
4. **Custom Fields**: Allow categories to define completely custom profile fields
5. **Role Hierarchies**: Some roles could inherit permissions from others
6. **Composite Roles**: Define roles that require multiple categories

## Django Settings Configuration

Add to `INSTALLED_APPS` in `backend/settings.py`:
```python
INSTALLED_APPS = [
    # ... existing apps ...
    'validators',
    'builders', 
    'stewards',
    # ... rest of apps ...
]
```

## Implementation Checklist

- [ ] Create database migrations for new models
- [ ] Implement ContributionCategory model and admin
- [ ] Update ContributionType model with category FK
- [ ] Implement UserRole model and auto-assignment logic
- [ ] Create UserProfile model with conditional fields
- [ ] Implement CategoryLeaderboard model
- [ ] Update User model with permission methods
- [ ] Create API endpoints for categories and roles
- [ ] Update user serializers with field filtering
- [ ] Implement frontend field visibility logic
- [ ] Create category-specific leaderboard views
- [ ] Write migration script for existing data
- [ ] Add tests for permission system
- [ ] Update documentation