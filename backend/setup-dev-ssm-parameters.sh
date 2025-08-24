#!/bin/bash
set -e

# Script to setup SSM parameters for dev environment
# Usage: ./setup-dev-ssm-parameters.sh
# This copies from /tally/prod to /tally-backend-dev/prod and updates dev-specific values

SOURCE_PREFIX="/tally"
DEST_PREFIX="/tally-backend-dev"
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Setting up SSM parameters for DEV environment..."
echo "Copying from $SOURCE_PREFIX/prod/ to $DEST_PREFIX/prod/"
echo ""

# Complete list of ALL parameters
PARAMETERS=(
    "secret_key"
    "debug"
    "allowed_hosts"
    "database_url"
    "csrf_trusted_origins"
    "siwe_domain"
    "validator_contract_address"
    "validator_rpc_url"
    "allowed_cidr_nets"
    "frontend_url"
    "cloudinary_api_key"
    "cloudinary_api_secret"
    "cloudinary_cloud_name"
)

# Copy each parameter
echo "Step 1: Copying all parameters..."
for param in "${PARAMETERS[@]}"; do
    echo -n "  Copying $param... "
    
    # Get the value from the existing parameter
    VALUE=$(aws ssm get-parameter \
        --name "$SOURCE_PREFIX/prod/$param" \
        --with-decryption \
        --region $REGION \
        --query 'Parameter.Value' \
        --output text 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Check if it's a SecureString
        TYPE=$(aws ssm get-parameter \
            --name "$SOURCE_PREFIX/prod/$param" \
            --region $REGION \
            --query 'Parameter.Type' \
            --output text 2>/dev/null)
        
        # Create the new parameter
        if [ "$TYPE" == "SecureString" ]; then
            aws ssm put-parameter \
                --name "$DEST_PREFIX/prod/$param" \
                --value "$VALUE" \
                --type SecureString \
                --overwrite \
                --region $REGION >/dev/null 2>&1
        else
            aws ssm put-parameter \
                --name "$DEST_PREFIX/prod/$param" \
                --value "$VALUE" \
                --type String \
                --overwrite \
                --region $REGION >/dev/null 2>&1
        fi
        
        if [ $? -eq 0 ]; then
            echo "✓"
        else
            echo "✗ (failed to create)"
        fi
    else
        echo "✗ (source not found)"
    fi
done

echo ""
echo "Step 2: Updating dev-specific parameters..."

# Update dev-specific values
echo -n "  Updating allowed_hosts... "
aws ssm put-parameter \
    --name "$DEST_PREFIX/prod/allowed_hosts" \
    --value "dev-api.points.genlayer.foundation" \
    --type SecureString \
    --overwrite \
    --region $REGION >/dev/null 2>&1 && echo "✓" || echo "✗"

echo -n "  Updating csrf_trusted_origins... "
aws ssm put-parameter \
    --name "$DEST_PREFIX/prod/csrf_trusted_origins" \
    --value "https://dev.points.genlayer.foundation" \
    --type String \
    --overwrite \
    --region $REGION >/dev/null 2>&1 && echo "✓" || echo "✗"

echo -n "  Updating siwe_domain... "
aws ssm put-parameter \
    --name "$DEST_PREFIX/prod/siwe_domain" \
    --value "dev.points.genlayer.foundation" \
    --type SecureString \
    --overwrite \
    --region $REGION >/dev/null 2>&1 && echo "✓" || echo "✗"

echo -n "  Updating frontend_url... "
aws ssm put-parameter \
    --name "$DEST_PREFIX/prod/frontend_url" \
    --value "https://dev.points.genlayer.foundation" \
    --type SecureString \
    --overwrite \
    --region $REGION >/dev/null 2>&1 && echo "✓" || echo "✗"

echo ""
echo "Step 3: Database setup..."
echo ""
echo "IMPORTANT: You need to update the database_url parameter with a dev database!"
echo ""

# Get current database URL to help with update
CURRENT_DB_URL=$(aws ssm get-parameter \
    --name "$SOURCE_PREFIX/prod/database_url" \
    --with-decryption \
    --region $REGION \
    --query 'Parameter.Value' \
    --output text 2>/dev/null)

echo "Current production database URL format:"
echo "  ${CURRENT_DB_URL//:*@/:****@}" # Hide password in output
echo ""
echo "To create and use a dev database:"
echo ""
echo "1. Connect to RDS and create dev database:"
echo "   psql -h [rds-host] -U [master-user] -d postgres"
echo "   CREATE DATABASE tally_dev;"
echo "   GRANT ALL PRIVILEGES ON DATABASE tally_dev TO [existing-user];"
echo ""
echo "2. Update the database_url parameter:"
echo "   aws ssm put-parameter \\"
echo "     --name \"$DEST_PREFIX/prod/database_url\" \\"
echo "     --value \"postgresql://[user]:[pass]@[host]:5432/tally_dev\" \\"
echo "     --type SecureString --overwrite --region $REGION"
echo ""
echo "Replace [user], [pass], and [host] with your actual values."
echo ""
echo "Step 4: Verify all parameters are set..."
echo ""
echo "Parameters created in $DEST_PREFIX/prod/:"
aws ssm get-parameters-by-path \
    --path "$DEST_PREFIX/prod/" \
    --query "Parameters[*].Name" \
    --output text \
    --region $REGION | tr '\t' '\n' | sed "s|$DEST_PREFIX/prod/|  - |"

echo ""
echo "✅ SSM parameter setup complete!"
echo ""
echo "Next steps:"
echo "1. Update the database_url parameter (see instructions above)"
echo "2. Deploy backend: cd backend && ./deploy-apprunner.sh tally-backend-dev"
echo "3. Configure DNS to point dev-api.points.genlayer.foundation to App Runner URL"
echo "4. Deploy frontend to Lightsail for dev.points.genlayer.foundation"