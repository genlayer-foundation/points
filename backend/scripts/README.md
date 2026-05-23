# Database Migration Scripts

Scripts for syncing the Tally production database to local development.

## Local PostgreSQL Setup

Local development uses a shared PostgreSQL container. All orca sessions connect to the same container, each with its own database.

### Architecture
```
Docker: tally-postgres (port 5432, postgres:17)
  ├── tally_main        ← main worktree
  ├── tally_template    ← production snapshot (restored via migrate-prod-to-dev.sh)
  ├── tally_feature_x   ← orca session (created automatically)
  └── tally_pr_123      ← PR session (created automatically)
```

### Start the PostgreSQL Container

```bash
cd backend
docker compose up -d db
```

Container credentials (used by all local databases):
- **User**: `tally_user`
- **Password**: `tally_password`
- **Port**: `5432`

## Syncing Production Data

### Prerequisites

1. **Virtual Environment** activated:
   ```bash
   source backend/env/bin/activate
   ```
2. **AWS CLI configured** with Parameter Store access:
   ```bash
   aws configure
   ```
3. **Docker** installed and the `tally-postgres` container running

### Quick Sync Workflow

```bash
cd backend/scripts

# Download production database (creates timestamped backup in backend/backups/)
./migrate-prod-to-dev.sh --download

# Restore to tally_template database in local container
./migrate-prod-to-dev.sh --upload

# Run Django migrations and create admin user
./migrate-prod-to-dev.sh --setup

# Or do all three at once:
./migrate-prod-to-dev.sh
```

### Creating Session Databases from Template

After syncing production data to `tally_template`, create instant clones for orca sessions:

```bash
# Create a database for a session (instant via PostgreSQL template)
docker compose exec db psql -U tally_user -c 'CREATE DATABASE "tally-feature-x" TEMPLATE tally_template'

# Drop a session database
docker compose exec db psql -U tally_user -c 'DROP DATABASE IF EXISTS "tally-feature-x"'
```

Note: orca sessions get their `DATABASE_URL` set automatically via `orchestrator.yml` env_substitutions. You only need to create the database manually if the template exists and you want an instant clone.

### Script Options

```bash
# Show help and all options
./migrate-prod-to-dev.sh --help

# Download production database only
./migrate-prod-to-dev.sh --download

# Upload last dump to local PostgreSQL (tally_template)
./migrate-prod-to-dev.sh --upload

# Upload specific backup file
./migrate-prod-to-dev.sh --upload-file backup.sql

# Run Django migrations and create admin user only
./migrate-prod-to-dev.sh --setup

# Full migration (download + upload + setup) - default
./migrate-prod-to-dev.sh
```

## What the Script Does

1. **Fetch credentials** from AWS Parameter Store
2. **Backup production database** to `backend/backups/` directory
3. **Drop and recreate** the `tally_template` database (with confirmation)
4. **Restore production data** to `tally_template`
5. **Run Django migrations**
6. **Create admin user**:
   - Email: `dev@genlayer.foundation`
   - Password: `password`
   - Roles: Steward and Superuser

## AWS Parameter Store Setup

The scripts expect database URLs stored as parameters in AWS Systems Manager:

```
/tally/prod/database_url          # Production PostgreSQL URL (SecureString)
/tally-backend/dev/database_url   # Optional: remote dev database URL
```

If the dev parameter is not set, the script defaults to the local `tally-postgres` container.

## Deprecated: SQLite Migration

The old `migrate_rds_to_sqlite.py` script is deprecated. It converted production PostgreSQL to SQLite, which was slow (1+ hour) and had behavioral differences. Use the PostgreSQL workflow above instead.

## Troubleshooting

### Container Not Running
```bash
docker compose -f backend/docker-compose.yml up -d db
docker compose -f backend/docker-compose.yml ps
```

### pg_dump Version Mismatch
The script uses Docker containers with the correct PostgreSQL version automatically.

### Connection from orca Container
From inside orca Docker containers, use `host.docker.internal` instead of `localhost` to reach the PostgreSQL container. This is set automatically by `orchestrator.yml`.

### AWS Credentials Error
1. Run `aws configure` to set up your credentials
2. Ensure your AWS user has permissions to read from Parameter Store
3. Check the parameter paths are correct for your environment
