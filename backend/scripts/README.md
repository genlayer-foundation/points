# Database Migration Scripts

Scripts for migrating Tally production database to development environment.

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