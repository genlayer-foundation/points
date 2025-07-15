# App Runner NAT Gateway Setup - Session Plan

## Current Status (2025-07-15)

### What We've Done
1. **Created NAT Gateway Infrastructure**:
   - Elastic IP: 54.209.62.141
   - NAT Gateway ID: nat-028dcaac5313dfa39
   - Private Route Table: rtb-00b8729eb3343bcfe
   - Associated all VPC connector subnets with the private route table

2. **Created New VPC Connector**:
   - Name: apprunner-rds-nat
   - ARN: `arn:aws:apprunner:us-east-1:245374728431:vpcconnector/apprunner-rds-nat/1/eab737135a5d4bed9b83d12d1c23699a`
   - Status: ACTIVE
   - Security Group: sg-0fa4b395d4ec5eb41 (new one created for this connector)

3. **Deployments**:
   - `points-backend` exists and is running at: https://2heebnmbkj.us-east-1.awsapprunner.com/
   - SSM parameters copied from /tally/* to /points/*

### The Problem
Both App Runner services (`tally-backend` and `points-backend`) cannot reach external APIs (specifically `genlayer-testnet.rpc.caldera.xyz`) when using VPC connector. The error:
```
Network is unreachable - HTTPSConnectionPool(host='genlayer-testnet.rpc.caldera.xyz', port=443)
```

**Root Cause Identified**: The NAT Gateway was created in subnet-080dc8ee51a2732f0, which is associated with the private route table. This creates a circular dependency - the private subnets route to the NAT Gateway, but the NAT Gateway itself is in a subnet that only has a route back to itself, not to the Internet Gateway.

**Solution**: Create a new NAT Gateway in a public subnet (one that uses the main route table with IGW access).

### What Still Needs to Be Done

1. **Fix NAT Gateway placement** (URGENT):
   ```bash
   cd /Users/rasca/Dev/tally/backend
   ./fix-nat-gateway.sh
   ```

2. **After NAT Gateway is fixed, verify points-backend works**:
   ```bash
   curl https://2heebnmbkj.us-east-1.awsapprunner.com/api/v1/users/validators/
   ```

3. **Update tally-backend to use new VPC connector**:
   ```bash
   ./deploy-apprunner.sh tally-backend arn:aws:apprunner:us-east-1:245374728431:vpcconnector/apprunner-rds-nat/1/eab737135a5d4bed9b83d12d1c23699a
   ```

4. **Test tally-backend connectivity**:
   ```bash
   curl https://yyns22b3pz.us-east-1.awsapprunner.com/api/v1/users/validators/
   ```

5. **Clean up old resources**:
   ```bash
   # Delete old NAT Gateway
   aws ec2 delete-nat-gateway --nat-gateway-id nat-028dcaac5313dfa39
   
   # Delete old VPC connector (if not already deleted)
   aws apprunner delete-vpc-connector \
     --vpc-connector-arn arn:aws:apprunner:us-east-1:245374728431:vpcconnector/apprunner-rds/1/847ca328313049c785c335023851fb72
   ```

### Important Notes
- The NAT Gateway costs ~$45/month plus data transfer fees
- Both services need to be updated to use the new VPC connector
- The old VPC connector should be deleted only after confirming both services work
- Docker seems to have intermittent build issues - may need to restart Docker Desktop

### Alternative Solutions (if NAT Gateway doesn't work)
1. **Remove VPC Connector**: Deploy without VPC connector and add App Runner CIDR to RDS security group
2. **Cache Validator Data**: Store validator data in database and update periodically
3. **Proxy Service**: Deploy a separate service without VPC connector as a proxy

### Useful Commands
```bash
# Check service status
aws apprunner describe-service --service-arn arn:aws:apprunner:us-east-1:245374728431:service/points-backend --query "Service.Status"

# Check recent operations
aws apprunner list-operations --service-arn arn:aws:apprunner:us-east-1:245374728431:service/points-backend --max-results 5

# Check NAT Gateway status
aws ec2 describe-nat-gateways --nat-gateway-ids nat-028dcaac5313dfa39
```