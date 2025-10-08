#!/bin/bash
set -e

# Deploy script for dev environment - wraps deploy-apprunner.sh with correct environment
# This sets up the environment to use /dev/ path instead of /prod/

SERVICE_NAME="tally-backend-dev"
REGION=${AWS_DEFAULT_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$SERVICE_NAME"
SSM_PREFIX="/tally-backend"
SSM_ENV="dev"  # Use dev environment

echo "Deploying to AWS App Runner: $SERVICE_NAME (DEV environment)"
echo "Using SSM parameters from: $SSM_PREFIX/$SSM_ENV/"
echo ""

# Build and push container image
echo "Building Docker image..."
docker build -t $SERVICE_NAME .

# Create ECR repo if it doesn't exist
aws ecr describe-repositories --repository-names $SERVICE_NAME --region $REGION >/dev/null 2>&1 || \
    aws ecr create-repository --repository-name $SERVICE_NAME --region $REGION

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO

# Tag and push with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag $SERVICE_NAME:latest $ECR_REPO:latest
docker tag $SERVICE_NAME:latest $ECR_REPO:$TIMESTAMP
docker push $ECR_REPO:latest
docker push $ECR_REPO:$TIMESTAMP

echo "Pushed new image with tag: $TIMESTAMP"

# Check if service exists
if aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME --region $REGION >/dev/null 2>&1; then
    echo "Updating existing App Runner service..."
    
    # Update configuration with dev parameters
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
          "SECRET_KEY": "$SSM_PREFIX/$SSM_ENV/secret_key",
          "DEBUG": "$SSM_PREFIX/$SSM_ENV/debug",
          "ALLOWED_HOSTS": "$SSM_PREFIX/$SSM_ENV/allowed_hosts",
          "DATABASE_URL": "$SSM_PREFIX/$SSM_ENV/database_url",
          "CORS_ALLOWED_ORIGINS": "$SSM_PREFIX/$SSM_ENV/csrf_trusted_origins",
          "CSRF_TRUSTED_ORIGINS": "$SSM_PREFIX/$SSM_ENV/csrf_trusted_origins",
          "SIWE_DOMAIN": "$SSM_PREFIX/$SSM_ENV/siwe_domain",
          "VALIDATOR_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/validator_contract_address",
          "VALIDATOR_RPC_URL": "$SSM_PREFIX/$SSM_ENV/validator_rpc_url",
          "ALLOWED_CIDR_NETS": "$SSM_PREFIX/$SSM_ENV/allowed_cidr_nets",
          "CLOUDINARY_CLOUD_NAME": "$SSM_PREFIX/$SSM_ENV/cloudinary_cloud_name",
          "CLOUDINARY_API_KEY": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_key",
          "CLOUDINARY_API_SECRET": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_secret",
          "BACKEND_URL": "$SSM_PREFIX/$SSM_ENV/backend_url",
          "FRONTEND_URL": "$SSM_PREFIX/$SSM_ENV/frontend_url",
          "GITHUB_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/github_client_id",
          "GITHUB_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/github_client_secret",
          "GITHUB_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/github_encryption_key",
          "GITHUB_REPO_TO_STAR": "$SSM_PREFIX/$SSM_ENV/github_repo_to_star"
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
  }
}
EOF
    
    aws apprunner update-service \
        --region $REGION \
        --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
        --cli-input-json file://apprunner-update-config.json
        
    rm -f apprunner-update-config.json
else
    echo "Creating new App Runner service..."
    
    # Create IAM roles if they don't exist
    if ! aws iam get-role --role-name AppRunnerInstanceRole >/dev/null 2>&1; then
        echo "Creating App Runner IAM role..."
        
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
        
        aws iam create-role \
            --role-name AppRunnerInstanceRole \
            --assume-role-policy-document file://trust-policy.json
        
        # Create policy for SSM access
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
            "Resource": [
                "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter$SSM_PREFIX/$SSM_ENV/*",
                "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter/tally/$SSM_ENV/*",
                "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter/tally/prod/*"
            ]
        }
    ]
}
EOF
        
        aws iam put-role-policy \
            --role-name AppRunnerInstanceRole \
            --policy-name SSMParameterAccess \
            --policy-document file://ssm-policy.json
        
        rm -f trust-policy.json ssm-policy.json
        sleep 10
    fi
    
    # Create ECR access role if needed
    if ! aws iam get-role --role-name AppRunnerECRAccessRole >/dev/null 2>&1; then
        echo "Creating App Runner ECR access role..."
        
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
        
        aws iam create-role \
            --role-name AppRunnerECRAccessRole \
            --assume-role-policy-document file://ecr-trust-policy.json
        
        aws iam attach-role-policy \
            --role-name AppRunnerECRAccessRole \
            --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
        
        rm -f ecr-trust-policy.json
        sleep 10
    fi
    
    # Create service configuration
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
          "SECRET_KEY": "$SSM_PREFIX/$SSM_ENV/secret_key",
          "DEBUG": "$SSM_PREFIX/$SSM_ENV/debug",
          "ALLOWED_HOSTS": "$SSM_PREFIX/$SSM_ENV/allowed_hosts",
          "DATABASE_URL": "$SSM_PREFIX/$SSM_ENV/database_url",
          "CORS_ALLOWED_ORIGINS": "$SSM_PREFIX/$SSM_ENV/csrf_trusted_origins",
          "CSRF_TRUSTED_ORIGINS": "$SSM_PREFIX/$SSM_ENV/csrf_trusted_origins",
          "SIWE_DOMAIN": "$SSM_PREFIX/$SSM_ENV/siwe_domain",
          "VALIDATOR_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/validator_contract_address",
          "VALIDATOR_RPC_URL": "$SSM_PREFIX/$SSM_ENV/validator_rpc_url",
          "ALLOWED_CIDR_NETS": "$SSM_PREFIX/$SSM_ENV/allowed_cidr_nets",
          "CLOUDINARY_CLOUD_NAME": "$SSM_PREFIX/$SSM_ENV/cloudinary_cloud_name",
          "CLOUDINARY_API_KEY": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_key",
          "CLOUDINARY_API_SECRET": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_secret",
          "BACKEND_URL": "$SSM_PREFIX/$SSM_ENV/backend_url",
          "FRONTEND_URL": "$SSM_PREFIX/$SSM_ENV/frontend_url",
          "GITHUB_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/github_client_id",
          "GITHUB_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/github_client_secret",
          "GITHUB_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/github_encryption_key",
          "GITHUB_REPO_TO_STAR": "$SSM_PREFIX/$SSM_ENV/github_repo_to_star"
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
  }
}
EOF
    
    aws apprunner create-service \
        --region $REGION \
        --cli-input-json file://apprunner-create-config.json
        
    rm -f apprunner-create-config.json
fi

# Get service URL
SERVICE_URL=$(aws apprunner describe-service \
    --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
    --region $REGION \
    --query 'Service.ServiceUrl' \
    --output text)

echo ""
echo "🎉 DEV Deployment initiated successfully!"
echo "Service URL: https://$SERVICE_URL"
echo ""
echo "⏳ Deployment is in progress. Monitor in AWS Console or check status with:"
echo "   aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME"
echo ""
echo "Configure DNS:"
echo "  dev-api.points.genlayer.foundation → $SERVICE_URL"
echo ""
echo "Test when ready: curl https://$SERVICE_URL/health/"