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
├── social_connections/    # OAuth (GitHub, Twitter, Discord) + encrypted token storage
├── social_tasks/          # Repeatable social tasks (follow, join, like) and completions
├── users/                 # User management and auth
├── partners/              # Ecosystem partners directory
├── gen_tv/                # Gen TV livestream index
├── utils/                 # Shared utilities
└── tally/                 # Django project settings (settings.py, urls.py)
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
  - Contribution - Individual contribution records. Has optional `project_contribution` self-FK and `milestone_version` used by the Projects/Milestones split.
  - ContributionType - Categories with slug field, has M2M `accepted_evidence_url_types`
- **Projects/Milestones split**: `contributions/project_milestones.py`
  - `projects` and `milestones` are separate contribution types (migration 0068). Projects require a GitHub repository evidence URL (`required_evidence_url_types` = github-repo). Milestones must be linked to one of the submitter's ACCEPTED Projects CONTRIBUTIONS (`/submissions/accepted-projects/`) via the `project_contribution` self-FK, require a written change description (evidence optional), and get an auto-assigned sequential `milestone_version` per project contribution. IMPORTANT: this is unrelated to the projects app's curated `projects.Project` showcase table, which contribution flows must never create or modify.
  - FeaturedContent - Portal hero/community/validator-steward content managed through admin
  - ContributionTypeMultiplier - Dynamic point multipliers
  - Evidence - Evidence items with `url_type` FK for auto-detected URL type, `normalized_url` indexed field for fast duplicate detection (text descriptions and URLs only - file uploads are disabled)
  - EvidenceURLType - Defines URL type categories (X Post, GitHub PR, etc.) with regex patterns for auto-detection and handle ownership validation
- **URL Utilities**: `contributions/url_utils.py`
  - `normalize_url()` - Enhanced URL normalization (strips tracking params, preserves essential params)
  - `detect_url_type()` - Auto-detects URL type from regex patterns
  - `extract_handle()` - Extracts handle/owner from URL for ownership checks
  - `validate_handle_ownership()` - Validates URL handle matches user's linked social account
  - `check_duplicate_url()` - Checks for duplicate URLs across submissions
- **reCAPTCHA**: `contributions/recaptcha_field.py`
  - Custom DRF serializer field for Google reCAPTCHA v2 validation
  - Validates tokens from frontend reCAPTCHA widget
  - Required for new contribution submissions only (not for edits)

### Projects
- **Models**: `projects/models.py`
  - Project - Project profile with website/GitHub links, description, usage notes, details, media, participants, and related accepted contributions
  - ProjectMetric - Admin-managed title/value/detail metric rows for project pages
  - ProjectPageRevision - Owner-submitted ordered page blocks rendered through whitelisted portal components
- **AI Review**: `contributions/ai_review/views.py`
  - `/api/v1/ai-review/` - List pending unproposed submissions for the external AI review agent; proposal filters such as `has_proposal=true` opt into active proposals
  - `/api/v1/ai-review/{id}/` - Retrieve a pending submission with evidence and user history
  - `/api/v1/ai-review/{id}/propose/` - Submit an AI proposal for human approval
  - `/api/v1/ai-review/proposed/` - List pending submissions with active proposals awaiting steward review; use `proposed_by=ai` for AI-created proposals only
  - `/api/v1/ai-review/reviewed/` - List reviewed submissions that had AI proposals for calibration
  - `/api/v1/ai-review/templates/` - List review templates available to the AI review agent

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
  - `/api/v1/leaderboard/monthly/` - Top contribution totals for the current month by default, or for an explicit `start_date`/`end_date` range
  - `/api/v1/leaderboard/stats/` - Global statistics
  - `/api/v1/leaderboard/user_stats/by-address/{address}/` - User-specific stats
- **Social-task plumbing**: `calculate_category_points` and `calculate_waitlist_points` sum
  `Contribution.frozen_global_points` AND `social_tasks.SocialTaskCompletion.points_awarded`
  for the matching category. The `update_leaderboard_on_social_task_completion` post_save
  handler is wired in `social_tasks/apps.py:ready()`.
  All social-task reads in `leaderboard/models.py` go through the `_social_tasks_ready()`
  guard: old data migrations (e.g. contributions 0051) call `recalculate_all_leaderboards()`
  while replaying history on a fresh database, before `social_tasks` 0001 has run — the
  guard makes completions read as empty until the table exists (a try/except would abort
  the surrounding PostgreSQL migration transaction).
  Note: the community leaderboard ranking (`community_xp.utils.effective_community_ranking_queryset`,
  MEE6 + community contributions) does NOT include social-task points — community-category
  task points are profile-only (`socialTaskTotal` in user stats) and reach the community
  ranking only once a steward distributes them as Discord XP (steward Discord XP view →
  MEE6 picks them up; see the Social Tasks "Discord XP integration" note). Builder /
  validator category task points DO feed their leaderboards.

### Social Tasks
- **Models**: `social_tasks/models.py`
  - SocialTask - CMS row admins manage. Fields: name, slug, description, category (FK,
    restricted by clean() to the surfaced categories community/builder/validator —
    see SURFACED_CATEGORY_SLUGS), points, verification_type (slug of a registered
    verifier), typed target_* fields (only the ones used by a current verifier —
    today: `target_handle`, `target_guild_id`, `target_repo`), action_url (optional:
    save() derives it from the verifier when blank, e.g. the GitHub repo page or an
    X follow-intent link; clean() requires it for verifiers that cannot derive),
    cta_text, platform (derived from verifier on save), is_active, starts_at,
    ends_at, order (admin sort within the lists; list_editable). Add new target_*
    fields in the same migration as the verifier that needs them; the admin
    "Verification targets" fieldset picks up `target_*` model fields automatically.
    The changelist shows a per-task Completions count.
  - `SocialTask.clean()` validates the typed target field(s) required by the chosen
    verifier; raises ValidationError otherwise. The admin dropdown for
    verification_type is rendered from the registry, so new verifiers show up
    automatically.
  - SocialTaskCompletion - Per-user completion. unique_together (user, task).
    Stores points_awarded + verification_type snapshot + verification_data audit.
- **Discord XP integration**: community-category completions get a
  `contributions.ContributionDiscordXPState` row (post_save signal in
  `contributions/models.py`, registered with the lazy string sender
  `'social_tasks.SocialTaskCompletion'` to avoid a circular import), so they
  surface in the steward Discord XP view (`/api/v1/steward-discord-xp/`)
  alongside community contributions as XP to distribute manually. The state
  model holds exactly one source (`contribution` XOR `social_task_completion`,
  DB check constraint); `target_amount` reads `frozen_global_points` or
  `points_awarded` accordingly. Detail actions (`record-copy`,
  `mark-distributed`, `unset-distributed`) are keyed by the **state id** (not
  contribution id). Stewards with 'accept' permission on any community
  contribution type can manage social-task XP rows. Migration
  `contributions/0069` backfills states for pre-existing community completions.
- **Verifier registry**: `social_tasks/verifiers/` package
  - `base.py` exposes `Verifier` base class, `VerifierResult` dataclass, `@register`
    decorator, and dispatch helpers: `verify(task, user)`, `get_choices()`,
    `required_fields_for()`, `platform_for()`, `requires_verification_for()`,
    `required_connection_for()`.
  - One file per verification logic: `twitter_follow.py`, `discord_guild_join.py`,
    `github_star.py`, `click_through.py`. Each self-registers via `@register` and
    declares `verification_type`, `label`, `platform`, `required_fields`,
    `requires_verification`, and `required_connection` (which linked social
    account the verifier needs: 'twitter' / 'discord' / 'github' / None).
    Verifiers can also override `clean_task(task)` for admin-time validation
    beyond field presence (e.g. github_star validates the owner/repo format).
  - To add a new logic (e.g. github_star): create
    `social_tasks/verifiers/github_star.py`, declare a `Verifier` subclass with
    `@register`, implement `verify(task, user) -> VerifierResult`, import it from
    `verifiers/__init__.py`. Model.clean(), admin dropdown, serializer flag, and
    view dispatch pick it up automatically with no further central edits.
  - `twitter_follow` calls Sorsa via `social_tasks/sorsa_client.py:SorsaClient.is_following`.
  - `discord_guild_join` makes the Discord API call inline (not via
    `DiscordOAuthService.check_guild_membership`, which collapses all non-200
    cases into `False`). It distinguishes 200 (member), 404 (not member),
    401/403 (token expired), and 429/5xx / transport errors
    (-> `verification_unavailable`). On 401/403 it first attempts one
    `DiscordOAuthService.refresh_stored_access_token` rotation and retries
    (Discord user tokens expire after ~7 days), so long-linked users are not
    funneled into a re-link flow; only when the refresh itself is impossible
    (missing/invalid refresh token) does it return
    `token_invalid_relink_required`. It only writes back to
    `DiscordConnection.guild_member` when the checked guild is the main
    `settings.DISCORD_GUILD_ID`; custom-guild tasks must not corrupt the main
    guild flag.
  - `github_star` calls `GET https://api.github.com/user/starred/{owner}/{repo}`
    inline with the user's token (not via `GitHubOAuthService.check_repo_star`,
    which collapses non-204 statuses and falls back to an unpaginated public
    listing). 204 (starred), 404 (not starred), 401 (-> `token_invalid_relink_required`),
    403 rate-limit / 5xx / transport (-> `verification_unavailable`). Works with the
    portal's empty-scope GitHub tokens because starred repos are public data.
  - `click_through` always succeeds (trust on click; `requires_verification=False`).
- **Views**: `social_tasks/views.py:SocialTaskViewSet`
  - `GET /api/v1/social-tasks/` - List with `?status=active|completed`, `?category=community|builder|validator`.
    The internal `verification_type` slug is NOT exposed; each task instead carries
    two derived flags from the verifier registry: `requires_verification`
    ("open-and-credit" vs "open-then-verify" UX) and `required_connection`
    ('twitter' / 'discord' / 'github' / null — which linked account the card must
    offer inline linking for). The frontend never inspects verifier slugs.
  - `POST /api/v1/social-tasks/{slug}/complete/` - Run verification, award atomically (UserRateThrottle 30/min)
- **URLs**: `social_tasks/urls.py` mounted from `api/urls.py` under `/api/v1/`.
- **Seeded tasks** (slug): `follow-genlayer-x`, `join-genlayer-discord`,
  `check-out-genlayer-on-x`. All in `community` category, all 500 points
  (migration 0002 bumped the seeds and changed the model default from 10 to
  500; completions made before the bump keep their frozen `points_awarded`). Community ranking is
  MEE6-based and does not include social-task points, so these seeds award
  profile-only points (`socialTaskTotal`); builder / validator category tasks feed
  their leaderboards when created.

### Validators
- **Models**: `validators/models.py`
  - ValidatorWallet - Synced validator wallet metadata per network. Now also stores Wall of Shame observability state: `metrics_status`, `logs_status` (both `on` / `shame` / `unknown`), and `last_grafana_check_at`.
  - ValidatorWalletStatusSnapshot - Daily wallet status snapshots for uptime lookback
  - SyncLock - Database-backed sync coordination row with owner token for cross-worker locking
- **Services**: `validators/grafana_service.py`
  - GrafanaValidatorStatusService - Polls Grafana Cloud (`/api/ds/query`) Prometheus + Loki datasources and updates `ValidatorWallet.metrics_status` / `logs_status` for `status='active'` wallets, per network. Used by the Wall of Shame cron.
- **Views**: `validators/views.py`
  - `/api/v1/validators/` - Validator profile CRUD for authenticated users
  - `/api/v1/validators/me/` - GET/PATCH current validator profile
  - `/api/v1/validators/wallets/` - Read-only validator wallet listing
  - `/api/v1/validators/wallets/sync/` - POST cron-protected background sync trigger with DB-backed lock (on-chain validator sync)
  - `/api/v1/validators/wallets/sync-grafana/` - POST cron-protected background sync trigger for Grafana observability cross-check (separate SyncLock row `grafana_status_sync` so it can run alongside the on-chain sync)
  - `/api/v1/validators/wallets/wall-of-shame/` - Public read-only endpoint listing active validator wallets with `metrics_status` / `logs_status`. SHAME rows sort first. Cached 60s. Optional `?network=asimov|bradbury` filter.

### Partners (Ecosystem Partners)
- **Models**: `partners/models.py`
  - Partner - Ecosystem partner directory entry with `name`, `slug`, `description`, `logo_url`, `website_url`, optional `url` (deep link), `display_order`, `is_active`. Ordered by `display_order, name`.
- **Serializers**: `partners/serializers.py`
  - LightPartnerSerializer - Minimal fields (id, name, slug, logo_url, website_url) for list views
  - PartnerSerializer - Full fields for detail
- **Views**: `partners/views.py`
  - `/api/v1/partners/` - Public read-only list of active partners (search + ordering)
  - `/api/v1/partners/{slug}/` - Public read-only detail by slug
- **Migrations**: `partners/migrations/0001_initial.py` creates the model and seeds the 22 founding partners from a `RunPython` step.
- **Admin**: `partners/admin.py` - list_editable on `display_order`, `is_active`; slug prepopulated from name.

### Gen TV
- **Models**: `gen_tv/models.py`
  - Stream - Livestream entry with `title`, `slug`, `description`, `url`, `image_url`, `starts_at` (required), `ends_at` (required), `category` (`internal` / `community`), `is_active`. `status` is a derived `@property` computed from `starts_at`/`ends_at` (no DB column).
- **Serializers**: `gen_tv/serializers.py`
  - LightStreamSerializer - Minimal fields for list views (status comes through as a read-only string)
  - StreamSerializer - Full fields for detail
- **Views**: `gen_tv/views.py`
  - `/api/v1/gen-tv/streams/` - Public read-only list with `category` filter; pagination disabled (small dataset)
  - `/api/v1/gen-tv/streams/{slug}/` - Public read-only detail by slug
- **Admin**: `gen_tv/admin.py` - status surfaces as a read-only `computed_status` column; date_hierarchy on `starts_at`; slug prepopulated from title.

### POAPs

- **Models**: `poaps/models.py`
  - PoapDrop - POAP campaign/drop with slug, artwork, event window, status, max claims, and legacy import ID.
  - PoapDistribution - Claiming method/window/cap configuration for a drop.
  - PoapClaim - Individual minted or imported claim records.
- **Views**: `poaps/views.py`
  - `/api/v1/poaps/` - Public read-only POAP drop list.
  - `/api/v1/poaps/{slug}/` - Public read-only POAP drop detail.
- **Admin**: `poaps/admin.py` - `PoapDropAdmin` keeps `created_by` as an autocomplete field, includes only `PoapDistributionInline` in `inlines`, and exposes claims through the read-only `claims_link` field instead of rendering `PoapClaim` rows inline. This keeps heavily claimed drops editable without exceeding Django's POST field limit. Ruff RUF012 warnings on the Django admin `inlines = [PoapDistributionInline]` list literal are intentional false positives for this standard admin pattern.

### Database & Migrations
- **Migrations**: `{app}/migrations/`
- **Database**: SQLite by default, configured in settings.py
- **Run migrations**: `python manage.py migrate`
- **Create migrations**: `python manage.py makemigrations`

### Database Migration from Production
- **Script**: `backend/scripts/migrate-prod-to-dev.sh`
- **Documentation**: `backend/scripts/README.md`
- **Purpose**: Sync production PostgreSQL database to local/dev environment
- **Prerequisites**:
  - Virtual environment activated
  - AWS CLI configured with Parameter Store access
  - Docker installed (for database operations)

**Usage:**
```bash
# Navigate to scripts directory
cd backend/scripts

# Download production database only (safest option)
./migrate-prod-to-dev.sh --download

# Upload latest dump to dev database
./migrate-prod-to-dev.sh --upload

# Run Django migrations and create admin user only
./migrate-prod-to-dev.sh --setup

# Full migration (download + upload + setup)
./migrate-prod-to-dev.sh
```

**What it does:**
1. Fetches production database credentials from AWS Parameter Store (`/tally/prod/database_url`)
2. Downloads production data to `backend/backups/` using Docker
3. Restores to development database (local PostgreSQL or AWS dev instance)
4. Runs Django migrations
5. Creates/updates admin user (`dev@genlayer.foundation`) with Steward role — password comes from `DEV_ADMIN_PASSWORD` or is randomly generated and printed by the script

**Notes:**
- Uses Docker to avoid PostgreSQL version mismatch issues
- Modular operation allows partial runs (download, upload, setup separately)
- Creates timestamped backups in `backend/backups/`
- See `backend/scripts/README.md` for detailed setup and troubleshooting

### RDS to SQLite Migration
- **Script**: `backend/scripts/migrate_rds_to_sqlite.py`
- **Purpose**: Convert production PostgreSQL to local SQLite for development
- **Usage**: `python scripts/migrate_rds_to_sqlite.py` (from backend directory)
- **Notes**: Resets all passwords to 'pass', excludes leaderboard entries, backs up existing db.sqlite3

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
GET    /api/v1/users/           (requires auth)
GET    /api/v1/users/me/           (requires auth)
PATCH  /api/v1/users/me/           (requires auth, only name)
GET    /api/v1/users/{address}/    (requires auth)
GET    /api/v1/users/by-address/{address}/ (requires auth)
GET    /api/v1/users/validators/   (requires auth)
POST   /api/v1/users/link_x_account/       (requires auth, awards configured points for linking X)
POST   /api/v1/users/link_discord_account/  (requires auth, awards configured points for linking Discord)

# Social Tasks
GET    /api/v1/social-tasks/                     (?status=active|completed&category=community|builder|validator)
POST   /api/v1/social-tasks/{slug}/complete/     (requires auth; throttled 30/min/user)

# Contributions
GET    /api/v1/contributions/      (requires auth)
POST   /api/v1/contributions/      (requires auth)
GET    /api/v1/contributions/{id}/ (requires auth)
PATCH  /api/v1/contributions/{id}/ (requires auth)
DELETE /api/v1/contributions/{id}/ (requires auth)

# Submissions (submitter-side)
GET    /api/v1/submissions/my/                  (requires auth, paginated user submissions)
GET    /api/v1/submissions/accepted-projects/   (requires auth, the user's accepted Projects contributions milestones can link to, with next_milestone_version and github_url from evidence)
POST   /api/v1/submissions/{id}/appeal/         (requires auth, owner-only, one per submission)
POST   /api/v1/submissions/{id}/add-evidence/   (requires auth, owner-only)

# Contribution Types
GET    /api/v1/contribution-types/            (requires auth)
GET    /api/v1/contribution-types/{id}/       (requires auth)
GET    /api/v1/contribution-types/statistics/ (requires auth)

# Leaderboard
GET    /api/v1/leaderboard/                             (requires auth)
GET    /api/v1/leaderboard/monthly/                     (requires auth, ?type=builder|community|validator, ?limit=10, optional ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD)
GET    /api/v1/leaderboard/stats/                       (requires auth)
GET    /api/v1/leaderboard/user_stats/by-address/{address}/ (requires auth)

# Multipliers
GET    /api/v1/multipliers/        (requires auth)
GET    /api/v1/multiplier-periods/

# Validators - Wall of Shame
POST   /api/v1/validators/wallets/sync-grafana/    (cron-protected, X-Cron-Token, background)
GET    /api/v1/validators/wallets/wall-of-shame/   (public, cached 60s, ?network= filter)

# Steward Submissions
GET    /api/v1/steward-submissions/stats/           (requires steward)
GET    /api/v1/steward-submissions/daily-metrics/   (requires steward)

# AI Review Agent
GET    /api/v1/ai-review/
GET    /api/v1/ai-review/{id}/
POST   /api/v1/ai-review/{id}/propose/     (create new proposal)
PUT    /api/v1/ai-review/{id}/propose/     (update existing proposal)
GET    /api/v1/ai-review/proposed/     (pending active proposals awaiting steward review; add proposed_by=ai for AI-only)
GET    /api/v1/ai-review/reviewed/
GET    /api/v1/ai-review/templates/

# Partners (Ecosystem Partners)
GET    /api/v1/partners/                   (public, list active partners)
GET    /api/v1/partners/{slug}/            (public, partner detail)

# Projects
GET    /api/v1/projects/                   (public, active project profiles)
GET    /api/v1/projects/{slug}/            (public, project detail with metrics and related contributions)

# Gen TV
GET    /api/v1/gen-tv/streams/             (public, supports ?category= filter)
GET    /api/v1/gen-tv/streams/{slug}/      (public, stream detail)
```

### Leaderboard monthly date ranges

`GET /api/v1/leaderboard/monthly/` returns ranked users by contribution totals for `type` (for example `community` or `builder`) and optional `limit`. Without `start_date`, it defaults to the current calendar month beginning on day 1; with `start_date` and/or `end_date`, it filters contributions by `contribution_date` date in the provided inclusive range. Dates must be `YYYY-MM-DD`, and `start_date` must be before or equal to `end_date`; invalid dates return `400`.

Example:

`GET /api/v1/leaderboard/monthly/?type=community&limit=5&start_date=2026-05-07&end_date=2026-06-05`

Example response:

```json
[
  {
    "id": "monthly-community-123",
    "user": 123,
    "user_details": { "address": "0x...", "name": "Contributor" },
    "type": "community",
    "total_points": 40,
    "rank": 1
  }
]
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
- `RECAPTCHA_ALLOW_TEST_KEYS` - Optional opt-in flag for non-production deployments that intentionally use Google's reCAPTCHA test keys with `DEBUG=False`. Set to `true` to silence `django_recaptcha.recaptcha_test_key_error`; production must not set this flag. The logic lives in `tally/settings.py` near `_RECAPTCHA_TEST_PUBLIC_KEY` and `SILENCED_SYSTEM_CHECKS`.
- `CRON_SYNC_TOKEN` - Cron-protected endpoint auth (used by `sync` and `sync-grafana`)
- `GRAFANA_BASE_URL` - Grafana Cloud base URL (default `https://genlayerfoundation.grafana.net`)
- `GRAFANA_API_TOKEN` - Grafana service-account bearer token (required for Wall of Shame). Store in AWS SSM (`/tally/{env}/grafana_api_token`) for production.
- `GRAFANA_PROM_DS_UID` - Prometheus datasource UID (default `grafanacloud-prom`)
- `GRAFANA_LOKI_DS_UID` - Loki datasource UID (default `grafanacloud-logs`)
- `GRAFANA_ASIMOV_LABEL` / `GRAFANA_BRADBURY_LABEL` - Override the `network` label values Grafana queries use per testnet (defaults: `asimov-phase5`, `bradbury-phase1`)
- `SORSA_API_BASE_URL` - Sorsa API base URL (default `https://api.sorsa.app`); used for Twitter follow verification in social_tasks
- `SORSA_API_KEY` - Sorsa bearer token (secret, required). Store in AWS SSM (`/tally/{env}/sorsa_api_key`) for production.
- Note: the Sorsa request timeout and follow endpoint path are intentionally code constants in `social_tasks/sorsa_client.py`, not env vars. Changing the endpoint requires a code deploy anyway because the response parser lives in the same file.

**AWS Deployment:** For production deployments on AWS App Runner, all environment variables must be stored in AWS Systems Manager (SSM) Parameter Store. See `aws-deployment-guide.md` for setup instructions.

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
- **reCAPTCHA Protection**: New contribution submissions require Google reCAPTCHA v2 verification to prevent spam. Editing existing submissions does not require reCAPTCHA. Local development silences Google's test-key system check automatically when `DEBUG=True`; dev deployments that run with `DEBUG=False` can explicitly set `RECAPTCHA_ALLOW_TEST_KEYS=true`. Never enable that flag in production.

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

**Evidence URL Type Serializers** (`contributions/serializers.py`):
- `LightEvidenceURLTypeSerializer` - Minimal (id, name, slug, is_generic) for nested use in Evidence responses
- `EvidenceURLTypeSerializer` - Full serializer with url_patterns for client-side detection, used in ContributionType responses

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
