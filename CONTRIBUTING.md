# Contributing to GenLayer Points

Thank you for your interest in contributing to the GenLayer Points system. This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Making Contributions](#making-contributions)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Security Considerations](#security-considerations)
- [Common Issues](#common-issues)

## Code of Conduct

By participating in this project, you agree to:

- Be respectful and inclusive in all interactions
- Provide constructive feedback
- Focus on the best outcomes for the community
- Report any unacceptable behavior

## Getting Started

### Prerequisites

- **Python 3.8+** - Backend runtime
- **Node.js 16+** - Frontend build tools
- **PostgreSQL** (optional) - Production database (SQLite works for development)
- **Git** - Version control

### Forking and Cloning

1. Fork the repository on GitHub
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/points.git
   cd points
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/genlayer-foundation/points.git
   ```

## Development Setup

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv env

# Activate virtual environment
# On Windows:
env\Scripts\activate
# On macOS/Linux:
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start development server
npm run dev
```

### Environment Variables

#### Backend (.env)

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:5173
SIWE_DOMAIN=localhost:5173
RECAPTCHA_SECRET_KEY=your-recaptcha-secret
```

#### Frontend (.env)

```env
VITE_API_URL=http://localhost:8000
VITE_RECAPTCHA_SITE_KEY=your-recaptcha-site-key
```

## Project Architecture

### Backend (Django REST Framework)

```
backend/
├── api/              # Main API configuration and metrics
├── contributions/    # Contribution tracking system
│   ├── models.py     # ContributionType, Contribution, Evidence
│   ├── views.py      # ViewSets for contributions
│   └── serializers.py
├── ethereum_auth/    # SIWE authentication
├── leaderboard/      # Points and rankings
├── users/            # User management
├── validators/       # Validator profiles
├── builders/         # Builder profiles
├── stewards/         # Steward management
└── tally/            # Django project settings
```

### Frontend (Svelte 5)

```
frontend/
├── src/
│   ├── components/   # Reusable UI components
│   ├── routes/       # Page components
│   ├── lib/          # Utilities and API clients
│   │   ├── api.js    # API endpoint definitions
│   │   ├── auth.js   # Authentication logic
│   │   └── wallet/   # Wallet integration
│   └── assets/       # Static assets
└── public/           # Public files
```

## Making Contributions

### Branch Naming

**Important**: The `dev` branch is the main development branch. Create feature branches from `dev`.

```bash
# Update your local dev branch
git checkout dev
git pull upstream dev

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### Types of Contributions

1. **Bug Fixes** - Fix issues in existing functionality
2. **Features** - Add new functionality
3. **Documentation** - Improve docs, comments, or examples
4. **Tests** - Add or improve test coverage
5. **Performance** - Optimize existing code
6. **Security** - Fix vulnerabilities or improve security

### Finding Issues

- Check the [Issues](https://github.com/genlayer-foundation/points/issues) page
- Look for issues labeled `good first issue` or `help wanted`
- Browse the codebase for `TODO` or `FIXME` comments

## Pull Request Process

### Before Submitting

1. **Sync with upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/dev
   ```

2. **Run tests**:
   ```bash
   # Backend
   cd backend
   python manage.py test

   # Frontend
   cd frontend
   npm test
   ```

3. **Check linting**:
   ```bash
   # Backend
   flake8 .

   # Frontend
   npm run lint
   ```

### PR Guidelines

1. **Target the `dev` branch** - Not `main`
2. **Write clear titles** - Use conventional commits (feat:, fix:, docs:, etc.)
3. **Include description** - Explain what and why
4. **Link issues** - Reference related issues with "Fixes #123"
5. **Keep PRs focused** - One feature or fix per PR
6. **Add tests** - For new functionality
7. **Update docs** - If behavior changes

### Commit Message Format

```
type(scope): subject

body (optional)

footer (optional)
```

**Types**: feat, fix, docs, style, refactor, test, chore

**Examples**:
```
feat(contributions): add evidence URL validation
fix(auth): resolve wallet connection timeout
docs(readme): update setup instructions
```

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints where appropriate
- Document functions with docstrings
- Keep functions focused and small
- Use meaningful variable names

```python
def calculate_points(
    contribution_type: ContributionType,
    base_points: int,
    multiplier: Decimal
) -> int:
    """
    Calculate frozen global points for a contribution.
    
    Args:
        contribution_type: The type of contribution
        base_points: Raw points before multiplier
        multiplier: Current multiplier value
        
    Returns:
        Calculated frozen global points
    """
    return int(base_points * multiplier)
```

### JavaScript/Svelte (Frontend)

- Use modern ES6+ syntax
- Follow Svelte 5 runes patterns (`$state`, `$derived`, `$effect`)
- Use meaningful component and variable names
- Keep components focused and reusable

```svelte
<script>
  let count = $state(0);
  let doubled = $derived(count * 2);
  
  function increment() {
    count++;
  }
</script>

<button onclick={increment}>
  Count: {count} (doubled: {doubled})
</button>
```

## Testing Guidelines

### Backend Testing

```python
from django.test import TestCase
from rest_framework.test import APITestCase

class ContributionTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            address='0x1234...'
        )
        
    def test_create_contribution(self):
        response = self.client.post('/api/v1/contributions/', {
            'contribution_type': 1,
            'points': 10
        })
        self.assertEqual(response.status_code, 201)
```

### Frontend Testing

```javascript
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Component from './Component.svelte';

describe('Component', () => {
  it('renders correctly', () => {
    render(Component, { props: { value: 'test' } });
    expect(screen.getByText('test')).toBeInTheDocument();
  });
});
```

## Security Considerations

### Authentication

- Never expose sensitive data in client-side code
- Validate all user inputs on the server
- Use SIWE (Sign-In With Ethereum) for authentication
- Store session data securely

### API Security

- Implement proper permission checks
- Use rate limiting for sensitive endpoints
- Sanitize user inputs to prevent injection
- Validate file uploads and URLs

### Common Vulnerabilities to Avoid

1. **SQL Injection** - Use Django ORM, never raw queries with user input
2. **XSS** - Sanitize user-generated content
3. **CSRF** - Django handles this, ensure it's not disabled
4. **Sensitive Data Exposure** - Don't log or expose private keys

## Common Issues

### Wallet Connection Issues

Multiple wallets installed can cause conflicts. See the wallet detection logic in `frontend/src/components/WalletSelector.svelte` for handling.

### CAPTCHA Validation Fails

Ensure reCAPTCHA keys match between frontend and backend environments.

### Session Authentication Errors

Check CORS and cookie settings if authentication state isn't persisting.

### Database Migration Errors

Always run migrations after pulling new changes:
```bash
python manage.py migrate
```

## Questions?

- Open a [Discussion](https://github.com/genlayer-foundation/points/discussions)
- Join the GenLayer community channels
- Review existing issues and PRs

Thank you for contributing to GenLayer Points!
