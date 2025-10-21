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
  - Evidence - Evidence items for contributions (text descriptions and URLs only - file uploads are disabled)
- **reCAPTCHA**: `contributions/recaptcha_field.py`
  - Custom DRF serializer field for Google reCAPTCHA v2 validation
  - Validates tokens from frontend reCAPTCHA widget
  - Required for new contribution submissions only (not for edits)

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
- `RECAPTCHA_PUBLIC_KEY` - Google reCAPTCHA site key (required - use test key from .env.example for development)
- `RECAPTCHA_PRIVATE_KEY` - Google reCAPTCHA secret key (required - use test key from .env.example for development)

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
- **Evidence Submission**: File uploads are disabled (issue #212). Evidence must be submitted as text descriptions or URLs only.
- **reCAPTCHA Protection**: New contribution submissions require Google reCAPTCHA v2 verification to prevent spam. Editing existing submissions does not require reCAPTCHA.

## Serialization Patterns & Performance Optimization

The project uses **context-aware serialization** to optimize API performance:
- **Light serializers** (`Light*Serializer`) for list views - minimal fields, no nested queries
- **Full serializers** for detail views - complete data with relationships
- ViewSets set `context['use_light_serializers'] = self.action == 'list'`
- Serializers check context flag to choose which nested serializer to use
- Always use `select_related()` for ForeignKey/OneToOne and `prefetch_related()` for reverse/M2M
- Light serializers defined at top of each app's `serializers.py` with `Light` prefix
- Performance impact: 99%+ query reduction (30s+ → <1s for list views)

**Examples**: See `users/serializers.py` for `LightUserSerializer` and `contributions/serializers.py` for `LightContributionSerializer`

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