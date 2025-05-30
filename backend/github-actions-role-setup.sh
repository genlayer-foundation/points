#!/bin/bash
set -e

# GitHub Actions IAM Role Setup for Tally Backend Deployment
# This script creates an IAM role that GitHub Actions can assume using OIDC

REPO_OWNER=${1:-"genlayer-foundation"}  # Replace with your GitHub username
REPO_NAME=${2:-"tally"}                  # Replace with your repository name
REGION=${AWS_DEFAULT_REGION:-us-east-1}

echo "Setting up GitHub Actions IAM role for $REPO_OWNER/$REPO_NAME"

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
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub": "repo:$REPO_OWNER/$REPO_NAME:*"
                }
            }
        }
    ]
}
EOF

# Create IAM role
echo "Creating GitHub Actions IAM role..."
aws iam create-role \
    --role-name GitHubActions-TallyBackendDeploy \
    --assume-role-policy-document file://github-actions-trust-policy.json \
    --description "Role for GitHub Actions to deploy Tally backend to App Runner"

# Create policy for App Runner deployment
cat > github-actions-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "apprunner:CreateService",
                "apprunner:UpdateService",
                "apprunner:DescribeService",
                "apprunner:ListServices",
                "apprunner:ListVpcConnectors",
                "apprunner:DescribeVpcConnector"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
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
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:GetRole",
                "iam:CreateRole",
                "iam:AttachRolePolicy",
                "iam:PutRolePolicy"
            ],
            "Resource": [
                "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerInstanceRole",
                "arn:aws:iam::$ACCOUNT_ID:role/AppRunnerECRAccessRole"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create and attach policy
aws iam put-role-policy \
    --role-name GitHubActions-TallyBackendDeploy \
    --policy-name TallyBackendDeploymentPolicy \
    --policy-document file://github-actions-policy.json

# Clean up temporary files
rm -f github-actions-trust-policy.json github-actions-policy.json

echo ""
echo "✅ GitHub Actions IAM role created successfully!"
echo ""
echo "Role ARN: arn:aws:iam::$ACCOUNT_ID:role/GitHubActions-TallyBackendDeploy"
echo ""
echo "Next steps:"
echo "1. Add this role ARN to your GitHub repository secrets as AWS_ROLE_ARN"
echo "2. Update your GitHub Actions workflow to use OIDC authentication"
echo ""
echo "GitHub Repository Settings → Secrets and variables → Actions → Add:"
echo "  AWS_ROLE_ARN = arn:aws:iam::$ACCOUNT_ID:role/GitHubActions-TallyBackendDeploy"
echo ""
