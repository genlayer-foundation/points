#!/bin/bash
set -e

# GitHub Actions IAM Role Setup for Tally Backend Deployment
# This script creates an IAM role that GitHub Actions can assume using OIDC

REPO_OWNER=${1:-"genlayer-foundation"}  # Replace with your GitHub organization/user
REPO_NAME=${2:-"tally"}                  # Replace with your repository name
ENVIRONMENT=${3:-"prod"}                 # GitHub environment: dev or prod
REGION=${AWS_DEFAULT_REGION:-us-east-1}

case "$ENVIRONMENT" in
    dev)
        ROLE_NAME="GitHubActions-TallyBackendDeploy-dev"
        SERVICE_NAME="tally-backend-dev"
        SSM_PREFIX="/tally-backend"
        SSM_ENV="dev"
        INSTANCE_ROLE_NAME="AppRunnerInstanceRole-dev"
        ;;
    prod)
        ROLE_NAME="GitHubActions-TallyBackendDeploy-prod"
        SERVICE_NAME="tally-backend"
        SSM_PREFIX="/tally"
        SSM_ENV="prod"
        INSTANCE_ROLE_NAME="AppRunnerInstanceRole-prod"
        ;;
    *)
        echo "Error: environment must be 'dev' or 'prod'" >&2
        exit 1
        ;;
esac

echo "Setting up GitHub Actions IAM role for $REPO_OWNER/$REPO_NAME environment=$ENVIRONMENT"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create GitHub OIDC provider if it doesn't exist
if ! aws iam get-open-id-connect-provider --open-id-connect-provider-arn arn:aws:iam::$ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com >/dev/null 2>&1; then
    echo "Creating GitHub OIDC provider..."
    aws iam create-open-id-connect-provider \
        --url https://token.actions.githubusercontent.com \
        --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
        --thumbprint-list 1c58a3a8518e8759bf075b76b750d4f2df264fcd \
        --client-id-list sts.amazonaws.com
else
    echo "GitHub OIDC provider already exists"
fi

# Create trust policy for GitHub Actions
cat > github-actions-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Federated": "arn:aws:iam::$ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    "token.actions.githubusercontent.com:sub": "repo:$REPO_OWNER/$REPO_NAME:environment:$ENVIRONMENT"
                }
            }
        }
    ]
}
EOF

# Create IAM role
echo "Creating GitHub Actions IAM role..."
aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file://github-actions-trust-policy.json \
    --description "Role for GitHub Actions to deploy Tally backend to App Runner ($ENVIRONMENT)"

# Create policy for App Runner deployment.
#
# Deliberately scoped:
# - No IAM write actions (CreateRole/AttachRolePolicy/PutRolePolicy): CI being
#   able to edit the App Runner instance-role policy is a privilege-escalation
#   path (e.g. granting itself read access to every SSM secret). The one-time
#   role bootstrap in deploy-apprunner.sh must be run by an administrator.
# - App Runner and ECR mutations are limited to the environment service and
#   repository ARNs; only the List*/GetAuthorizationToken calls that AWS does
#   not support resource-scoping for remain on "*".
# - iam:PassRole is restricted to the two exact App Runner role ARNs. The
#   deployment role has no actions for other services that accept roles.
cat > github-actions-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AppRunnerDeploy",
            "Effect": "Allow",
            "Action": [
                "apprunner:CreateService",
                "apprunner:UpdateService",
                "apprunner:DescribeService"
            ],
            "Resource": "arn:aws:apprunner:$REGION:$ACCOUNT_ID:service/$SERVICE_NAME/*"
        },
        {
            "Sid": "AppRunnerRead",
            "Effect": "Allow",
            "Action": [
                "apprunner:ListServices",
                "apprunner:ListVpcConnectors",
                "apprunner:DescribeVpcConnector"
            ],
            "Resource": "*"
        },
        {
            "Sid": "EcrLogin",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Sid": "EcrPush",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:DescribeRepositories",
                "ecr:CreateRepository",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImage"
            ],
            "Resource": "arn:aws:ecr:$REGION:$ACCOUNT_ID:repository/$SERVICE_NAME"
        },
        {
            "Sid": "ReadAppRunnerRoles",
            "Effect": "Allow",
            "Action": [
                "iam:GetRole"
            ],
            "Resource": [
                "arn:aws:iam::$ACCOUNT_ID:role/$INSTANCE_ROLE_NAME",
                "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerECRAccessRole"
            ]
        },
        {
            "Sid": "PassAppRunnerRoles",
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::$ACCOUNT_ID:role/$INSTANCE_ROLE_NAME",
                "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerECRAccessRole"
            ]
        },
        {
            "Sid": "Identity",
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        },
        {
            "Sid": "GrafanaTokenParameter",
            "Effect": "Allow",
            "Action": [
                "ssm:PutParameter"
            ],
            "Resource": [
                "arn:aws:ssm:$REGION:$ACCOUNT_ID:parameter$SSM_PREFIX/$SSM_ENV/grafana_api_token"
            ]
        }
    ]
}
EOF

# Create and attach policy
aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name TallyBackendDeploymentPolicy \
    --policy-document file://github-actions-policy.json

# Clean up temporary files
rm -f github-actions-trust-policy.json github-actions-policy.json

echo ""
echo "✅ GitHub Actions IAM role created successfully!"
echo ""
echo "Role ARN: arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
echo ""
echo "Next steps:"
echo "1. Add this role ARN to the $ENVIRONMENT GitHub environment as AWS_ROLE_ARN"
echo "2. Update your GitHub Actions workflow to use OIDC authentication"
echo ""
echo "GitHub Repository Settings → Secrets and variables → Actions → Add:"
echo "  AWS_ROLE_ARN = arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"
echo ""
