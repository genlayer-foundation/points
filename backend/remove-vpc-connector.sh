#!/bin/bash
set -e

# Remove VPC Connector from App Runner Service
SERVICE_NAME=${1:-tally-backend}
REGION=${AWS_DEFAULT_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Removing VPC connector from App Runner service: $SERVICE_NAME"

# Get current service configuration
SERVICE_CONFIG=$(aws apprunner describe-service \
    --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
    --region $REGION \
    --query 'Service.SourceConfiguration' \
    --output json)

# Create update configuration without VPC connector
cat > apprunner-no-vpc-config.json << EOF
{
  "SourceConfiguration": $SERVICE_CONFIG,
  "NetworkConfiguration": {
    "EgressConfiguration": {
      "EgressType": "DEFAULT"
    }
  }
}
EOF

# Update the service
echo "Updating service to remove VPC connector..."
aws apprunner update-service \
    --region $REGION \
    --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
    --cli-input-json file://apprunner-no-vpc-config.json

rm -f apprunner-no-vpc-config.json

echo ""
echo "✅ VPC connector removal initiated!"
echo "⏳ Monitor the update progress with:"
echo "   aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME"