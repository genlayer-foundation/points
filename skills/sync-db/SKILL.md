---
name: sync-db
description: This skill should be used when the user asks to "sync database", "get production data", "download prod db", "migrate database", "update local db", "refresh dev database", or needs to sync production data to local/dev environment.
version: 1.0.0
---

# Sync Production Database to Development

Run the database migration script to sync production data to local development environment.

## Prerequisites
- Virtual environment must be activated: `source backend/env/bin/activate`
- AWS CLI configured with Parameter Store access
- Docker installed (for database operations)

## Script Location
`backend/scripts/migrate-prod-to-dev.sh`

## Usage Options

### Download Production Database Only (Safest)
```bash
cd backend/scripts
./migrate-prod-to-dev.sh --download
```
Downloads production database to `backend/backups/` without making any local changes.

### Upload Latest Dump to Dev Database
```bash
cd backend/scripts
./migrate-prod-to-dev.sh --upload
```
Restores the most recent backup file to development database.

### Run Django Migrations and Create Admin User Only
```bash
cd backend/scripts
./migrate-prod-to-dev.sh --setup
```
Runs migrations and creates/updates admin user (`dev@genlayer.foundation` / `password`).

### Full Migration (Download + Upload + Setup)
```bash
cd backend/scripts
./migrate-prod-to-dev.sh
```
Complete workflow: download production data, restore to dev, run migrations, and create admin.

## What It Does
1. Fetches production database credentials from AWS Parameter Store
2. Downloads production PostgreSQL database using Docker (matching version)
3. Restores to development database (local or AWS dev instance)
4. Runs Django migrations
5. Creates/updates admin user with Steward role

## Notes
- Backups are saved to `backend/backups/` with timestamps
- Uses Docker to avoid PostgreSQL version mismatch issues
- See `backend/scripts/README.md` for detailed documentation and troubleshooting
