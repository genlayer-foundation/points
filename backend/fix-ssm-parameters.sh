#!/bin/bash
set -e

# Script to move SSM parameters from wrong path to correct path
# From: /tally-backend-dev/prod/* 
# To: /tally-backend/dev/*

OLD_PREFIX="/tally-backend-dev/prod"
NEW_PREFIX="/tally-backend/dev"
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Fixing SSM parameter paths..."
echo "Moving from $OLD_PREFIX/* to $NEW_PREFIX/*"
echo ""

# List of all parameters to move
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

# Copy each parameter to the new location
echo "Step 1: Copying parameters to correct location..."
for param in "${PARAMETERS[@]}"; do
    echo -n "  Moving $param... "
    
    # Get the value and type from the old parameter
    VALUE=$(aws ssm get-parameter \
        --name "$OLD_PREFIX/$param" \
        --with-decryption \
        --region $REGION \
        --query 'Parameter.Value' \
        --output text 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        TYPE=$(aws ssm get-parameter \
            --name "$OLD_PREFIX/$param" \
            --region $REGION \
            --query 'Parameter.Type' \
            --output text 2>/dev/null)
        
        # Create at new location
        if [ "$TYPE" == "SecureString" ]; then
            aws ssm put-parameter \
                --name "$NEW_PREFIX/$param" \
                --value "$VALUE" \
                --type SecureString \
                --overwrite \
                --region $REGION >/dev/null 2>&1
        else
            aws ssm put-parameter \
                --name "$NEW_PREFIX/$param" \
                --value "$VALUE" \
                --type String \
                --overwrite \
                --region $REGION >/dev/null 2>&1
        fi
        
        if [ $? -eq 0 ]; then
            # Delete from old location
            aws ssm delete-parameter \
                --name "$OLD_PREFIX/$param" \
                --region $REGION >/dev/null 2>&1
            echo "✓"
        else
            echo "✗ (failed to create at new location)"
        fi
    else
        echo "✗ (not found)"
    fi
done

echo ""
echo "Step 2: Verifying parameters at new location..."
echo "Parameters at $NEW_PREFIX/:"
aws ssm get-parameters-by-path \
    --path "$NEW_PREFIX/" \
    --query "Parameters[*].Name" \
    --output text \
    --region $REGION | tr '\t' '\n' | sed "s|$NEW_PREFIX/|  - |"

echo ""
echo "✅ SSM parameters moved successfully!"
echo ""
echo "The App Runner deployment script will now use the correct path:"
echo "  Service name: tally-backend-dev"
echo "  SSM prefix: /tally-backend/dev"
echo ""
echo "Ready to deploy: ./deploy-apprunner.sh tally-backend-dev"