#!/bin/bash
set -e

# AWS App Runner Deployment Script with VPC Connector Support
# 
# Usage: 
#   ./deploy-apprunner.sh [service-name] [vpc-connector-arn]
#
# Examples:
#   # Deploy with VPC connector (recommended for production):
#   ./deploy-apprunner.sh tally-backend arn:aws:apprunner:us-east-1:123456789012:vpcconnector/my-connector
#
#   # Deploy without VPC connector (uses external networking):
#   ./deploy-apprunner.sh tally-backend
#
#   # Update existing deployment (automatically uses existing VPC connector if any):
#   ./deploy-apprunner.sh tally-backend
#
#   # Update and change VPC connector:
#   ./deploy-apprunner.sh tally-backend arn:aws:apprunner:us-east-1:123456789012:vpcconnector/new-connector
#
# Note: This script always forces a new deployment by using timestamped image tags
#
# Prerequisites:
# 1. AWS CLI configured with appropriate permissions
# 2. Docker installed and running
# 3. If using VPC connector: VPC connector must already exist
# 4. Database security group configured to allow App Runner access
# 5. SSM parameters configured for environment variables

SERVICE_NAME=${1:-tally-backend}
VPC_CONNECTOR_ARN=${2:-}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

# Extract SSM parameter prefix from service name (remove -backend suffix)
SSM_PREFIX="/${SERVICE_NAME%-backend}"

if [ -n "$VPC_CONNECTOR_ARN" ]; then
    echo "Deploying to AWS App Runner: $SERVICE_NAME (with VPC connector)"
    echo "VPC Connector: $VPC_CONNECTOR_ARN"
else
    echo "Deploying to AWS App Runner: $SERVICE_NAME (no VPC connector)"
    echo "Note: Database connectivity will use App Runner's external networking"
fi
echo "Using SSM parameter prefix: $SSM_PREFIX"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$SERVICE_NAME"

# Build and push container image
echo "Building Docker image..."
docker build -t $SERVICE_NAME .

# Create ECR repo if it doesn't exist
aws ecr describe-repositories --repository-names $SERVICE_NAME --region $REGION >/dev/null 2>&1 || aws ecr create-repository --repository-name $SERVICE_NAME --region $REGION

# Create IAM role for App Runner if it doesn't exist
if ! aws iam get-role --role-name AppRunnerInstanceRole >/dev/null 2>&1; then
    echo "Creating App Runner IAM role..."
    
    # Create trust policy
    cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "tasks.apprunner.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # Create IAM role
    aws iam create-role \
        --role-name AppRunnerInstanceRole \
        --assume-role-policy-document file://trust-policy.json

    # Create policy for accessing SSM parameters
    cat > ssm-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParameters",
                "ssm:GetParametersByPath"
            ],
            "Resource": "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter$SSM_PREFIX/*"
        }
    ]
}
EOF

    # Create and attach policy
    aws iam put-role-policy \
        --role-name AppRunnerInstanceRole \
        --policy-name SSMParameterAccess \
        --policy-document file://ssm-policy.json

    # Clean up temporary files
    rm -f trust-policy.json ssm-policy.json
    
    echo "Waiting for IAM role to propagate..."
    sleep 10
fi

# Create App Runner access role for ECR if it doesn't exist
if ! aws iam get-role --role-name AppRunnerECRAccessRole >/dev/null 2>&1; then
    echo "Creating App Runner ECR access role..."
    
    # Create trust policy for App Runner service
    cat > ecr-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "build.apprunner.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

    # Create IAM role
    aws iam create-role \
        --role-name AppRunnerECRAccessRole \
        --assume-role-policy-document file://ecr-trust-policy.json

    # Attach AWS managed policy for ECR access
    aws iam attach-role-policy \
        --role-name AppRunnerECRAccessRole \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

    # Clean up temporary files
    rm -f ecr-trust-policy.json
    
    echo "Waiting for ECR access role to propagate..."
    sleep 10
fi

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Tag and push to ECR with timestamp to force new deployment
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag $SERVICE_NAME:latest $ECR_REPO:latest
docker tag $SERVICE_NAME:latest $ECR_REPO:$TIMESTAMP
docker push $ECR_REPO:latest
docker push $ECR_REPO:$TIMESTAMP

echo "Pushed new image with tag: $TIMESTAMP"

# Create or update App Runner service
if aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME --region $REGION >/dev/null 2>&1; then
    echo "Updating existing App Runner service..."
    
    # If no VPC connector provided, try to get it from existing service
    if [ -z "$VPC_CONNECTOR_ARN" ]; then
        EXISTING_VPC_CONNECTOR=$(aws apprunner describe-service \
            --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
            --region $REGION \
            --query 'Service.NetworkConfiguration.EgressConfiguration.VpcConnectorArn' \
            --output text 2>/dev/null)
        
        if [ "$EXISTING_VPC_CONNECTOR" != "None" ] && [ -n "$EXISTING_VPC_CONNECTOR" ]; then
            VPC_CONNECTOR_ARN="$EXISTING_VPC_CONNECTOR"
            echo "Using existing VPC connector: $VPC_CONNECTOR_ARN"
        fi
    fi
    
    # Create update configuration (different structure)
    cat > apprunner-update-config.json << EOF
{
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$ECR_REPO:$TIMESTAMP",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "PYTHONPATH": "/app",
          "DJANGO_SETTINGS_MODULE": "tally.settings"
        },
        "RuntimeEnvironmentSecrets": {
          "SECRET_KEY": "$SSM_PREFIX/prod/secret_key",
          "DEBUG": "$SSM_PREFIX/prod/debug",
          "ALLOWED_HOSTS": "$SSM_PREFIX/prod/allowed_hosts",
          "DATABASE_URL": "$SSM_PREFIX/prod/database_url",
          "CORS_ALLOWED_ORIGINS": "$SSM_PREFIX/prod/csrf_trusted_origins",
          "CSRF_TRUSTED_ORIGINS": "$SSM_PREFIX/prod/csrf_trusted_origins",
          "SIWE_DOMAIN": "$SSM_PREFIX/prod/siwe_domain",
          "VALIDATOR_CONTRACT_ADDRESS": "$SSM_PREFIX/prod/validator_contract_address",
          "VALIDATOR_RPC_URL": "$SSM_PREFIX/prod/validator_rpc_url",
          "ALLOWED_CIDR_NETS": "$SSM_PREFIX/prod/allowed_cidr_nets",
          "CLOUDINARY_CLOUD_NAME": "$SSM_PREFIX/prod/cloudinary_cloud_name",
          "CLOUDINARY_API_KEY": "$SSM_PREFIX/prod/cloudinary_api_key",
          "CLOUDINARY_API_SECRET": "$SSM_PREFIX/prod/cloudinary_api_secret",
          "BACKEND_URL": "$SSM_PREFIX/prod/backend_url",
          "FRONTEND_URL": "$SSM_PREFIX/prod/frontend_url",
          "GITHUB_CLIENT_ID": "$SSM_PREFIX/prod/github_client_id",
          "GITHUB_CLIENT_SECRET": "$SSM_PREFIX/prod/github_client_secret",
          "GITHUB_ENCRYPTION_KEY": "$SSM_PREFIX/prod/github_encryption_key",
          "GITHUB_REPO_TO_STAR": "$SSM_PREFIX/prod/github_repo_to_star",
          "RECAPTCHA_PUBLIC_KEY": "$SSM_PREFIX/prod/recaptcha_public_key",
          "RECAPTCHA_PRIVATE_KEY": "$SSM_PREFIX/prod/recaptcha_private_key"
        },
        "StartCommand": "./startup.sh gunicorn --bind 0.0.0.0:8000 --timeout 180 --workers 2 tally.wsgi:application"
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": false,
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerECRAccessRole"
    }
  },
  "InstanceConfiguration": {
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB",
    "InstanceRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerInstanceRole"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health/",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }$(if [ -n "$VPC_CONNECTOR_ARN" ]; then echo ',
  "NetworkConfiguration": {
    "EgressConfiguration": {
      "EgressType": "VPC",
      "VpcConnectorArn": "'$VPC_CONNECTOR_ARN'"
    }
  }'; fi)
}
EOF
    
    UPDATE_RESULT=$(aws apprunner update-service \
        --region $REGION \
        --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
        --cli-input-json file://apprunner-update-config.json)
    
    echo "$UPDATE_RESULT"
    
    # Check if deployment started
    UPDATE_STATUS=$(echo "$UPDATE_RESULT" | jq -r '.Service.Status')
    echo "Deployment status: $UPDATE_STATUS"
        
    rm -f apprunner-update-config.json
else
    echo "Creating new App Runner service..."
    
    # Create service configuration (includes ServiceName)
    cat > apprunner-create-config.json << EOF
{
  "ServiceName": "$SERVICE_NAME",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$ECR_REPO:$TIMESTAMP",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "PYTHONPATH": "/app",
          "DJANGO_SETTINGS_MODULE": "tally.settings"
        },
        "RuntimeEnvironmentSecrets": {
          "SECRET_KEY": "$SSM_PREFIX/prod/secret_key",
          "DEBUG": "$SSM_PREFIX/prod/debug",
          "ALLOWED_HOSTS": "$SSM_PREFIX/prod/allowed_hosts",
          "DATABASE_URL": "$SSM_PREFIX/prod/database_url",
          "CORS_ALLOWED_ORIGINS": "$SSM_PREFIX/prod/csrf_trusted_origins",
          "CSRF_TRUSTED_ORIGINS": "$SSM_PREFIX/prod/csrf_trusted_origins",
          "SIWE_DOMAIN": "$SSM_PREFIX/prod/siwe_domain",
          "VALIDATOR_CONTRACT_ADDRESS": "$SSM_PREFIX/prod/validator_contract_address",
          "VALIDATOR_RPC_URL": "$SSM_PREFIX/prod/validator_rpc_url",
          "ALLOWED_CIDR_NETS": "$SSM_PREFIX/prod/allowed_cidr_nets",
          "CLOUDINARY_CLOUD_NAME": "$SSM_PREFIX/prod/cloudinary_cloud_name",
          "CLOUDINARY_API_KEY": "$SSM_PREFIX/prod/cloudinary_api_key",
          "CLOUDINARY_API_SECRET": "$SSM_PREFIX/prod/cloudinary_api_secret",
          "BACKEND_URL": "$SSM_PREFIX/prod/backend_url",
          "FRONTEND_URL": "$SSM_PREFIX/prod/frontend_url",
          "GITHUB_CLIENT_ID": "$SSM_PREFIX/prod/github_client_id",
          "GITHUB_CLIENT_SECRET": "$SSM_PREFIX/prod/github_client_secret",
          "GITHUB_ENCRYPTION_KEY": "$SSM_PREFIX/prod/github_encryption_key",
          "GITHUB_REPO_TO_STAR": "$SSM_PREFIX/prod/github_repo_to_star",
          "RECAPTCHA_PUBLIC_KEY": "$SSM_PREFIX/prod/recaptcha_public_key",
          "RECAPTCHA_PRIVATE_KEY": "$SSM_PREFIX/prod/recaptcha_private_key"
        },
        "StartCommand": "./startup.sh gunicorn --bind 0.0.0.0:8000 --timeout 180 --workers 2 tally.wsgi:application"
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": false,
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerECRAccessRole"
    }
  },
  "InstanceConfiguration": {
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB",
    "InstanceRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerInstanceRole"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health/",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }$(if [ -n "$VPC_CONNECTOR_ARN" ]; then echo ',
  "NetworkConfiguration": {
    "EgressConfiguration": {
      "EgressType": "VPC",
      "VpcConnectorArn": "'$VPC_CONNECTOR_ARN'"
    }
  }'; fi)
}
EOF
    
    aws apprunner create-service \
        --region $REGION \
        --cli-input-json file://apprunner-create-config.json
        
    rm -f apprunner-create-config.json
fi


# Get service URL for output
SERVICE_URL=$(aws apprunner describe-service \
    --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
    --region $REGION \
    --query 'Service.ServiceUrl' \
    --output text)

echo ""
echo "🎉 Deployment initiated successfully!"
echo "Service URL: https://$SERVICE_URL"
echo ""
if [ -n "$VPC_CONNECTOR_ARN" ]; then
    echo "✅ Using VPC connector: $VPC_CONNECTOR_ARN"
else
    echo "ℹ️  No VPC connector (using App Runner's external networking)"
fi
echo ""
echo "⏳ Deployment is in progress. Monitor in AWS Console or check status with:"
echo "   aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME"
echo ""
echo "Test when ready: curl https://$SERVICE_URL/health/"
echo "See aws-deployment-guide.md for detailed configuration and update instructions."
