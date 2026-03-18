# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **Do NOT create a public issue** for security vulnerabilities
2. Email security concerns to the GenLayer Foundation team
3. Include detailed steps to reproduce the vulnerability
4. Provide any relevant proof-of-concept code

### What to Include

- Type of vulnerability
- Full path of affected file(s)
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix Timeline**: Depends on severity, typically 30-90 days

## Security Best Practices

### Authentication

The Points system uses Sign-In With Ethereum (SIWE) for authentication:

1. **Nonce Handling**
   - Nonces are generated server-side with cryptographic randomness
   - Nonces expire after 5 minutes
   - Each nonce can only be used once

2. **Session Management**
   - Sessions are stored server-side
   - Session cookies are httpOnly and secure in production
   - Sessions expire after inactivity

3. **Wallet Integration**
   - No private keys are ever transmitted to the server
   - Only signed messages are verified

### API Security

1. **Input Validation**
   - All user inputs are validated and sanitized
   - File uploads are restricted by type and size
   - URLs are validated before storage

2. **Rate Limiting**
   - Consider implementing rate limiting on sensitive endpoints:
     - `/api/auth/nonce/` - Nonce generation
     - `/api/auth/login/` - Login attempts
     - `/api/v1/submissions/` - Submission creation

3. **CORS Configuration**
   - CORS is restricted to known frontend origins
   - Credentials are only allowed for specific origins

### Known Security Considerations

#### Nonce Cleanup

Expired nonces should be periodically cleaned from the database to prevent storage bloat:

```python
# Add to a management command or scheduled task
from django.utils import timezone
from ethereum_auth.models import Nonce

def cleanup_expired_nonces():
    """Remove expired nonces older than 1 hour."""
    cutoff = timezone.now() - timedelta(hours=1)
    Nonce.objects.filter(expires_at__lt=cutoff).delete()
```

#### Email Generation

Auto-generated emails for wallet users follow a predictable pattern. While this doesn't expose any sensitive data, consider:

- Not using these emails for any communication
- Implementing email verification for actual contact

#### Session Fixation

The application regenerates session IDs on login to prevent session fixation attacks.

### Development Security

1. **Environment Variables**
   - Never commit `.env` files
   - Use different secrets for development and production
   - Rotate secrets periodically

2. **Dependencies**
   - Regularly update dependencies
   - Run security audits:
     ```bash
     # Python
     pip-audit
     
     # Node.js
     npm audit
     ```

3. **Code Review**
   - All changes require code review
   - Security-sensitive changes require additional review

### Deployment Security

1. **HTTPS Only**
   - All production traffic must use HTTPS
   - HSTS headers are set

2. **Content Security Policy**
   - Implement appropriate CSP headers
   - Restrict script sources

3. **Database**
   - Use parameterized queries (Django ORM handles this)
   - Regular backups with encryption
   - Principle of least privilege for database users

## Security Checklist for Contributors

Before submitting a PR, ensure:

- [ ] No sensitive data in logs or error messages
- [ ] User inputs are validated on the server
- [ ] Authentication/authorization checks are in place
- [ ] No hardcoded secrets or credentials
- [ ] SQL queries use ORM or parameterized queries
- [ ] File uploads validate content type and size
- [ ] External URLs are validated before use
- [ ] Error messages don't leak implementation details

## Acknowledgments

We appreciate security researchers who responsibly disclose vulnerabilities. Contributors who report valid security issues will be acknowledged (unless they prefer to remain anonymous).
