# Daily Uptime Job Scheduling in AWS - Investigation and Proposals

## Current Implementation Analysis

### What Currently Exists
The daily uptime job is implemented as a Django management command that generates uptime contributions for all users retroactively from their first uptime contribution to the current date.

**Location**: `backend/contributions/management/commands/add_daily_uptime.py`

**Key Features**:
- Generates daily uptime contributions for all users
- Applies proper multipliers based on contribution date
- Updates leaderboard entries (both global and category-specific)
- Supports dry-run mode for testing
- Prevents duplicate contributions
- Configurable points value (default: 1 point per day)

**Current Triggers**:
1. Manual via Django Admin: `/admin/run-daily-uptime/`
2. Command line: `python manage.py add_daily_uptime`
3. Admin interface button in Contributions section

**Command Options**:
- `--dry-run`: Simulate without making changes
- `--verbose`: Increase output verbosity  
- `--points`: Points per daily contribution (default: 1)
- `--force`: Use default multiplier (1.0) if none exists

## AWS Scheduling Alternatives

### 1. EventBridge + Lambda (Recommended for Serverless)

**Implementation**:
- Create Lambda function to call App Runner endpoint
- Schedule with EventBridge cron expression
- Secure with internal API key

**Pros**:
- Fully serverless, no infrastructure management
- Cost-effective (~$0.20/month for daily execution)
- Native AWS integration with CloudWatch monitoring
- Automatic retries and error handling

**Cons**:
- Requires exposing internal API endpoint
- Lambda cold starts (minimal impact for daily job)
- Need to manage API security

**Setup Code**:
```python
# Lambda function
import boto3
import requests
import os

def lambda_handler(event, context):
    response = requests.post(
        f"{os.environ['APP_RUNNER_URL']}/api/internal/run-uptime",
        headers={'X-Internal-Key': os.environ['INTERNAL_KEY']},
        timeout=300
    )
    return {
        'statusCode': response.status_code,
        'body': response.text
    }
```

### 2. ECS Fargate Scheduled Task

**Implementation**:
- Use same Docker container as App Runner
- Schedule with EventBridge
- Direct VPC access to database

**Pros**:
- Reuses existing Docker image
- Direct database access through VPC
- No code changes needed
- Supports long-running tasks (>15 min)

**Cons**:
- Higher cost (~$3-5/month)
- More complex setup
- Requires task definition maintenance

**Task Definition**:
```json
{
  "family": "tally-daily-uptime",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "networkMode": "awsvpc",
  "containerDefinitions": [{
    "name": "django-uptime",
    "image": "account.dkr.ecr.region.amazonaws.com/tally-backend:latest",
    "command": ["python", "manage.py", "add_daily_uptime", "--verbose"],
    "environment": [
      {"name": "DATABASE_URL", "value": "from-ssm"}
    ]
  }]
}
```

### 3. GitHub Actions (Simplest Implementation)

**Implementation**:
- Scheduled workflow in `.github/workflows/`
- Triggers API endpoint or SSH command
- Version controlled with code

**Pros**:
- No AWS infrastructure needed
- Free tier: 2000 minutes/month
- Easy monitoring and logs in GitHub UI
- Version controlled configuration

**Cons**:
- External dependency on GitHub
- Requires exposing endpoint
- Subject to GitHub outages

**Workflow File**:
```yaml
name: Daily Uptime Update
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Allow manual trigger

jobs:
  update-uptime:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger uptime update
        run: |
          response=$(curl -X POST https://your-app.awsapprunner.com/api/internal/run-uptime \
            -H "X-Internal-Key: ${{ secrets.INTERNAL_API_KEY }}" \
            -w "\n%{http_code}" \
            --fail-with-body)
          echo "Response: $response"
```

### 4. AWS Systems Manager (SSM) Run Command

**Implementation**:
- Requires EC2 instance or hybrid activation
- Schedule with EventBridge or Maintenance Windows

**Pros**:
- Built-in audit trail
- Can run on existing infrastructure
- AWS native solution

**Cons**:
- Not serverless
- Requires persistent compute resource
- Additional EC2 costs

### 5. App Runner Jobs (Future Option)

AWS announced App Runner Jobs for batch processing but not yet available. Would be ideal once released.

## Recommended Implementation Path

### Phase 1: Quick Implementation (GitHub Actions)
1. Add internal endpoint to Django app
2. Create GitHub Actions workflow
3. Store API key in GitHub secrets
4. Monitor for 1-2 weeks

### Phase 2: Production Migration (EventBridge + Lambda)
1. Create Lambda function
2. Set up EventBridge rule
3. Configure CloudWatch alarms
4. Migrate from GitHub Actions

### Required Django Changes

Add internal endpoint:
```python
# backend/api/internal_views.py
from django.http import JsonResponse
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import os
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_POST
def run_daily_uptime(request):
    # Verify internal key
    internal_key = request.headers.get('X-Internal-Key')
    expected_key = os.environ.get('INTERNAL_API_KEY')
    
    if not expected_key or internal_key != expected_key:
        logger.warning('Unauthorized daily uptime attempt')
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        logger.info('Starting daily uptime update via API')
        call_command('add_daily_uptime', '--verbose')
        logger.info('Daily uptime update completed successfully')
        return JsonResponse({
            'status': 'success',
            'message': 'Daily uptime update completed'
        })
    except Exception as e:
        logger.error(f'Daily uptime update failed: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
```

Add URL pattern:
```python
# backend/api/urls.py
urlpatterns = [
    # ... existing patterns
    path('internal/run-uptime/', run_daily_uptime, name='run-daily-uptime'),
]
```

## Security Considerations

1. **API Key Management**:
   - Store in AWS SSM Parameter Store
   - Rotate regularly (quarterly)
   - Use different keys per environment

2. **Network Security**:
   - Restrict endpoint to specific IPs if possible
   - Use AWS WAF for additional protection
   - Monitor for suspicious activity

3. **Monitoring**:
   - Set up CloudWatch alarms for failures
   - Log all execution attempts
   - Alert on multiple failures

## Cost Comparison

| Solution | Monthly Cost | Setup Complexity | Maintenance |
|----------|-------------|------------------|-------------|
| GitHub Actions | Free* | Low | Low |
| EventBridge + Lambda | ~$0.20 | Medium | Low |
| ECS Fargate | ~$3-5 | High | Medium |
| EC2 + SSM | ~$10+ | High | High |

*Free for public repos or within private repo limits

## Monitoring and Alerting

### Metrics to Track
- Execution success/failure rate
- Execution duration
- Number of contributions created
- Database connection issues

### Recommended Alerts
- Job failure (immediate)
- Job duration > 5 minutes (warning)
- No execution in 48 hours (critical)

## Testing Strategy

1. **Local Testing**:
   ```bash
   python manage.py add_daily_uptime --dry-run --verbose
   ```

2. **Staging Environment**:
   - Run with smaller dataset
   - Verify multiplier calculations
   - Check leaderboard updates

3. **Production Rollout**:
   - Start with dry-run via API
   - Monitor first few executions closely
   - Have rollback plan ready

## Next Steps

1. **Immediate** (Week 1):
   - [ ] Add internal API endpoint to Django
   - [ ] Deploy updated App Runner service
   - [ ] Create GitHub Actions workflow
   - [ ] Test in staging environment

2. **Short-term** (Week 2-4):
   - [ ] Monitor execution stability
   - [ ] Set up basic alerting
   - [ ] Document runbook for failures

3. **Long-term** (Month 2+):
   - [ ] Evaluate need for AWS-native solution
   - [ ] Consider Lambda migration if needed
   - [ ] Implement comprehensive monitoring

## Conclusion

For immediate needs, GitHub Actions provides the simplest, most maintainable solution. It requires minimal infrastructure changes and provides good visibility. As the system scales or requires more AWS-native integration, migration to EventBridge + Lambda would be straightforward using the same API endpoint approach.