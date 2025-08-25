#!/bin/bash

# Tally Production to Development Database Migration Script (Modular Version)
# Supports partial operations: download, upload, setup
# Uses Docker to avoid pg_dump version mismatch issues

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Operation mode
MODE="all"  # Default to full migration
BACKUP_FILE=""  # For upload mode

# Parse command line arguments
print_usage() {
    echo -e "${BLUE}Usage: $0 [OPTIONS]${NC}"
    echo ""
    echo "Options:"
    echo "  --download    Download production database only"
    echo "  --upload      Upload last dump to dev database"
    echo "  --upload-file <file>  Upload specific dump file to dev database"
    echo "  --setup       Run Django migrations and create admin user only"
    echo "  --all         Run complete migration (default)"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --download              # Just download prod data"
    echo "  $0 --upload                 # Use last dump to restore dev"
    echo "  $0 --upload-file backup.sql # Use specific file"
    echo "  $0 --setup                  # Just run migrations & create admin"
    echo "  $0                          # Full migration (download + upload + setup)"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --download)
            MODE="download"
            shift
            ;;
        --upload)
            MODE="upload"
            shift
            ;;
        --upload-file)
            MODE="upload"
            BACKUP_FILE="$2"
            shift 2
            ;;
        --setup)
            MODE="setup"
            shift
            ;;
        --all)
            MODE="all"
            shift
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Tally Database Migration (Mode: $MODE) ===${NC}"
echo ""

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}Error: Not running in a virtual environment${NC}"
    echo ""
    echo "Please activate your virtual environment first:"
    echo "  - If using virtualenvwrapper: workon <your-env-name>"
    echo "  - If using venv: source env/bin/activate"
    echo ""
    echo "Then run this script again"
    exit 1
fi

echo -e "${GREEN}Virtual environment detected: $VIRTUAL_ENV${NC}"

# AWS Parameter Store paths
PROD_PARAM_PATH="/tally/prod/database_url"
DEV_PARAM_PATH="/tally-backend/dev/database_url"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get AWS parameter value
get_parameter() {
    local param_name=$1
    local value
    
    # Try to get parameter and capture any errors
    if value=$(aws ssm get-parameter --name "$param_name" --with-decryption --query 'Parameter.Value' --output text 2>&1); then
        # Check if value is not "None" or empty
        if [ "$value" != "None" ] && [ ! -z "$value" ]; then
            echo "$value"
            return 0
        else
            return 1
        fi
    else
        # Only print debug for actual errors (not just missing parameters)
        if [[ ! "$value" == *"ParameterNotFound"* ]]; then
            echo "Debug: Failed to get parameter $param_name: $value" >&2
        fi
        return 1
    fi
}

# Function to find the latest backup file
find_latest_backup() {
    local backup_dir="$BACKEND_DIR/backups"
    if [ -d "$backup_dir" ]; then
        # Find the most recent .sql file
        latest=$(ls -t "$backup_dir"/*.sql 2>/dev/null | head -1)
        if [ ! -z "$latest" ]; then
            echo "$latest"
            return 0
        fi
    fi
    return 1
}

# Check for required tools based on mode
check_required_tools() {
    echo -e "${YELLOW}Checking required tools...${NC}"
    
    local required_tools=("aws" "python3")
    
    if [ "$MODE" != "setup" ]; then
        required_tools+=("docker")
    fi
    
    for tool in "${required_tools[@]}"; do
        if ! command_exists $tool; then
            echo -e "${RED}Error: $tool is not installed${NC}"
            if [ "$tool" = "docker" ]; then
                echo "Please install Docker or use the non-Docker version"
            fi
            exit 1
        fi
    done
    
    # Check AWS CLI configuration
    echo -e "${YELLOW}Checking AWS credentials...${NC}"
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo -e "${RED}Error: AWS CLI is not configured. Please run 'aws configure'${NC}"
        exit 1
    fi
}

# Function to download production database
download_production() {
    echo -e "${BLUE}=== DOWNLOAD MODE ===${NC}"
    
    # Fetch production database URL from AWS Parameter Store
    echo -e "${YELLOW}Fetching production database URL from AWS...${NC}"
    
    echo "Fetching $PROD_PARAM_PATH..."
    PROD_DATABASE_URL=$(get_parameter "$PROD_PARAM_PATH")
    
    if [ -z "$PROD_DATABASE_URL" ]; then
        echo -e "${YELLOW}Warning: Could not fetch $PROD_PARAM_PATH${NC}"
        echo -e "${YELLOW}Enter production database URL (postgresql://user:pass@host:port/dbname):${NC}"
        read PROD_DATABASE_URL
    fi
    
    # Parse the database URL
    if [ ! -z "$PROD_DATABASE_URL" ]; then
        # Extract components from postgresql://user:pass@host:port/dbname
        DB_STRING=${PROD_DATABASE_URL#postgresql://}
        USER_PASS=${DB_STRING%%@*}
        PROD_DB_USER=${USER_PASS%%:*}
        PROD_DB_PASSWORD=${USER_PASS#*:}
        HOST_PORT_DB=${DB_STRING#*@}
        HOST_PORT=${HOST_PORT_DB%%/*}
        PROD_DB_HOST=${HOST_PORT%%:*}
        if [[ "$HOST_PORT" == *":"* ]]; then
            PROD_DB_PORT=${HOST_PORT#*:}
        else
            PROD_DB_PORT=5432
        fi
        PROD_DB_NAME=${HOST_PORT_DB#*/}
        
        echo -e "${GREEN}Parsed database connection:${NC}"
        echo "  Host: $PROD_DB_HOST"
        echo "  Port: $PROD_DB_PORT"
        echo "  Database: $PROD_DB_NAME"
        echo "  User: $PROD_DB_USER"
    else
        echo -e "${RED}Error: No production database URL provided${NC}"
        exit 1
    fi
    
    # Backup configuration
    BACKUP_DIR="$BACKEND_DIR/backups"
    BACKUP_FILE="$BACKUP_DIR/tally_prod_$(date +%Y%m%d_%H%M%S).sql"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Detect production PostgreSQL version
    echo -e "${YELLOW}Detecting production PostgreSQL version...${NC}"
    
    # Try to detect version using psql
    if command -v psql >/dev/null 2>&1; then
        VERSION_STRING=$(PGPASSWORD=$PROD_DB_PASSWORD psql -h "$PROD_DB_HOST" -p "$PROD_DB_PORT" -U "$PROD_DB_USER" -d "$PROD_DB_NAME" -t -c "SELECT version();" 2>/dev/null || echo "")
        
        # Extract major version number (works on both Linux and macOS)
        if [ ! -z "$VERSION_STRING" ]; then
            PROD_PG_VERSION=$(echo "$VERSION_STRING" | sed -n 's/.*PostgreSQL \([0-9][0-9]*\).*/\1/p')
        fi
    fi
    
    # If detection failed, use default
    if [ -z "$PROD_PG_VERSION" ]; then
        PROD_PG_VERSION="17"  # Default to PostgreSQL 17 (current production version)
        echo -e "${YELLOW}Could not detect version, using PostgreSQL $PROD_PG_VERSION${NC}"
    else
        echo -e "${GREEN}Production PostgreSQL version: $PROD_PG_VERSION${NC}"
    fi
    
    # Dump production database using Docker
    echo -e "${YELLOW}Dumping production database using Docker...${NC}"
    echo "Using postgres:$PROD_PG_VERSION Docker image"
    echo "Connecting to $PROD_DB_HOST:$PROD_DB_PORT/$PROD_DB_NAME as $PROD_DB_USER"
    
    docker run --rm \
        -v "$BACKUP_DIR:/backup" \
        -e PGPASSWORD="$PROD_DB_PASSWORD" \
        postgres:$PROD_PG_VERSION \
        pg_dump \
            -h "$PROD_DB_HOST" \
            -p "$PROD_DB_PORT" \
            -U "$PROD_DB_USER" \
            -d "$PROD_DB_NAME" \
            --no-owner \
            --no-acl \
            --clean \
            --if-exists \
            --format=plain \
            --file="/backup/$(basename $BACKUP_FILE)" \
            --verbose
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Production database dumped successfully${NC}"
        echo -e "${GREEN}Backup saved to: $BACKUP_FILE${NC}"
        echo ""
        echo "To upload this dump to dev, run:"
        echo "  $0 --upload"
    else
        echo -e "${RED}Error: Failed to dump production database${NC}"
        exit 1
    fi
}

# Function to upload to development database
upload_to_development() {
    echo -e "${BLUE}=== UPLOAD MODE ===${NC}"
    
    # Determine which backup file to use
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${YELLOW}Looking for latest backup file...${NC}"
        BACKUP_FILE=$(find_latest_backup)
        if [ -z "$BACKUP_FILE" ]; then
            echo -e "${RED}Error: No backup files found in $BACKEND_DIR/backups/${NC}"
            echo "Run with --download first to create a backup"
            exit 1
        fi
        echo -e "${GREEN}Using latest backup: $BACKUP_FILE${NC}"
    else
        if [ ! -f "$BACKUP_FILE" ]; then
            echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
            exit 1
        fi
        echo -e "${GREEN}Using specified backup: $BACKUP_FILE${NC}"
    fi
    
    # Fetch credentials from AWS
    echo -e "${YELLOW}Fetching database credentials from AWS...${NC}"
    
    # Get production credentials (for creating DB if on same instance)
    echo "Fetching $PROD_PARAM_PATH..."
    PROD_DATABASE_URL=$(get_parameter "$PROD_PARAM_PATH")
    if [ ! -z "$PROD_DATABASE_URL" ]; then
        DB_STRING=${PROD_DATABASE_URL#postgresql://}
        USER_PASS=${DB_STRING%%@*}
        PROD_DB_USER=${USER_PASS%%:*}
        PROD_DB_PASSWORD=${USER_PASS#*:}
        HOST_PORT_DB=${DB_STRING#*@}
        HOST_PORT=${HOST_PORT_DB%%/*}
        PROD_DB_HOST=${HOST_PORT%%:*}
    fi
    
    # Get development credentials
    echo "Fetching $DEV_PARAM_PATH..."
    DEV_DATABASE_URL=$(get_parameter "$DEV_PARAM_PATH")
    
    if [ ! -z "$DEV_DATABASE_URL" ]; then
        # Parse the dev database URL
        DB_STRING=${DEV_DATABASE_URL#postgresql://}
        USER_PASS=${DB_STRING%%@*}
        DEV_DB_USER=${USER_PASS%%:*}
        DEV_DB_PASSWORD=${USER_PASS#*:}
        HOST_PORT_DB=${DB_STRING#*@}
        HOST_PORT=${HOST_PORT_DB%%/*}
        DEV_DB_HOST=${HOST_PORT%%:*}
        if [[ "$HOST_PORT" == *":"* ]]; then
            DEV_DB_PORT=${HOST_PORT#*:}
        else
            DEV_DB_PORT=5432
        fi
        DEV_DB_NAME=${HOST_PORT_DB#*/}
        echo -e "${GREEN}Using dev database from AWS${NC}"
    else
        # Use local defaults if not in AWS
        echo -e "${YELLOW}No dev database URL in AWS, using local defaults${NC}"
        DEV_DB_HOST="localhost"
        DEV_DB_PORT="5432"
        DEV_DB_NAME="tally_dev"
        DEV_DB_USER="postgres"
        
        echo -e "${YELLOW}Enter password for local development database user ($DEV_DB_USER):${NC}"
        read -s DEV_DB_PASSWORD
        echo ""
    fi
    
    echo -e "${GREEN}Development database configuration:${NC}"
    echo "  Host: $DEV_DB_HOST"
    echo "  Port: $DEV_DB_PORT"
    echo "  Database: $DEV_DB_NAME"
    echo "  User: $DEV_DB_USER"
    
    # Detect PostgreSQL version from backup
    PROD_PG_VERSION=$(head -20 "$BACKUP_FILE" | grep -E "^-- Dumped from database version" | sed 's/.*version \([0-9][0-9]*\).*/\1/' || echo "17")
    echo -e "${GREEN}Using PostgreSQL version: $PROD_PG_VERSION${NC}"
    
    # Ask for confirmation before dropping dev database
    echo -e "${RED}WARNING: This will DROP and RECREATE the development database!${NC}"
    echo -e "${YELLOW}Do you want to continue? (yes/no):${NC}"
    read -r CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Upload cancelled"
        exit 0
    fi
    
    # Drop and recreate the development database
    echo -e "${YELLOW}Dropping and recreating development database...${NC}"
    
    # Check if we're on the same RDS instance (compare hosts)
    if [ "$PROD_DB_HOST" = "$DEV_DB_HOST" ] && [ ! -z "$PROD_DB_USER" ]; then
        echo -e "${YELLOW}Same RDS instance detected - using production user to create dev database${NC}"
        
        # Use production user to drop and create
        docker run --rm \
            -e PGPASSWORD="$PROD_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h "$DEV_DB_HOST" -p "$DEV_DB_PORT" -U "$PROD_DB_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS $DEV_DB_NAME"
        
        docker run --rm \
            -e PGPASSWORD="$PROD_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h "$DEV_DB_HOST" -p "$DEV_DB_PORT" -U "$PROD_DB_USER" -d postgres \
            -c "CREATE DATABASE $DEV_DB_NAME"
        
        docker run --rm \
            -e PGPASSWORD="$PROD_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h "$DEV_DB_HOST" -p "$DEV_DB_PORT" -U "$PROD_DB_USER" -d "$DEV_DB_NAME" \
            -c "GRANT ALL PRIVILEGES ON DATABASE $DEV_DB_NAME TO $DEV_DB_USER; GRANT ALL ON SCHEMA public TO $DEV_DB_USER; GRANT CREATE ON SCHEMA public TO $DEV_DB_USER;"
    elif [ "$DEV_DB_HOST" = "localhost" ] || [ "$DEV_DB_HOST" = "127.0.0.1" ]; then
        # Use host network for localhost connections
        docker run --rm \
            --network host \
            -e PGPASSWORD="$DEV_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h localhost -p "$DEV_DB_PORT" -U "$DEV_DB_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS $DEV_DB_NAME"
        
        docker run --rm \
            --network host \
            -e PGPASSWORD="$DEV_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h localhost -p "$DEV_DB_PORT" -U "$DEV_DB_USER" -d postgres \
            -c "CREATE DATABASE $DEV_DB_NAME"
    else
        # Different remote host
        echo -e "${YELLOW}Different host detected - using dev user${NC}"
        docker run --rm \
            -e PGPASSWORD="$DEV_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h "$DEV_DB_HOST" -p "$DEV_DB_PORT" -U "$DEV_DB_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS $DEV_DB_NAME"
        
        docker run --rm \
            -e PGPASSWORD="$DEV_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h "$DEV_DB_HOST" -p "$DEV_DB_PORT" -U "$DEV_DB_USER" -d postgres \
            -c "CREATE DATABASE $DEV_DB_NAME"
    fi
    
    # Restore the database
    echo -e "${YELLOW}Restoring database...${NC}"
    
    if [ "$DEV_DB_HOST" = "localhost" ] || [ "$DEV_DB_HOST" = "127.0.0.1" ]; then
        docker run --rm \
            --network host \
            -v "$(dirname $BACKUP_FILE):/backup" \
            -e PGPASSWORD="$DEV_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h localhost -p "$DEV_DB_PORT" -U "$DEV_DB_USER" -d "$DEV_DB_NAME" -f "/backup/$(basename $BACKUP_FILE)"
    else
        docker run --rm \
            -v "$(dirname $BACKUP_FILE):/backup" \
            -e PGPASSWORD="$DEV_DB_PASSWORD" \
            postgres:$PROD_PG_VERSION \
            psql -h "$DEV_DB_HOST" -p "$DEV_DB_PORT" -U "$DEV_DB_USER" -d "$DEV_DB_NAME" -f "/backup/$(basename $BACKUP_FILE)"
    fi
    
    echo -e "${GREEN}Database restored to development${NC}"
    echo ""
    echo "To run migrations and create admin user, run:"
    echo "  $0 --setup"
}

# Function to setup Django (migrations and admin user)
setup_django() {
    echo -e "${BLUE}=== SETUP MODE ===${NC}"
    
    # Fetch development database URL from AWS
    echo -e "${YELLOW}Fetching development database URL from AWS...${NC}"
    
    echo "Fetching $DEV_PARAM_PATH..."
    DEV_DATABASE_URL=$(get_parameter "$DEV_PARAM_PATH")
    
    if [ -z "$DEV_DATABASE_URL" ]; then
        echo -e "${YELLOW}No dev database URL in AWS, building from local defaults${NC}"
        echo -e "${YELLOW}Enter dev database connection details:${NC}"
        
        read -p "Host (default: localhost): " DEV_DB_HOST
        DEV_DB_HOST=${DEV_DB_HOST:-localhost}
        
        read -p "Port (default: 5432): " DEV_DB_PORT
        DEV_DB_PORT=${DEV_DB_PORT:-5432}
        
        read -p "Database name (default: tally_dev): " DEV_DB_NAME
        DEV_DB_NAME=${DEV_DB_NAME:-tally_dev}
        
        read -p "Username (default: postgres): " DEV_DB_USER
        DEV_DB_USER=${DEV_DB_USER:-postgres}
        
        echo -n "Password: "
        read -s DEV_DB_PASSWORD
        echo ""
        
        DEV_DATABASE_URL="postgresql://${DEV_DB_USER}:${DEV_DB_PASSWORD}@${DEV_DB_HOST}:${DEV_DB_PORT}/${DEV_DB_NAME}"
    fi
    
    echo -e "${GREEN}Using database: $DEV_DATABASE_URL${NC}"
    
    # Ensure we're in the backend directory
    cd "$BACKEND_DIR"
    
    # Run Django migrations
    echo -e "${YELLOW}Running Django migrations...${NC}"
    DATABASE_URL="$DEV_DATABASE_URL" python manage.py migrate
    
    # Create admin user
    echo -e "${YELLOW}Creating/updating admin user (dev@genlayer.foundation)...${NC}"
    
    DATABASE_URL="$DEV_DATABASE_URL" python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from stewards.models import Steward

User = get_user_model()

email = 'dev@genlayer.foundation'
password = 'password'

try:
    user = User.objects.get(email=email)
    print(f"User {email} already exists, updating...")
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.save()
    print(f"User {email} updated successfully")
    
    # Check if user is already a steward
    if not Steward.objects.filter(user=user).exists():
        Steward.objects.create(user=user)
        print(f"Steward record created for {email}")
    else:
        print(f"User {email} is already a steward")
        
except User.DoesNotExist:
    print(f"Creating new user {email}...")
    user = User.objects.create_user(
        email=email,
        password=password,
        is_superuser=True,
        is_staff=True,
        is_active=True
    )
    print(f"User {email} created successfully")
    
    # Create steward record
    Steward.objects.create(user=user)
    print(f"Steward record created for {email}")

print(f"\nAdmin User Details:")
print(f"Email: {email}")
print(f"Password: password")
print(f"Is Steward: {Steward.objects.filter(user=user).exists()}")
print(f"Is Superuser: {user.is_superuser}")
print(f"Is Staff: {user.is_staff}")
EOF
    
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo "Admin user credentials:"
    echo "  Email: dev@genlayer.foundation"
    echo "  Password: password"
}

# Main execution
check_required_tools

case $MODE in
    download)
        download_production
        ;;
    upload)
        upload_to_development
        ;;
    setup)
        setup_django
        ;;
    all)
        download_production
        echo ""
        upload_to_development
        echo ""
        setup_django
        echo ""
        echo -e "${GREEN}=== Full Migration Complete ===${NC}"
        ;;
esac