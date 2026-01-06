---
description: Migrate production RDS database to local SQLite
---

Migrate the production PostgreSQL database to local SQLite for development.

Steps:
1. Navigate to backend directory
2. Run the migration script: `python scripts/migrate_rds_to_sqlite.py`
3. Verify the migration completed successfully
4. Note that all user passwords will be reset to 'pass'

The script will:
- Export data from production RDS using AWS SSM credentials
- Clean and process data (remove leaderboard entries, reset passwords)
- Create fresh SQLite database with migrations
- Import cleaned data
- Backup existing db.sqlite3 before replacing
