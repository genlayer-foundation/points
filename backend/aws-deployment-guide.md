# AWS Deployment Guide for Tally

## Prerequisites
- AWS CLI configured with appropriate permissions
- Docker installed and running
- Environment variables configured in AWS Systems Manager Parameter Store

## Quick Deployment

### Using the deployment script:

**With VPC Connector (Recommended for Production):**
```bash
./deploy-apprunner.sh tally-backend arn:aws:apprunner:us-east-1:123456789012:vpcconnector/my-connector
```

**Without VPC Connector (uses external networking):**
```bash
./deploy-apprunner.sh tally-backend
```

**To update an existing deployment:**
```bash
./deploy-apprunner.sh tally-backend
```
The script will automatically detect and update the existing service, preserving the current VPC connector configuration.

## Manual Setup Guide

## 1. Create RDS Database

### Using AWS CLI:
```bash
# Create DB subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name tally-subnet-group \
    --db-subnet-group-description "Subnet group for Tally database" \
    --subnet-ids subnet-xxxxxx subnet-yyyyyy

# Create RDS PostgreSQL instance
aws rds create-db-instance \
    --db-instance-identifier tally-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --master-username tallyuser \
    --master-user-password YourSecurePassword123! \
    --allocated-storage 20 \
    --db-subnet-group-name tally-subnet-group \
    --vpc-security-group-ids sg-xxxxxxxx \
    --backup-retention-period 7 \
    --storage-encrypted
```

### Using AWS Console:
1. Go to RDS → Create database
2. Choose PostgreSQL
3. Use db.t3.micro for free tier
4. Set master username/password
5. Configure VPC and security groups
6. Enable backup retention

## 2. Create VPC Connector (Recommended for Production)

A VPC connector allows App Runner to securely access resources in your VPC without exposing your database to the internet.

### Create VPC Connector:
```bash
aws apprunner create-vpc-connector \
    --vpc-connector-name tally-vpc-connector \
    --subnets subnet-xxxxxx subnet-yyyyyy \
    --security-groups sg-xxxxxxxx
```

### Or using AWS Console:
1. Go to App Runner → VPC connectors → Create VPC connector
2. Name: tally-vpc-connector
3. Select your VPC
4. Choose private subnets (where your RDS is located)
5. Select security group that can access your RDS

## 3. Configure Environment Variables

Store sensitive configuration in AWS Systems Manager Parameter Store:

```bash
# Required parameters
aws ssm put-parameter --name "/tally/prod/secret_key" --value "your-production-secret-key" --type "SecureString"
aws ssm put-parameter --name "/tally/prod/debug" --value "False" --type "String"
aws ssm put-parameter --name "/tally/prod/database_url" --value "postgresql://username:password@your-rds-endpoint:5432/database_name" --type "SecureString"
aws ssm put-parameter --name "/tally/prod/allowed_hosts" --value "your-domain.com,your-app-runner-url.amazonaws.com" --type "String"
aws ssm put-parameter --name "/tally/prod/csrf_trusted_origins" --value "https://your-domain.com" --type "String"
aws ssm put-parameter --name "/tally/prod/siwe_domain" --value "your-domain.com" --type "String"
aws ssm put-parameter --name "/tally/prod/validator_contract_address" --value "0x7CceE43964F70CEAEfDED4b8b07410D30d64eC37" --type "String"
aws ssm put-parameter --name "/tally/prod/validator_rpc_url" --value "https://genlayer-testnet.rpc.caldera.xyz/http" --type "String"

# reCAPTCHA configuration (required for spam protection)
# Get keys from https://www.google.com/recaptcha/admin
# Select "reCAPTCHA v2" > "I'm not a robot" Checkbox
aws ssm put-parameter --name "/tally/prod/recaptcha_public_key" --value "your-recaptcha-site-key" --type "String"
aws ssm put-parameter --name "/tally/prod/recaptcha_private_key" --value "your-recaptcha-secret-key" --type "SecureString"
```

### For Development Environment

For development/testing, you can use Google's official test keys (these always pass validation):

```bash
# Development environment uses /tally-backend/dev/* prefix
aws ssm put-parameter --name "/tally-backend/dev/recaptcha_public_key" --value "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI" --type "String"
aws ssm put-parameter --name "/tally-backend/dev/recaptcha_private_key" --value "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe" --type "SecureString"
```

**Note:** All other development parameters should also use the `/tally-backend/dev/*` prefix.

## 4. Deploy Django Backend with App Runner

### Using the deployment script (Recommended):
The `deploy-apprunner.sh` script automates the entire deployment process.

### Manual deployment using AWS CLI:
```bash
aws apprunner create-service \
    --service-name tally-backend \
    --source-configuration file://apprunner-source-config.json
```

## 5. Security Group Configuration

### With VPC Connector (Recommended):
**RDS Security Group:**
- Inbound: PostgreSQL (5432) from VPC connector security group or subnets
- Outbound: All traffic

**VPC Connector Security Group:**
- Inbound: All traffic from App Runner (managed automatically)
- Outbound: PostgreSQL (5432) to RDS security group

### Without VPC Connector:
**RDS Security Group:**
- Inbound: PostgreSQL (5432) from App Runner's external IP ranges or 0.0.0.0/0
- Outbound: All traffic

**Note:** When using VPC connector, App Runner accesses your RDS through the VPC's private network. Without VPC connector, App Runner uses external networking to reach your database.

## 6. Database Setup

After App Runner deployment, the migrations will run automatically via the startup script.
If you need to run additional commands:

```bash
# Connect to your App Runner service via AWS console logs
python manage.py createsuperuser
```

## 7. Updating Your Deployment

To update your App Runner service with new code or configuration:

1. **Using the deployment script:**
   ```bash
   # Simple update (preserves existing VPC connector)
   ./deploy-apprunner.sh tally-backend
   
   # Or specify a new/different VPC connector
   ./deploy-apprunner.sh tally-backend arn:aws:apprunner:us-east-1:123456789012:vpcconnector/new-connector
   ```

2. **The script will automatically:**
   - Build and push a new Docker image
   - Detect the existing service and its current VPC connector (if any)
   - Update the service with the new image
   - Preserve existing VPC connector unless a new one is specified
   - Wait for the deployment to complete

3. **To update environment variables:**
   ```bash
   # Update the parameter in SSM
   aws ssm put-parameter --name "/tally/prod/allowed_hosts" --value "new-domain.com,app-runner-url.amazonaws.com" --overwrite
   
   # Then redeploy to pick up the new values
   ./deploy-apprunner.sh tally-backend arn:aws:apprunner:us-east-1:123456789012:vpcconnector/my-connector
   ```

## 8. Custom Domain (Optional)

1. In App Runner console, go to your service
2. Click "Custom domains"
3. Add your domain
4. Update DNS records as instructed
5. Update ALLOWED_HOSTS environment variable