#!/bin/bash
set -e

# Script to copy SSM parameters between deployments
# Usage: ./setup-points-ssm-parameters.sh [source-prefix] [dest-prefix]
# Example: ./setup-points-ssm-parameters.sh /tally /points

SOURCE_PREFIX=${1:-/tally}
DEST_PREFIX=${2:-/points}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Setting up SSM parameters for new deployment..."
echo "This script will copy parameters from $SOURCE_PREFIX/prod/ to $DEST_PREFIX/prod/"
echo ""

# List of parameters to copy
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
)

# Copy each parameter
for param in "${PARAMETERS[@]}"; do
    echo -n "Copying $SOURCE_PREFIX/prod/$param to $DEST_PREFIX/prod/$param... "
    
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
echo "SSM parameter setup complete!"
echo ""
echo "Note: You may want to update some parameters for the new deployment:"
echo "  - $DEST_PREFIX/prod/allowed_hosts (if using a different domain)"
echo "  - $DEST_PREFIX/prod/csrf_trusted_origins (if using a different domain)"
echo "  - $DEST_PREFIX/prod/database_url (if using a different database)"
echo ""
echo "To update a parameter, use:"
echo "  aws ssm put-parameter --name $DEST_PREFIX/prod/PARAM_NAME --value 'NEW_VALUE' --overwrite --region $REGION"
echo ""
echo "For SecureString parameters:"
echo "  aws ssm put-parameter --name $DEST_PREFIX/prod/PARAM_NAME --value 'NEW_VALUE' --type SecureString --overwrite --region $REGION"