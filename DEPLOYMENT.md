# AWS Deployment Instructions

## Architecture Overview
- **Frontend**: Svelte 5 app deployed on AWS Amplify
- **Backend**: Django API deployed on AWS App Runner  
- **Database**: PostgreSQL on AWS RDS

## Quick Deployment Steps

### 1. Create RDS Database
```bash
# Using AWS Console (recommended for first time):
# 1. Go to RDS → Create database
# 2. Choose PostgreSQL, db.t3.micro (free tier)
# 3. Set master username: tallyuser
# 4. Generate password and save it
# 5. Enable public accessibility for initial setup
# 6. Create database
```

### 2. Deploy Backend (App Runner)
```bash
# 1. Push code to GitHub
git add .
git commit -m "Add AWS deployment configuration"
git push origin main

# 2. Create App Runner service:
# - Go to AWS App Runner → Create service
# - Source: GitHub repository
# - Branch: main
# - Build settings: Use apprunner.yaml
# - Service name: tally-backend
```

**Required Environment Variables for App Runner:**
```
DEBUG=False
SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=postgresql://tallyuser:password@your-rds-endpoint:5432/postgres
ALLOWED_HOSTS=your-apprunner-url.amazonaws.com,your-custom-domain.com
FRONTEND_URL=https://main.d1234567890.amplifyapp.com
SIWE_DOMAIN=main.d1234567890.amplifyapp.com
VALIDATOR_CONTRACT_ADDRESS=0x7CceE43964F70CEAEfDED4b8b07410D30d64eC37
VALIDATOR_RPC_URL=https://genlayer-testnet.rpc.caldera.xyz/http
```

### 3. Deploy Frontend (Amplify)
```bash
# 1. Go to AWS Amplify → New app → Host web app
# 2. Connect GitHub repository
# 3. App settings:
#    - App name: tally-frontend
#    - Environment: production
#    - Branch: main
# 4. Build settings: Use amplify.yml (auto-detected)
```

**Required Environment Variables for Amplify:**
```
VITE_API_URL=https://your-apprunner-url.amazonaws.com
VITE_APP_NAME=Tally
```

### 4. Update CORS Settings
After both deployments, update the App Runner environment variables:
```
FRONTEND_URL=https://main.d1234567890.amplifyapp.com
SIWE_DOMAIN=main.d1234567890.amplifyapp.com
```

## Security Configuration

### RDS Security Group
- **Inbound**: PostgreSQL (5432) from App Runner
- **Outbound**: All traffic

### App Runner 
- **Inbound**: HTTP/HTTPS from anywhere
- **Outbound**: All traffic (for RDS and external APIs)

## Post-Deployment

### 1. Verify Database Connection
Check App Runner logs to ensure migrations ran successfully.

### 2. Create Superuser (if needed)
```bash
# From App Runner console, use the built-in terminal:
python manage.py createsuperuser
```

### 3. Test API Endpoints
- Backend health: `https://your-apprunner-url.amazonaws.com/admin/`
- API docs: `https://your-apprunner-url.amazonaws.com/swagger/`

### 4. Test Frontend
- Visit your Amplify URL
- Verify API connection in browser console

## Custom Domain Setup (Optional)

### Backend (App Runner)
1. Go to App Runner → Custom domains
2. Add your API domain (e.g., api.yourdomain.com)
3. Update DNS records as instructed

### Frontend (Amplify)
1. Go to Amplify → Domain management
2. Add your domain (e.g., yourdomain.com)
3. Update DNS records as instructed

## Environment-Specific URLs

Replace these URLs in your configuration:
- `your-apprunner-url.amazonaws.com` → Your actual App Runner URL
- `main.d1234567890.amplifyapp.com` → Your actual Amplify URL
- `your-rds-endpoint` → Your actual RDS endpoint

## Troubleshooting

### Common Issues:
1. **Database connection errors**: Check RDS security groups and DATABASE_URL
2. **CORS errors**: Verify FRONTEND_URL and CORS settings
3. **Build failures**: Check environment variables and build logs
4. **Static files not loading**: Verify whitenoise middleware configuration

### Useful AWS CLI Commands:
```bash
# Check App Runner service status
aws apprunner describe-service --service-arn your-service-arn

# Check RDS instance status  
aws rds describe-db-instances --db-instance-identifier tally-db

# View Amplify app
aws amplify get-app --app-id your-app-id
```