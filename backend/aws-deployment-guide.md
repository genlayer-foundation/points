# AWS Deployment Guide for Tally

## Prerequisites
- AWS CLI configured with appropriate permissions
- Docker installed (for local testing)

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

## 2. Deploy Django Backend with App Runner

### Step 1: Push code to GitHub
```bash
git add .
git commit -m "Add AWS deployment configuration"
git push origin main
```

### Step 2: Create App Runner service
1. Go to AWS App Runner → Create service
2. Source: Repository → GitHub
3. Connect your GitHub account
4. Select your repository and branch
5. Build settings: Use apprunner.yaml
6. Service name: tally-backend
7. Set environment variables:
   - `DEBUG=False`
   - `SECRET_KEY=your-production-secret-key`
   - `DATABASE_URL=postgresql://username:password@your-rds-endpoint:5432/database_name`
   - `ALLOWED_HOSTS=your-app-runner-url.amazonaws.com`
   - `FRONTEND_URL=https://your-amplify-domain.amplifyapp.com`
   - `SIWE_DOMAIN=your-amplify-domain.amplifyapp.com`

### Using AWS CLI:
```bash
aws apprunner create-service \
    --service-name tally-backend \
    --source-configuration file://apprunner-source-config.json
```

## 3. Environment Variables for App Runner

Required environment variables:
- `DEBUG=False`
- `SECRET_KEY=your-production-secret-key`
- `DATABASE_URL=postgresql://username:password@endpoint:5432/dbname`
- `ALLOWED_HOSTS=your-domain.com,your-app-runner-url.amazonaws.com`
- `FRONTEND_URL=https://your-amplify-domain.amplifyapp.com`
- `SIWE_DOMAIN=your-amplify-domain.amplifyapp.com`
- `VALIDATOR_CONTRACT_ADDRESS=0x7CceE43964F70CEAEfDED4b8b07410D30d64eC37`
- `VALIDATOR_RPC_URL=https://genlayer-testnet.rpc.caldera.xyz/http`

## 4. Security Group Configuration

### RDS Security Group:
- Inbound: PostgreSQL (5432) from App Runner security group
- Outbound: All traffic

### App Runner Security Group:
- Inbound: HTTP (80), HTTPS (443) from anywhere
- Outbound: All traffic

## 5. Database Setup

After App Runner deployment, the migrations will run automatically via apprunner.yaml.
If you need to run additional commands:

```bash
# Connect to your App Runner service via AWS console logs or SSH
python manage.py createsuperuser
```

## 6. Custom Domain (Optional)

1. In App Runner console, go to your service
2. Click "Custom domains"
3. Add your domain
4. Update DNS records as instructed
5. Update ALLOWED_HOSTS environment variable