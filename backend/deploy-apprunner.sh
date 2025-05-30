#!/bin/bash
set -e

# AWS App Runner Deployment Script (Simple - no VPC connector)
# Usage: ./deploy-apprunner.sh [service-name]

SERVICE_NAME=${1:-tally-backend}
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Deploying to AWS App Runner: $SERVICE_NAME (no VPC connector)"

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
            "Resource": "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter/tally/*"
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

# Tag and push to ECR
docker tag $SERVICE_NAME:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Create or update App Runner service
if aws apprunner describe-service --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME --region $REGION >/dev/null 2>&1; then
    echo "Updating existing App Runner service..."
    
    # Create update configuration (different structure)
    cat > apprunner-update-config.json << EOF
{
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$ECR_REPO:latest",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "PYTHONPATH": "/app",
          "DJANGO_SETTINGS_MODULE": "tally.settings"
        },
        "RuntimeEnvironmentSecrets": {
          "SECRET_KEY": "/tally/prod/secret_key",
          "DEBUG": "/tally/prod/debug",
          "ALLOWED_HOSTS": "/tally/prod/allowed_hosts",
          "DATABASE_URL": "/tally/prod/database_url",
          "CORS_ALLOWED_ORIGINS": "/tally/prod/csrf_trusted_origins",
          "CSRF_TRUSTED_ORIGINS": "/tally/prod/csrf_trusted_origins",
          "SIWE_DOMAIN": "/tally/prod/siwe_domain",
          "VALIDATOR_CONTRACT_ADDRESS": "/tally/prod/validator_contract_address",
          "VALIDATOR_RPC_URL": "/tally/prod/validator_rpc_url"
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
    
    # Create service configuration (includes ServiceName)
    cat > apprunner-create-config.json << EOF
{
  "ServiceName": "$SERVICE_NAME",
  "SourceConfiguration": {
    "ImageRepository": {
      "ImageIdentifier": "$ECR_REPO:latest",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "PYTHONPATH": "/app",
          "DJANGO_SETTINGS_MODULE": "tally.settings"
        },
        "RuntimeEnvironmentSecrets": {
          "SECRET_KEY": "/tally/prod/secret_key",
          "DEBUG": "/tally/prod/debug",
          "ALLOWED_HOSTS": "/tally/prod/allowed_hosts",
          "DATABASE_URL": "/tally/prod/database_url",
          "CORS_ALLOWED_ORIGINS": "/tally/prod/csrf_trusted_origins",
          "CSRF_TRUSTED_ORIGINS": "/tally/prod/csrf_trusted_origins",
          "SIWE_DOMAIN": "/tally/prod/siwe_domain",
          "VALIDATOR_CONTRACT_ADDRESS": "/tally/prod/validator_contract_address",
          "VALIDATOR_RPC_URL": "/tally/prod/validator_rpc_url"
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


# Wait for App Runner service to be ready
echo "Waiting for App Runner service to be ready..."
while true; do
    STATUS=$(aws apprunner describe-service \
        --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
        --region $REGION \
        --query 'Service.Status' \
        --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$STATUS" = "RUNNING" ]; then
        SERVICE_URL=$(aws apprunner describe-service \
            --service-arn arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME \
            --region $REGION \
            --query 'Service.ServiceUrl' \
            --output text)
        echo "App Runner service is ready!"
        echo "Service URL: https://$SERVICE_URL"
        break
    elif [ "$STATUS" = "CREATE_FAILED" ] || [ "$STATUS" = "DELETE_FAILED" ]; then
        echo "App Runner service creation failed with status: $STATUS"
        exit 1
    else
        echo "App Runner service status: $STATUS. Waiting..."
        sleep 15
    fi
done

echo ""
echo "Next steps:"
echo "1. Add App Runner IP ranges to your RDS security group"
echo "2. Test the connection: curl https://$SERVICE_URL/health/"
echo ""
echo "Deployment completed successfully!"
