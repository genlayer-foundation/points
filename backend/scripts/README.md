# Database Migration Scripts

Scripts for migrating Tally production database to development environment.

## Which script do I want?

| Goal | Script |
|---|---|
| Production data in my local `db.sqlite3` | `sync_prod_to_sqlite.py` |
| Production data in the shared dev **Postgres** instance | `migrate-prod-to-dev.sh` |
| Nothing — it does not finish | ~~`migrate_rds_to_sqlite.py`~~ |

Local Django uses SQLite unless `DATABASE_URL` is set, so day-to-day work wants
the first row.

## sync_prod_to_sqlite.py (local development)

```bash
cd backend
source env/bin/activate
python scripts/sync_prod_to_sqlite.py
```

Roughly 30 minutes. Needs Docker running and AWS credentials. All passwords
become `pass`. The existing `db.sqlite3` is renamed to
`db.sqlite3.backup_<timestamp>` — those are ~1.6GB each, so prune old ones.

Flags for resuming after a failure: `--reuse-dump` (skip pg_dump, use the newest
`backups/*.sql`), `--reuse-postgres` (the `tally-local-pg` container already
holds the data), `--keep-container`, `--keep-json`, `--no-leaderboard`.

It works in five stages: pg_dump production → restore into a local Postgres 17
container on port 5434 → `manage.py migrate` that copy → `dumpdata` from the
local copy → `loaddata` into a fresh SQLite, then rebuild the leaderboard.

Each stage exists because of a specific failure; do not "simplify" them away:

- **pg_dump, never `dumpdata`, against production.** Django issues a query per
  row for many-to-many fields. Over a remote link that is ~90 user rows per
  minute; a 3.5 hour run never finished the users table (production has ~56k).
- **Explicit Docker `--platform`.** A cached amd64 `postgres:17` on Apple
  Silicon fails with `exec format error`.
- **Migrate the local copy before exporting.** Production's schema lags the
  code, so `dumpdata` otherwise fails on model-only columns.
- **contenttypes and auth.permission are NOT excluded from the export.** The
  m2m rows reference production's permission ids; a fresh database generates
  different ones and `loaddata` fails its foreign-key check at commit, rolling
  back the whole load.
- **Every table except `django_migrations` is cleared before loading.** Data
  migrations seed rows that collide with the snapshot on natural keys such as
  `projects.Project.slug`.
- **Model signals are suppressed during the load.** Several `post_save`
  receivers ignore Django's `raw` flag and recreate rows the snapshot already
  contains — see "Known bug" below.
- **The leaderboard is rebuilt afterwards** (`manage.py update_leaderboard`),
  because leaderboard entries are excluded from the export.

### Known bug it works around

`contributions/models.py` `sync_contribution_discord_xp_state` and
`sync_social_task_completion_discord_xp_state`, plus
`users/signals.py:create_referral_code` and
`poaps/signals.py:attach_legacy_poap_claims`, do not check
`kwargs.get('raw')`. A fixture load therefore recreates every
`ContributionDiscordXPState` and dies on
`UNIQUE constraint failed: ...contribution_id` at the first row.

Neighbouring receivers guard correctly —
`ensure_validator_profile_for_graduation_contribution` in the same file and
`update_leaderboard_on_contribution` in `leaderboard/models.py` ("Skip during
fixture loading (loaddata) to avoid ordering issues"). The real fix is a
one-line `if kwargs.get('raw', False): return` in each of the four.

## migrate_rds_to_sqlite.py — do not use

Runs `dumpdata` straight against production RDS and does not complete (see
above). It also calls `loaddata json_file 'exclude' 'leaderboard'`, where the
trailing strings are parsed as *fixture labels*, not as an exclude option.

## Prerequisites

1. **Virtual Environment** must be activated:
   ```bash
   # If using virtualenvwrapper:
   workon your-tally-env
   
   # If using venv:
   source backend/env/bin/activate
   ```

2. **AWS CLI configured** with access to Parameter Store:
   ```bash
   aws configure
   ```

3. **AWS Parameters** must be set up (see below)

4. **Required tools**:
   - Docker (for database operations)
   - Python 3 with Django environment (activated)
   - AWS CLI

## AWS Parameter Store Setup

The scripts expect database URLs stored as single parameters in AWS Systems Manager Parameter Store:

### Production Parameter
```
/tally/prod/database_url  # Full PostgreSQL URL (SecureString)
```

### Development Parameter (Optional)
```
/tally-backend/dev/database_url  # Full PostgreSQL URL for dev environment (SecureString)
```

### Setting Parameters

To set parameters in AWS:

```bash
# Set production database URL
aws ssm put-parameter \
  --name "/tally/prod/database_url" \
  --value "postgresql://username:password@host:port/database" \
  --type "SecureString" \
  --overwrite

# Set development database URL (optional)
aws ssm put-parameter \
  --name "/tally-backend/dev/database_url" \
  --value "postgresql://tally_dev:password@host:port/tally_dev" \
  --type "SecureString" \
  --overwrite
```

The database URL format is: `postgresql://username:password@host:port/database_name`

If the development database URL is not set in AWS, the script will use local defaults (localhost, postgres user) and prompt for the password.

## Usage

**IMPORTANT**: Always activate your virtual environment first!

```bash
# Activate your virtual environment
workon your-tally-env  # or source backend/env/bin/activate

# Navigate to scripts directory
cd backend/scripts
```

### Migration Script Options

The migration script (`migrate-prod-to-dev.sh`) supports modular operations:

```bash
# Show help and all options
./migrate-prod-to-dev.sh --help

# Download production database only
./migrate-prod-to-dev.sh --download

# Upload last dump to dev database
./migrate-prod-to-dev.sh --upload

# Upload specific backup file
./migrate-prod-to-dev.sh --upload-file backup.sql

# Run Django migrations and create admin user only
./migrate-prod-to-dev.sh --setup

# Full migration (download + upload + setup) - default
./migrate-prod-to-dev.sh
```

### Common Workflows

```bash
# First time setup
./migrate-prod-to-dev.sh  # Full migration

# Re-run just the setup after fixing issues
./migrate-prod-to-dev.sh --setup

# Use existing backup without re-downloading
./migrate-prod-to-dev.sh --upload
./migrate-prod-to-dev.sh --setup

# Download fresh backup for later use
./migrate-prod-to-dev.sh --download
```

The script uses Docker containers with matching PostgreSQL versions to avoid version mismatch issues.

## What the Script Does

1. **Fetch credentials** from AWS Parameter Store
2. **Backup production database** to `backend/backups/` directory
3. **Drop and recreate** development database (with confirmation)
4. **Restore production data** to development
5. **Run Django migrations**
6. **Create admin user**:
   - Email: `dev@genlayer.foundation`
   - Password: `password`
   - Roles: Steward and Superuser

## Security Notes

- Production credentials are fetched from AWS Parameter Store (never hardcoded)
- Backups are stored locally in `backend/backups/` (add to .gitignore)
- The admin user password is intentionally simple for development only
- Never use these scripts in production environments

## Troubleshooting

### pg_dump Version Mismatch

The script automatically uses Docker containers with the correct PostgreSQL version to avoid mismatch issues.

### AWS Credentials Error

If you get AWS credential errors:
1. Run `aws configure` to set up your credentials
2. Ensure your AWS user has permissions to read from Parameter Store
3. Check the parameter paths are correct for your environment

### Connection Issues

If you can't connect to the database:
1. Check network connectivity to production database
2. Verify firewall/security group rules allow your IP
3. Ensure database credentials are correct in AWS Parameter Store