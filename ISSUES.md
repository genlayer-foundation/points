# Known Issues - Points Repository

## Priority 1: Critical Security Issues

### Issue #3: Security - Replace localStorage with server-side session management
- **Status**: Open
- **Severity**: HIGH
- **GitHub Issue**: [#3](https://github.com/Endijuan33/points/issues/3)
- **Description**: Application uses localStorage/sessionStorage for sensitive data (36+ instances in 12+ files)
- **Files Affected**:
  - `frontend/src/App.svelte`
  - `frontend/src/components/AuthButton.svelte`
  - `frontend/src/components/Navbar.svelte`
  - `frontend/src/components/SocialLink.svelte` (16 instances)
  - `frontend/src/components/SystemAlerts.svelte`
  - `frontend/src/routes/SubmitContribution.svelte`
  - `frontend/src/routes/ProgressJourney.svelte`
  - And more...

**Security Concerns**:
1. Data is unencrypted - stored in plaintext
2. XSS vulnerability - JavaScript can access all data
3. No expiration - persists indefinitely
4. Storage quota - limited to 5-10MB
5. Privacy - sensitive user data exposed

**Recommended Solution**:
1. Replace localStorage with HttpOnly cookies (server-side)
2. Replace sessionStorage with in-memory state + API calls
3. Use URL parameters for short-lived data (referral codes)
4. Store user preferences in database

---

## Priority 2: High Impact Bugs

### Issue #1: Remove expired hackathon redirect
- **Status**: Open
- **Severity**: LOW
- **GitHub Issue**: [#1](https://github.com/Endijuan33/points/issues/1)
- **File**: `frontend/src/App.svelte:211`
- **Description**: Temporary TODO code for hackathon redirect (deadline April 1, 2026 has passed)
- **Current Code**:
```svelte
// TODO: Remove after April 1, 2026 — temporarily send referred users to hackathon
if (new Date() < new Date('2026-04-01')) {
  window.location.hash = '#/hackathon';
}
```
- **Action**: Remove the entire conditional block

---

### Issue #2: Fix non-reactive reference in ContributionsList
- **Status**: Open
- **Severity**: MEDIUM
- **GitHub Issue**: [#2](https://github.com/Endijuan33/points/issues/2)
- **File**: `frontend/src/components/ContributionsList.svelte:22`
- **Description**: Svelte warning - reactive reference only captures initial value
- **Current Code**:
```svelte
let localError = $state(externalError);
```
- **Recommended Fix**:
```svelte
let localError = $derived(externalError);
```

---

## Priority 3: User Experience Improvements

### Issue #4: Add user-facing error handling and retry mechanisms
- **Status**: Open
- **Severity**: MEDIUM
- **GitHub Issue**: [#4](https://github.com/Endijuan33/points/issues/4)
- **Description**: Multiple components handle API errors but don't provide user feedback or retry options
- **Affected Components**:
  - `GlobalDashboard.svelte:80` - fetch error handling
  - `SubmitContribution.svelte:159, 201, 207` - mission/type loading errors
  - `RankingsWidget.svelte:136` - rankings fetch error
  - `Community.svelte:51` - load more members error

**Recommended Solution**:
1. Add user-facing error messages
2. Implement retry button/mechanism
3. Add graceful fallback UI
4. Proper loading state management

---

### Issue #5: Add error boundary component to prevent app crashes
- **Status**: Open
- **Severity**: MEDIUM
- **GitHub Issue**: [#5](https://github.com/Endijuan33/points/issues/5)
- **Description**: No global error boundary component - any component error crashes entire app
- **Scope**: Affects all 131+ Svelte components in the app

**Recommended Solution**:
Create `ErrorBoundary.svelte` component that:
1. Catches component render errors
2. Displays user-friendly error message
3. Provides retry mechanism
4. Logs errors for debugging

---

## Summary

| # | Issue | Severity | Type | Status |
|---|-------|----------|------|--------|
| 1 | Expired hackathon TODO | LOW | Cleanup | Open |
| 2 | Non-reactive reference | MEDIUM | Bug | Open |
| 3 | localStorage security | HIGH | Security | Open |
| 4 | Missing error handling | MEDIUM | Enhancement | Open |
| 5 | No error boundary | MEDIUM | Enhancement | Open |

---

## Next Steps

1. ✅ Identify and document all issues (DONE)
2. ⏳ Create fixes and submit PR for each issue
3. ⏳ Review and merge PRs
4. ⏳ Deploy to production
5. ⏳ Monitor for regressions
