#!/bin/bash
set -e

# Script to setup dev database with separate user
# Usage: ./setup-dev-database.sh

echo "Setting up tally_dev database..."
echo ""

# Get RDS endpoint from SSM
RDS_HOST=$(aws ssm get-parameter --name "/tally/prod/database_url" --with-decryption --query 'Parameter.Value' --output text | sed 's/.*@\([^:]*\):.*/\1/')
echo "RDS Host: $RDS_HOST"
echo ""

# Prompt for master password
echo -n "Enter RDS master password (postgres user): "
read -s MASTER_PASSWORD
echo ""

# Prompt for dev user password
echo -n "Enter password for new tally_dev user: "
read -s DEV_PASSWORD
echo ""
echo -n "Confirm password for tally_dev user: "
read -s DEV_PASSWORD_CONFIRM
echo ""

if [ "$DEV_PASSWORD" != "$DEV_PASSWORD_CONFIRM" ]; then
    echo "❌ Passwords do not match!"
    exit 1
fi

echo ""
echo "Creating database and user..."

# Create SQL commands
cat > /tmp/create_dev_db.sql << EOF
-- Create dev database and user
CREATE DATABASE tally_dev;
CREATE USER tally_dev WITH PASSWORD '$DEV_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE tally_dev TO tally_dev;

-- Connect to the new database and grant schema permissions
\c tally_dev
GRANT ALL ON SCHEMA public TO tally_dev;
ALTER DATABASE tally_dev OWNER TO tally_dev;
EOF

# Execute SQL
PGPASSWORD=$MASTER_PASSWORD psql -h $RDS_HOST -U postgres -d postgres -f /tmp/create_dev_db.sql

if [ $? -eq 0 ]; then
    echo "✅ Database tally_dev created successfully!"
    echo ""
    
    # Update SSM parameter
    echo "Updating SSM parameter with new database URL..."
    DATABASE_URL="postgresql://tally_dev:${DEV_PASSWORD}@${RDS_HOST}:5432/tally_dev"
    
    aws ssm put-parameter \
        --name "/tally-backend-dev/prod/database_url" \
        --value "$DATABASE_URL" \
        --type SecureString \
        --overwrite \
        --region us-east-1
    
    if [ $? -eq 0 ]; then
        echo "✅ SSM parameter updated successfully!"
    else
        echo "❌ Failed to update SSM parameter"
        echo "You can manually update it with:"
        echo "aws ssm put-parameter --name \"/tally-backend-dev/prod/database_url\" --value \"$DATABASE_URL\" --type SecureString --overwrite"
    fi
else
    echo "❌ Failed to create database"
    exit 1
fi

# Clean up
rm -f /tmp/create_dev_db.sql

echo ""
echo "✅ Dev database setup complete!"
echo ""
echo "Database: tally_dev"
echo "User: tally_dev"
echo "Host: $RDS_HOST"
echo ""
echo "Next step: Deploy backend with:"
echo "  cd backend && ./deploy-apprunner.sh tally-backend-dev"