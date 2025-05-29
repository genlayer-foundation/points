#!/bin/bash
set -e

# AWS Lightsail Container Service Deployment Script
# Usage: ./deploy-lightsail.sh [service-name]

SERVICE_NAME=${1:-tally-backend}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Deploying to AWS Lightsail Container Service: $SERVICE_NAME"

# Check if container service exists, create if it doesn't
if ! aws lightsail get-container-services --service-name $SERVICE_NAME --region $REGION >/dev/null 2>&1; then
    echo "Creating Lightsail container service: $SERVICE_NAME"
    aws lightsail create-container-service \
        --service-name $SERVICE_NAME \
        --power nano \
        --scale 1 \
        --region $REGION
    
    echo "Waiting for container service to be ready..."
    while true; do
        STATE=$(aws lightsail get-container-services --service-name $SERVICE_NAME --region $REGION --query 'containerServices[0].state' --output text)
        if [ "$STATE" = "READY" ]; then
            echo "Container service is ready!"
            break
        elif [ "$STATE" = "FAILED" ]; then
            echo "Container service creation failed!"
            exit 1
        else
            echo "Current state: $STATE. Waiting..."
            sleep 10
        fi
    done
fi

# Build and push container image
echo "Building Docker image..."
docker build -t $SERVICE_NAME .

echo "Pushing to Lightsail..."
# Set correct Docker socket path for Docker Desktop on macOS
export DOCKER_HOST="unix:///Users/rasca/.docker/run/docker.sock"

# Push the image to Lightsail
aws lightsail push-container-image \
    --region $REGION \
    --service-name $SERVICE_NAME \
    --label backend \
    --image $SERVICE_NAME:latest

# Get the latest image URI from Lightsail registry
IMAGE_URI=$(aws lightsail get-container-images \
    --service-name $SERVICE_NAME \
    --region $REGION \
    --query 'containerImages[0].image' \
    --output text)

echo "Latest image: $IMAGE_URI"

# If the query didn't work, construct the image name based on Lightsail format
if [ "$IMAGE_URI" = "None" ] || [ -z "$IMAGE_URI" ]; then
    IMAGE_URI=":$SERVICE_NAME.backend.1"
    echo "Using constructed image URI: $IMAGE_URI"
fi

# Fetch SSM parameters
echo "Fetching SSM parameters..."
SECRET_KEY=$(aws ssm get-parameter --name "/tally/prod/secret_key" --with-decryption --region $REGION --query 'Parameter.Value' --output text)
DEBUG_VALUE=$(aws ssm get-parameter --name "/tally/prod/debug" --with-decryption --region $REGION --query 'Parameter.Value' --output text)
ALLOWED_HOSTS_VALUE=$(aws ssm get-parameter --name "/tally/prod/allowed_hosts" --with-decryption --region $REGION --query 'Parameter.Value' --output text)
DATABASE_URL_VALUE=$(aws ssm get-parameter --name "/tally/prod/database_url" --with-decryption --region $REGION --query 'Parameter.Value' --output text)
CSRF_TRUSTED_ORIGINS_VALUE=$(aws ssm get-parameter --name "/tally/prod/csrf_trusted_origins" --region $REGION --query 'Parameter.Value' --output text)
SIWE_DOMAIN_VALUE=$(aws ssm get-parameter --name "/tally/prod/siwe_domain" --with-decryption --region $REGION --query 'Parameter.Value' --output text)
VALIDATOR_CONTRACT_ADDRESS_VALUE=$(aws ssm get-parameter --name "/tally/prod/validator_contract_address" --with-decryption --region $REGION --query 'Parameter.Value' --output text)
VALIDATOR_RPC_URL_VALUE=$(aws ssm get-parameter --name "/tally/prod/validator_rpc_url" --with-decryption --region $REGION --query 'Parameter.Value' --output text)

# Create deployment configuration
cat > containers.json << EOF
{
  "backend": {
    "image": "$IMAGE_URI",
    "ports": {
      "8000": "HTTP"
    },
    "environment": {
      "PYTHONPATH": "/app",
      "DJANGO_SETTINGS_MODULE": "tally.settings",
      "SECRET_KEY": "$SECRET_KEY",
      "DEBUG": "$DEBUG_VALUE",
      "ALLOWED_HOSTS": "$ALLOWED_HOSTS_VALUE",
      "DATABASE_URL": "$DATABASE_URL_VALUE",
      "CORS_ALLOWED_ORIGINS": "$CSRF_TRUSTED_ORIGINS_VALUE",
      "CSRF_TRUSTED_ORIGINS": "$CSRF_TRUSTED_ORIGINS_VALUE",
      "SIWE_DOMAIN": "$SIWE_DOMAIN_VALUE",
      "VALIDATOR_CONTRACT_ADDRESS": "$VALIDATOR_CONTRACT_ADDRESS_VALUE",
      "VALIDATOR_RPC_URL": "$VALIDATOR_RPC_URL_VALUE"
    }
  }
}
EOF

cat > public-endpoint.json << EOF
{
  "containerName": "backend",
  "containerPort": 8000,
  "healthCheck": {
    "healthyThreshold": 2,
    "unhealthyThreshold": 2,
    "timeoutSeconds": 5,
    "intervalSeconds": 30,
    "path": "/health/",
    "successCodes": "200-499"
  }
}
EOF

# Deploy the containers
echo "Deploying containers..."
aws lightsail create-container-service-deployment \
    --region $REGION \
    --service-name $SERVICE_NAME \
    --containers file://containers.json \
    --public-endpoint file://public-endpoint.json

# Clean up temporary files
rm containers.json public-endpoint.json

echo "Deployment initiated. Check status with:"
echo "aws lightsail get-container-service-deployments --service-name $SERVICE_NAME --region $REGION"