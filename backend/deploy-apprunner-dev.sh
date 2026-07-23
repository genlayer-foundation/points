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
INSTANCE_ROLE_NAME="AppRunnerInstanceRole-dev"

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

# The deployment identity can use this role but cannot modify its policy.
# An administrator must bootstrap it once for this environment.
if ! aws iam get-role --role-name "$INSTANCE_ROLE_NAME" >/dev/null 2>&1; then
    echo "Creating App Runner IAM role: $INSTANCE_ROLE_NAME"

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
        --role-name "$INSTANCE_ROLE_NAME" \
        --assume-role-policy-document file://trust-policy.json

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
                "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter/tally/$SSM_ENV/*"
            ]
        }
    ]
}
EOF

    aws iam put-role-policy \
        --role-name "$INSTANCE_ROLE_NAME" \
        --policy-name SSMParameterAccess \
        --policy-document file://ssm-policy.json

    rm -f trust-policy.json ssm-policy.json
    echo "Waiting for IAM role to propagate..."
    sleep 10
fi

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
          "DJANGO_SETTINGS_MODULE": "tally.settings",
          "RECAPTCHA_ALLOW_TEST_KEYS": "true"
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
          "ASIMOV_STAKING_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/asimov_staking_contract_address",
          "ASIMOV_FACTORY_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/asimov_factory_contract_address",
          "ASIMOV_EXPLORER_URL": "$SSM_PREFIX/$SSM_ENV/asimov_explorer_url",
          "BRADBURY_STAKING_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/bradbury_staking_contract_address",
          "BRADBURY_FACTORY_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/bradbury_factory_contract_address",
          "BRADBURY_EXPLORER_URL": "$SSM_PREFIX/$SSM_ENV/bradbury_explorer_url",
          "UPTIME_LOOKBACK_DAYS": "$SSM_PREFIX/$SSM_ENV/uptime_lookback_days",
          "VALIDATOR_RPC_URL": "$SSM_PREFIX/$SSM_ENV/validator_rpc_url",
          "ALLOWED_CIDR_NETS": "$SSM_PREFIX/$SSM_ENV/allowed_cidr_nets",
          "CLOUDINARY_CLOUD_NAME": "$SSM_PREFIX/$SSM_ENV/cloudinary_cloud_name",
          "CLOUDINARY_API_KEY": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_key",
          "CLOUDINARY_API_SECRET": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_secret",
          "BACKEND_URL": "$SSM_PREFIX/$SSM_ENV/backend_url",
          "FRONTEND_URL": "$SSM_PREFIX/$SSM_ENV/frontend_url",
          "EMAIL_HOST": "$SSM_PREFIX/$SSM_ENV/email_host",
          "EMAIL_PORT": "$SSM_PREFIX/$SSM_ENV/email_port",
          "EMAIL_USE_TLS": "$SSM_PREFIX/$SSM_ENV/email_use_tls",
          "EMAIL_HOST_USER": "$SSM_PREFIX/$SSM_ENV/email_host_user",
          "EMAIL_HOST_PASSWORD": "$SSM_PREFIX/$SSM_ENV/email_host_password",
          "DEFAULT_FROM_EMAIL": "$SSM_PREFIX/$SSM_ENV/default_from_email",
          "TURNSTILE_SECRET_KEY": "$SSM_PREFIX/$SSM_ENV/turnstile_secret_key",
          "TURNSTILE_ALLOWED_HOSTNAMES": "$SSM_PREFIX/$SSM_ENV/turnstile_allowed_hostnames",
          "EMAIL_VERIFICATION_HMAC_KEY": "$SSM_PREFIX/$SSM_ENV/email_verification_hmac_key",
          "EMAIL_VERIFICATION_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/email_verification_encryption_key",
          "GITHUB_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/github_client_id",
          "GITHUB_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/github_client_secret",
          "GITHUB_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/github_encryption_key",
          "GITHUB_REPO_TO_STAR": "$SSM_PREFIX/$SSM_ENV/github_repo_to_star",
          "RECAPTCHA_PUBLIC_KEY": "$SSM_PREFIX/$SSM_ENV/recaptcha_public_key",
          "RECAPTCHA_PRIVATE_KEY": "$SSM_PREFIX/$SSM_ENV/recaptcha_private_key",
          "CRON_SYNC_TOKEN": "$SSM_PREFIX/$SSM_ENV/cron_sync_validators",
          "GRAFANA_API_TOKEN": "$SSM_PREFIX/$SSM_ENV/grafana_api_token",
          "DEFILLAMA_FEES_RANK": "$SSM_PREFIX/$SSM_ENV/defillama_fees_rank",
          "DEFILLAMA_FEES_RANK_URL": "$SSM_PREFIX/$SSM_ENV/defillama_fees_rank_url",
          "TELEGRAM_MEMBERS": "$SSM_PREFIX/$SSM_ENV/telegram_members",
          "TELEGRAM_BOT_TOKEN": "$SSM_PREFIX/$SSM_ENV/telegram_bot_token",
          "TELEGRAM_BOT_USERNAME": "$SSM_PREFIX/$SSM_ENV/telegram_bot_username",
          "TELEGRAM_WEBHOOK_SECRET": "$SSM_PREFIX/$SSM_ENV/telegram_webhook_secret",
          "SOCIAL_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/social_encryption_key",
          "TWITTER_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/twitter_client_id",
          "TWITTER_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/twitter_client_secret",
          "SORSA_API_KEY": "$SSM_PREFIX/$SSM_ENV/sorsa_api_key",
          "DISCORD_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/discord_client_id",
          "DISCORD_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/discord_client_secret",
          "DISCORD_BOT_TOKEN": "$SSM_PREFIX/$SSM_ENV/discord_bot_token",
          "DISCORD_GUILD_ID": "$SSM_PREFIX/$SSM_ENV/discord_guild_id",
          "DISCORD_ROLE_SYNC_BATCH_SIZE": "$SSM_PREFIX/$SSM_ENV/discord_role_sync_batch_size",
          "DISCORD_MANUAL_ROLE_SYNC_COOLDOWN_SECONDS": "$SSM_PREFIX/$SSM_ENV/discord_manual_role_sync_cooldown_seconds",
          "DISCORD_ROLE_SUBMISSION_SYNC_GRACE_SECONDS": "$SSM_PREFIX/$SSM_ENV/discord_role_submission_sync_grace_seconds",
          "DISCORD_SYNAPSE_ROLE_ID": "$SSM_PREFIX/$SSM_ENV/discord_synapse_role_id",
          "DISCORD_BRAIN_ROLE_ID": "$SSM_PREFIX/$SSM_ENV/discord_brain_role_id",
          "DISCORD_NEUROCREATIVE_ROLE_ID": "$SSM_PREFIX/$SSM_ENV/discord_neurocreative_role_id",
          "TWITTER_REDIRECT_URI": "$SSM_PREFIX/$SSM_ENV/twitter_redirect_uri",
          "DISCORD_REDIRECT_URI": "$SSM_PREFIX/$SSM_ENV/discord_redirect_uri"
        },
        "StartCommand": "./startup.sh gunicorn --bind 0.0.0.0:8000 --timeout 180 --workers 2 --access-logfile - --error-logfile - --capture-output --log-level info tally.wsgi:application"
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
    "InstanceRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/$INSTANCE_ROLE_NAME"
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
          "DJANGO_SETTINGS_MODULE": "tally.settings",
          "RECAPTCHA_ALLOW_TEST_KEYS": "true"
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
          "ASIMOV_STAKING_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/asimov_staking_contract_address",
          "ASIMOV_FACTORY_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/asimov_factory_contract_address",
          "ASIMOV_EXPLORER_URL": "$SSM_PREFIX/$SSM_ENV/asimov_explorer_url",
          "BRADBURY_STAKING_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/bradbury_staking_contract_address",
          "BRADBURY_FACTORY_CONTRACT_ADDRESS": "$SSM_PREFIX/$SSM_ENV/bradbury_factory_contract_address",
          "BRADBURY_EXPLORER_URL": "$SSM_PREFIX/$SSM_ENV/bradbury_explorer_url",
          "UPTIME_LOOKBACK_DAYS": "$SSM_PREFIX/$SSM_ENV/uptime_lookback_days",
          "VALIDATOR_RPC_URL": "$SSM_PREFIX/$SSM_ENV/validator_rpc_url",
          "ALLOWED_CIDR_NETS": "$SSM_PREFIX/$SSM_ENV/allowed_cidr_nets",
          "CLOUDINARY_CLOUD_NAME": "$SSM_PREFIX/$SSM_ENV/cloudinary_cloud_name",
          "CLOUDINARY_API_KEY": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_key",
          "CLOUDINARY_API_SECRET": "$SSM_PREFIX/$SSM_ENV/cloudinary_api_secret",
          "BACKEND_URL": "$SSM_PREFIX/$SSM_ENV/backend_url",
          "FRONTEND_URL": "$SSM_PREFIX/$SSM_ENV/frontend_url",
          "EMAIL_HOST": "$SSM_PREFIX/$SSM_ENV/email_host",
          "EMAIL_PORT": "$SSM_PREFIX/$SSM_ENV/email_port",
          "EMAIL_USE_TLS": "$SSM_PREFIX/$SSM_ENV/email_use_tls",
          "EMAIL_HOST_USER": "$SSM_PREFIX/$SSM_ENV/email_host_user",
          "EMAIL_HOST_PASSWORD": "$SSM_PREFIX/$SSM_ENV/email_host_password",
          "DEFAULT_FROM_EMAIL": "$SSM_PREFIX/$SSM_ENV/default_from_email",
          "TURNSTILE_SECRET_KEY": "$SSM_PREFIX/$SSM_ENV/turnstile_secret_key",
          "TURNSTILE_ALLOWED_HOSTNAMES": "$SSM_PREFIX/$SSM_ENV/turnstile_allowed_hostnames",
          "EMAIL_VERIFICATION_HMAC_KEY": "$SSM_PREFIX/$SSM_ENV/email_verification_hmac_key",
          "EMAIL_VERIFICATION_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/email_verification_encryption_key",
          "GITHUB_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/github_client_id",
          "GITHUB_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/github_client_secret",
          "GITHUB_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/github_encryption_key",
          "GITHUB_REPO_TO_STAR": "$SSM_PREFIX/$SSM_ENV/github_repo_to_star",
          "RECAPTCHA_PUBLIC_KEY": "$SSM_PREFIX/$SSM_ENV/recaptcha_public_key",
          "RECAPTCHA_PRIVATE_KEY": "$SSM_PREFIX/$SSM_ENV/recaptcha_private_key",
          "CRON_SYNC_TOKEN": "$SSM_PREFIX/$SSM_ENV/cron_sync_validators",
          "GRAFANA_API_TOKEN": "$SSM_PREFIX/$SSM_ENV/grafana_api_token",
          "DEFILLAMA_FEES_RANK": "$SSM_PREFIX/$SSM_ENV/defillama_fees_rank",
          "DEFILLAMA_FEES_RANK_URL": "$SSM_PREFIX/$SSM_ENV/defillama_fees_rank_url",
          "TELEGRAM_MEMBERS": "$SSM_PREFIX/$SSM_ENV/telegram_members",
          "TELEGRAM_BOT_TOKEN": "$SSM_PREFIX/$SSM_ENV/telegram_bot_token",
          "TELEGRAM_BOT_USERNAME": "$SSM_PREFIX/$SSM_ENV/telegram_bot_username",
          "TELEGRAM_WEBHOOK_SECRET": "$SSM_PREFIX/$SSM_ENV/telegram_webhook_secret",
          "SOCIAL_ENCRYPTION_KEY": "$SSM_PREFIX/$SSM_ENV/social_encryption_key",
          "TWITTER_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/twitter_client_id",
          "TWITTER_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/twitter_client_secret",
          "SORSA_API_KEY": "$SSM_PREFIX/$SSM_ENV/sorsa_api_key",
          "DISCORD_CLIENT_ID": "$SSM_PREFIX/$SSM_ENV/discord_client_id",
          "DISCORD_CLIENT_SECRET": "$SSM_PREFIX/$SSM_ENV/discord_client_secret",
          "DISCORD_BOT_TOKEN": "$SSM_PREFIX/$SSM_ENV/discord_bot_token",
          "DISCORD_GUILD_ID": "$SSM_PREFIX/$SSM_ENV/discord_guild_id",
          "DISCORD_ROLE_SYNC_BATCH_SIZE": "$SSM_PREFIX/$SSM_ENV/discord_role_sync_batch_size",
          "DISCORD_MANUAL_ROLE_SYNC_COOLDOWN_SECONDS": "$SSM_PREFIX/$SSM_ENV/discord_manual_role_sync_cooldown_seconds",
          "DISCORD_ROLE_SUBMISSION_SYNC_GRACE_SECONDS": "$SSM_PREFIX/$SSM_ENV/discord_role_submission_sync_grace_seconds",
          "DISCORD_SYNAPSE_ROLE_ID": "$SSM_PREFIX/$SSM_ENV/discord_synapse_role_id",
          "DISCORD_BRAIN_ROLE_ID": "$SSM_PREFIX/$SSM_ENV/discord_brain_role_id",
          "DISCORD_NEUROCREATIVE_ROLE_ID": "$SSM_PREFIX/$SSM_ENV/discord_neurocreative_role_id",
          "TWITTER_REDIRECT_URI": "$SSM_PREFIX/$SSM_ENV/twitter_redirect_uri",
          "DISCORD_REDIRECT_URI": "$SSM_PREFIX/$SSM_ENV/discord_redirect_uri"
        },
        "StartCommand": "./startup.sh gunicorn --bind 0.0.0.0:8000 --timeout 180 --workers 2 --access-logfile - --error-logfile - --capture-output --log-level info tally.wsgi:application"
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
    "InstanceRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/$INSTANCE_ROLE_NAME"
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
