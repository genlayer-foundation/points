# Backend Quick Reference - Django Structure

## 📝 MAINTENANCE INSTRUCTIONS
**IMPORTANT**: Keep this file updated when you:
- Add new API endpoints - update the "API Endpoints Summary" section
- Create new models - add to relevant app section with location
- Add new apps - update "Project Structure" and create new section
- Change authentication flow - update "Authentication Flow" section
- Add new environment variables - update "Environment Variables" section
- Create new ViewSets or serializers - add to relevant app section
- Change URL patterns - update endpoint paths
- Add new commands or scripts - update "Common Commands" section

**Quick update checklist:**
```bash
# After making changes, check:
- [ ] New endpoints added to API Endpoints Summary?
- [ ] New models documented with file locations?
- [ ] New serializers listed in app sections?
- [ ] Environment variables documented?
- [ ] URL pattern changes reflected?
```

## Project Structure
```
backend/
├── api/                    # Core API app
├── contributions/          # Contribution tracking
├── leaderboard/           # Leaderboard and rankings
├── users/                 # User management and auth
├── utils/                 # Shared utilities
└── backend/               # Django project settings
```

## Key Files & Locations

### User Management
- **Models**: `users/models.py`
  - User model with email auth, name, address fields
  - Validator model with node_version field (OneToOne with User)
  - Custom UserManager for email-based auth
- **Views**: `users/views.py`
  - `/api/v1/users/me/` - GET/PATCH current user profile (name and node_version editable)
  - `/api/v1/users/by-address/{address}/` - Get user by wallet address
  - `/api/v1/users/validators/` - Get validator list from blockchain
- **Serializers**: `users/serializers.py`
  - UserSerializer - Full user data including validator info
  - ValidatorSerializer - Validator node version and target matching
  - UserProfileUpdateSerializer - Allows name and node_version updates
  - UserCreateSerializer - Registration

### Authentication
- **Views**: `api/views.py`
  - `/api/auth/nonce/` - Get nonce for SIWE
  - `/api/auth/login/` - Login with signed message
  - `/api/auth/verify/` - Verify auth status
  - `/api/auth/logout/` - Logout
- **Settings**: `backend/settings.py`
  - JWT auth configuration
  - CORS settings for frontend
  - Session-based auth with SIWE

### Contributions
- **Models**: `contributions/models.py`
  - Contribution - Individual contribution records
  - ContributionType - Categories with slug field (Node Running, Blog Posts, etc.)
  - ContributionTypeMultiplier - Dynamic point multipliers
  - Evidence - Evidence items for contributions

### Node Upgrade (Sub-app)
- **Models**: `contributions/node_upgrade/models.py`
  - TargetNodeVersion - Active target version for node upgrades
- **Admin**: `contributions/node_upgrade/admin.py`
  - TargetNodeVersion admin interface
- **Views**: `contributions/views.py`
  - `/api/v1/contributions/` - CRUD for contributions
  - `/api/v1/contribution-types/` - Contribution type management
  - `/api/v1/contribution-types/statistics/` - Stats per type

### Leaderboard
- **Models**: `leaderboard/models.py`
  - LeaderboardEntry - User rankings with total points
  - GlobalMultiplier - System-wide multipliers
  - MultiplierPeriod - Time-based multiplier changes
- **Views**: `leaderboard/views.py`
  - `/api/v1/leaderboard/` - Get rankings
  - `/api/v1/leaderboard/stats/` - Global statistics
  - `/api/v1/leaderboard/user_stats/by-address/{address}/` - User-specific stats

### Database & Migrations
- **Migrations**: `{app}/migrations/`
- **Database**: SQLite by default, configured in settings.py
- **Run migrations**: `python manage.py migrate`
- **Create migrations**: `python manage.py makemigrations`

## API Endpoints Summary

### Base URL
- Development: `http://localhost:8000`
- API Root: `/api/v1/`
- Auth endpoints: `/api/auth/` (not v1)

### Main Endpoints
```
# Authentication
GET    /api/auth/nonce/
POST   /api/auth/login/
GET    /api/auth/verify/
POST   /api/auth/logout/

# Users
GET    /api/v1/users/
GET    /api/v1/users/me/           (requires auth)
PATCH  /api/v1/users/me/           (requires auth, only name)
GET    /api/v1/users/{address}/
GET    /api/v1/users/by-address/{address}/
GET    /api/v1/users/validators/

# Contributions
GET    /api/v1/contributions/
POST   /api/v1/contributions/      (requires auth)
GET    /api/v1/contributions/{id}/
PATCH  /api/v1/contributions/{id}/ (requires auth)
DELETE /api/v1/contributions/{id}/ (requires auth)

# Contribution Types
GET    /api/v1/contribution-types/
GET    /api/v1/contribution-types/{id}/
GET    /api/v1/contribution-types/statistics/

# Leaderboard
GET    /api/v1/leaderboard/
GET    /api/v1/leaderboard/stats/
GET    /api/v1/leaderboard/user_stats/by-address/{address}/

# Multipliers
GET    /api/v1/multipliers/
GET    /api/v1/multiplier-periods/
```

## Environment Variables
Located in `.env` file:
- `VALIDATOR_RPC_URL` - Blockchain RPC endpoint
- `VALIDATOR_CONTRACT_ADDRESS` - Smart contract address
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode flag
- `ALLOWED_HOSTS` - Allowed host headers

## Common Commands
```bash
# Activate environment
source env/bin/activate

# Run development server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

## Authentication Flow
1. Frontend requests nonce from `/api/auth/nonce/`
2. User signs message with MetaMask
3. Frontend sends signed message to `/api/auth/login/`
4. Backend verifies signature and creates session
5. Session cookie is set for subsequent requests
6. All authenticated endpoints require session cookie

## Key Patterns
- All models inherit from `utils.models.BaseModel` (adds created_at, updated_at)
- ViewSets use DRF's ModelViewSet for standard CRUD
- Authentication uses Sign-In With Ethereum (SIWE)
- Points calculation: base_points × multipliers = total_points
- Addresses are stored lowercase but compared case-insensitively

## Serialization Patterns & Performance Optimization

### Overview
The project uses a **context-aware serialization pattern** that switches between lightweight and full serializers based on the view context. This pattern dramatically reduces database queries and improves API response times by 99%+ (from 30+ seconds to <1 second for list views).

### Light vs Full Serializers

#### **Light Serializers**
Light serializers return minimal data for list views and nested relationships:
- **Purpose**: Optimize list views by avoiding expensive queries
- **Location**: Defined at the top of each app's `serializers.py` file
- **Naming**: Prefix with `Light` (e.g., `LightUserSerializer`)
- **Characteristics**:
  - No nested relationships (or only light nested serializers)
  - No computed fields requiring additional queries
  - Only essential display fields
  - Use `serializers.Serializer` (not `ModelSerializer`) for explicit control

**Example Light Serializers by App:**

```python
# users/serializers.py
class LightUserSerializer(serializers.Serializer):
    """Minimal user data for list views"""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    profile_image_url = serializers.URLField(read_only=True)
    visible = serializers.BooleanField(read_only=True)

class LightValidatorSerializer(serializers.Serializer):
    """Minimal validator data without expensive stats"""
    node_version = serializers.CharField(read_only=True)
    matches_target = serializers.SerializerMethodField()
    target_version = serializers.SerializerMethodField()

class LightBuilderSerializer(serializers.Serializer):
    """Minimal builder data without expensive stats"""
    created_at = serializers.DateTimeField(read_only=True)

# contributions/serializers.py
class LightContributionTypeSerializer(serializers.Serializer):
    """Minimal contribution type data"""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    min_points = serializers.IntegerField(read_only=True)
    max_points = serializers.IntegerField(read_only=True)
    category = serializers.SerializerMethodField()

class LightContributionSerializer(serializers.Serializer):
    """Minimal contribution data using light nested serializers"""
    id = serializers.IntegerField(read_only=True)
    user = LightUserSerializer(read_only=True)
    contribution_type = LightContributionTypeSerializer(read_only=True)
    points = serializers.IntegerField(read_only=True)
    frozen_global_points = serializers.IntegerField(read_only=True)
    # ... other essential fields
```

#### **Full Serializers**
Full serializers return complete data with all relationships and computed fields:
- **Purpose**: Provide detailed data for single-object detail views
- **Location**: Defined after light serializers in each app's `serializers.py`
- **Naming**: Standard names (e.g., `UserSerializer`, `ContributionSerializer`)
- **Characteristics**:
  - Include all model fields
  - Nested relationships with full serializers
  - Computed fields (stats, aggregations)
  - Use `serializers.ModelSerializer` for convenience

### Context-Aware Serialization

Serializers check the `use_light_serializers` context flag to switch behavior:

```python
class ContributionSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()

    def get_user_details(self, obj):
        """Returns user details based on context"""
        use_light = self.context.get('use_light_serializers', True)
        if use_light:
            return LightUserSerializer(obj.user).data
        return UserSerializer(obj.user, context=self.context).data
```

**Setting Context in ViewSets:**

```python
class ContributionViewSet(viewsets.ReadOnlyModelViewSet):
    def get_serializer_context(self):
        """Use light serializers for list, full for detail"""
        context = super().get_serializer_context()
        context['use_light_serializers'] = self.action == 'list'
        return context
```

### Query Optimization Patterns

Always use `select_related()` and `prefetch_related()` in ViewSet `get_queryset()`:

```python
def get_queryset(self):
    queryset = Contribution.objects.all()

    # select_related: For ForeignKey and OneToOne (SQL JOIN)
    queryset = queryset.select_related(
        'user',                    # ForeignKey to User
        'user__validator',         # OneToOne through User
        'user__builder',           # OneToOne through User
        'contribution_type',       # ForeignKey to ContributionType
        'contribution_type__category'  # ForeignKey through ContributionType
    )

    # prefetch_related: For ManyToMany and reverse ForeignKey (separate query + Python join)
    queryset = queryset.prefetch_related(
        'evidence_items',  # Reverse ForeignKey
        'highlights'       # Reverse ForeignKey
    )

    return queryset
```

### Performance Best Practices

1. **List Views**:
   - Always use `use_light_serializers=True`
   - Skip expensive fields (e.g., referral_details, contribution stats)
   - Prefetch only what light serializers need

2. **Detail Views**:
   - Use `use_light_serializers=False` (or omit the flag)
   - Include all fields and relationships
   - Prefetch everything the serializer might access

3. **Skip Fields When Not Needed**:
```python
def get_evidence_items(self, obj):
    """Skip evidence in list views"""
    if self.context.get('use_light_serializers', True):
        return []
    return EvidenceSerializer(obj.evidence_items.all(), many=True).data
```

4. **Avoid N+1 Queries**:
   - Use `select_related` for ForeignKey/OneToOne
   - Use `prefetch_related` for ManyToMany/reverse ForeignKey
   - Check Django Debug Toolbar or `django.db.connection.queries` during development

### Creating New Serializers

**When adding a new model that will be nested in other serializers:**

1. **Create the light serializer** in the model's app `serializers.py`:
```python
class LightMyModelSerializer(serializers.Serializer):
    """Minimal MyModel data for list views"""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    # Only essential fields
```

2. **Create the full serializer** below the light serializers:
```python
class MyModelSerializer(serializers.ModelSerializer):
    # Full fields, relationships, computed properties
    class Meta:
        model = MyModel
        fields = '__all__'
```

3. **Use context-aware pattern** when this model is nested:
```python
def get_mymodel_details(self, obj):
    use_light = self.context.get('use_light_serializers', False)
    if use_light:
        return LightMyModelSerializer(obj.mymodel).data
    return MyModelSerializer(obj.mymodel, context=self.context).data
```

4. **Optimize the ViewSet queryset**:
```python
def get_queryset(self):
    return MyModel.objects.select_related(
        'related_field'
    ).prefetch_related(
        'many_related_field'
    )
```

### Serializer Organization

Each app's `serializers.py` should be organized as follows:

```python
from rest_framework import serializers
from .models import MyModel
from other_app.serializers import LightOtherSerializer  # Import light from other apps

# ============================================================================
# Lightweight Serializers for Optimized List Views
# ============================================================================

class LightMyModelSerializer(serializers.Serializer):
    """Minimal data for list views"""
    # ... fields

# ============================================================================
# Full Serializers
# ============================================================================

class MyModelSerializer(serializers.ModelSerializer):
    """Full serializer with all fields and relationships"""
    # ... fields and methods
```

### Common Context Flags

- `use_light_serializers`: `True` for list views, `False` for detail views
- `include_referral_details`: `True` only when explicitly needed (expensive)
- `request`: Pass the request object for building absolute URLs

### Example: Full Pattern Implementation

```python
# users/serializers.py
class UserSerializer(serializers.ModelSerializer):
    validator = serializers.SerializerMethodField()

    def get_validator(self, obj):
        if not hasattr(obj, 'validator'):
            return None
        use_light = self.context.get('use_light_serializers', False)
        if use_light:
            return LightValidatorSerializer(obj.validator).data
        return ValidatorSerializer(obj.validator, context=self.context).data

# users/views.py
class UserViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return User.objects.select_related('validator', 'builder')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['use_light_serializers'] = self.action == 'list'
        return context
```

### Measuring Performance Impact

Before implementing optimizations:
```
GET /api/v1/contributions/?page=1&limit=10
- Queries: ~1,500
- Time: 30+ seconds (timeout)
```

After implementing light serializers + query optimization:
```
GET /api/v1/contributions/?page=1&limit=10
- Queries: 5-10
- Time: <1 second
- Improvement: 99%+ reduction in queries
```

### Related PRs

- **PR #204**: Initial implementation of context-aware serialization and light serializers
  - Created lightweight serializers for all major models
  - Added query optimization across all ViewSets
  - Implemented context-aware switching in serializers
  - Reduced API timeouts from 30s+ to <1s

## Testing
- **Test Organization Best Practice**: Use `{app}/tests/` folder structure for better organization
  - Create `{app}/tests/__init__.py` to make it a Python package
  - Separate test files by functionality: `test_models.py`, `test_views.py`, `test_forms.py`, etc.
  - Example: `contributions/tests/test_validator_creation.py`
- Run specific app tests: `python manage.py test {app}`
- Run specific test file: `python manage.py test {app}.tests.test_filename`
- Run specific test class: `python manage.py test {app}.tests.test_filename.TestClassName`
- Test database is created/destroyed automatically
- **Important**: Add 'testserver' to ALLOWED_HOSTS in .env for tests to work properly

## Admin Panel
- URL: `/admin/`
- Requires superuser account
- Models registered in `{app}/admin.py`