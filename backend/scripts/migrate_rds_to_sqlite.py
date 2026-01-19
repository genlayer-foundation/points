#!/usr/bin/env python
"""
Migrate data from RDS PostgreSQL to local SQLite database.

Requirements (.env file):
    RDS_DATABASE_URL: Full PostgreSQL database URL (postgresql://user:pass@host:port/database)
    or
    RDS_DATABASE_URL_PARAM: SSM parameter name containing database URL (e.g., /tally/prod/database_url)
    or
    RDS_SECRET_NAME: Secrets Manager secret name containing database URL
    
    RESET_PASSWORD: New password for all users (optional, defaults to 'pass')

Usage:
    python migrate_rds_to_sqlite.py
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import boto3

# Add backend directory to Python path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables
load_dotenv()

def get_rds_credentials():
    """Get RDS credentials from AWS SSM Parameter Store or .env file."""
    # First check if full DATABASE_URL is in .env
    db_url = os.getenv('RDS_DATABASE_URL')
    if db_url:
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        return {
            'host': parsed.hostname,
            'port': str(parsed.port) if parsed.port else '5432',
            'database': parsed.path.lstrip('/'),
            'username': parsed.username,
            'password': parsed.password
        }
    
    # Try SSM Parameter Store for DATABASE_URL
    param_name = os.getenv('RDS_DATABASE_URL_PARAM', '/tally/prod/database_url')
    
    try:
        client = boto3.client('ssm')
        response = client.get_parameter(Name=param_name, WithDecryption=True)
        db_url = response['Parameter']['Value']
        
        # Parse postgresql://username:password@host:port/database
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        
        return {
            'host': parsed.hostname,
            'port': str(parsed.port) if parsed.port else '5432',
            'database': parsed.path.lstrip('/'),
            'username': parsed.username,
            'password': parsed.password
        }
    except Exception as e:
        print(f"Warning: Could not get database URL from SSM: {e}")
    
    # Try to get from AWS Secrets Manager (expects full database URL in secret)
    secret_name = os.getenv('RDS_SECRET_NAME')
    if secret_name:
        try:
            client = boto3.client('secretsmanager')
            response = client.get_secret_value(SecretId=secret_name)
            secret_data = json.loads(response['SecretString'])
            
            # Check if it's a database URL or individual fields
            if 'database_url' in secret_data:
                db_url = secret_data['database_url']
                from urllib.parse import urlparse
                parsed = urlparse(db_url)
                return {
                    'host': parsed.hostname,
                    'port': str(parsed.port) if parsed.port else '5432',
                    'database': parsed.path.lstrip('/'),
                    'username': parsed.username,
                    'password': parsed.password
                }
        except:
            pass
    
    # No credentials found
    raise ValueError(
        "RDS credentials not found. Please provide either:\n"
        "1. RDS_DATABASE_URL in .env file (full PostgreSQL URL)\n"
        "2. RDS_DATABASE_URL_PARAM pointing to SSM parameter with database URL\n"
        "3. RDS_SECRET_NAME pointing to AWS Secrets Manager secret with database_url field\n"
        "4. AWS credentials configured to access /tally/prod/database_url in SSM"
    )

def export_from_rds():
    """Export data from RDS using Django dumpdata."""
    print("=" * 60)
    print("EXPORTING FROM RDS DATABASE")
    print("=" * 60)
    
    # Get RDS connection details
    creds = get_rds_credentials()
    host = creds['host']
    port = creds['port']
    database = creds['database']
    username = creds['username']
    password = creds['password']
    
    if not password:
        raise ValueError("RDS password not found. Set RDS_PASSWORD in .env or configure AWS credentials")
    
    print(f"Host: {host}")
    print(f"Database: {database}")
    print(f"User: {username}")
    
    # Create export filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_dump_file = f"rds_dump_{timestamp}.json"
    
    # Set DATABASE_URL for Django to use RDS
    db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    # Export using Django's dumpdata
    cmd = [
        'python', 'manage.py', 'dumpdata',
        '--indent', '2',
        '--exclude', 'contenttypes',
        '--exclude', 'auth.permission',
        '--exclude', 'sessions',
        '--exclude', 'admin.logentry',
        '--exclude', 'leaderboard.leaderboardentry',  # Exclude leaderboard entries
        '--output', json_dump_file
    ]
    
    env = os.environ.copy()
    env['DATABASE_URL'] = db_url
    
    print(f"\nExporting data to {json_dump_file}...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    if result.returncode != 0:
        print(f"Error during export: {result.stderr}")
        return None
    
    # Check file size
    file_size = Path(json_dump_file).stat().st_size / 1024
    print(f"✓ Data exported successfully ({file_size:.2f} KB)")
    return json_dump_file

def clean_and_process_data(json_file):
    """Clean data: remove leaderboard entries and reset passwords."""
    print("\n" + "=" * 60)
    print("CLEANING AND PROCESSING DATA")
    print("=" * 60)
    
    reset_password = os.getenv('RESET_PASSWORD', 'pass')
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} objects")
    
    # Track statistics
    stats = {
        'users_processed': 0,
        'passwords_reset': 0,
        'leaderboard_removed': 0
    }
    
    cleaned_data = []
    
    # Create password hash for all users
    from django.contrib.auth.hashers import make_password
    new_password_hash = make_password(reset_password)
    
    for item in data:
        model = item.get('model', '')
        
        # Skip leaderboard entries (already excluded in export, but double-check)
        if model == 'leaderboard.leaderboardentry':
            stats['leaderboard_removed'] += 1
            continue
        
        # Reset user passwords
        if model == 'users.user' or model == 'auth.user':
            stats['users_processed'] += 1
            if 'password' in item['fields']:
                item['fields']['password'] = new_password_hash
                stats['passwords_reset'] += 1
                username = item['fields'].get('username', item['fields'].get('email', 'unknown'))
                print(f"  Reset password for user: {username}")
        
        cleaned_data.append(item)
    
    # Save cleaned data
    clean_file = json_file.replace('.json', '_clean.json')
    with open(clean_file, 'w') as f:
        json.dump(cleaned_data, f, indent=2)
    
    print(f"\n✓ Processed {len(cleaned_data)} objects")
    print(f"  - Users processed: {stats['users_processed']}")
    print(f"  - Passwords reset: {stats['passwords_reset']}")
    print(f"  - Leaderboard entries removed: {stats['leaderboard_removed']}")
    print(f"  - New password for all users: {reset_password}")
    print(f"\n✓ Cleaned data saved to {clean_file}")
    
    return clean_file

def import_to_sqlite(json_file):
    """Import cleaned data to local SQLite database."""
    print("\n" + "=" * 60)
    print("IMPORTING TO LOCAL SQLITE DATABASE")
    print("=" * 60)
    
    # Remove DATABASE_URL to use local SQLite
    if 'DATABASE_URL' in os.environ:
        del os.environ['DATABASE_URL']
    
    # Backup current database if it exists
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if Path('db.sqlite3').exists():
        backup_name = f'db.sqlite3.backup_{timestamp}'
        print(f"Backing up current database to {backup_name}...")
        subprocess.run(['cp', 'db.sqlite3', backup_name])
        print(f"✓ Backup created")
        
        # Remove current database
        os.remove('db.sqlite3')
    
    # Run migrations to create fresh database
    print("Creating fresh database...")
    result = subprocess.run(
        ['python', 'manage.py', 'migrate', '--run-syncdb'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error during migration: {result.stderr}")
        return False
    
    # Load data
    print(f"Loading data from {json_file}...")
    result = subprocess.run(
        ['python', 'manage.py', 'loaddata', json_file, 'exclude', 'leaderboard'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error during import: {result.stderr}")
        if "IntegrityError" in result.stderr:
            print("\n⚠️ Integrity error detected. Some data may not have been imported.")
        return False
    
    print("✓ Data imported successfully!")
    
    # Verify import
    verify_import()
    return True

def verify_import():
    """Verify the imported data."""
    print("\nVerifying imported data...")
    
    cmd = '''python manage.py shell -c "
from users.models import User
from contributions.models import Contribution, ContributionType
print(f'Users: {User.objects.count()}')
print(f'Contributions: {Contribution.objects.count()}')
print(f'Contribution Types: {ContributionType.objects.count()}')
"'''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)

def main():
    """Main function."""
    print("RDS to SQLite Migration Tool")
    print("This will export data from RDS and import to local SQLite\n")
    
    # Check if we're in the right directory
    if not Path('manage.py').exists():
        print("Error: This script must be run from the Django backend directory")
        print("Please cd to the backend directory and try again")
        sys.exit(1)
    
    # Import Django settings to enable password hashing
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    
    try:
        # Step 1: Export from RDS
        json_file = export_from_rds()
        
        if not json_file or not Path(json_file).exists():
            print("\n✗ Export failed!")
            sys.exit(1)
        
        # Step 2: Clean and process data
        clean_file = clean_and_process_data(json_file)
        
        # Step 3: Import to SQLite
        if not import_to_sqlite(clean_file):
            print("\n✗ Import failed!")
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("✓ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nFiles created:")
        print(f"  - RDS dump: {json_file}")
        print(f"  - Cleaned data: {clean_file}")
        print(f"\n⚠️ All user passwords have been reset to: {os.getenv('RESET_PASSWORD', 'pass')}")
        
    except Exception as e:
        print(f"\n✗ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
