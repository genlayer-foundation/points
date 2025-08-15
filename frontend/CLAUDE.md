# Frontend Quick Reference - Svelte 5 Structure

## 📝 MAINTENANCE INSTRUCTIONS
**IMPORTANT**: Keep this file updated when you:
- Add new routes - update route definitions in "Routes/Pages" section
- Create new components - add to "Components" section with purpose
- Add new API functions - update "API Integration" section
- Create new pages - add to routes and document in "Routes/Pages"
- Change navigation - update "Navigation & Layout" section
- Add new stores or state - update "State Management" section
- Discover new Svelte 5 patterns - add to "Important Notes" section
- Find common issues - add to "Common Issues & Solutions"
- Add environment variables - update "Environment Variables" section

**Quick update checklist:**
```bash
# After making changes, check:
- [ ] New routes added to route definitions?
- [ ] New components documented with location and purpose?
- [ ] New API functions added to api.js section?
- [ ] Navigation changes reflected in Navbar section?
- [ ] New environment variables documented?
- [ ] Svelte 5 specific patterns documented?
```

## ⚠️ CRITICAL: Svelte 5 Runes Mode
**This project uses Svelte 5 with runes mode enabled**
- **NEVER use `export let` for props** - This will cause errors
- **ALWAYS use `$props()` for component props**
- **Use `$state()` for reactive state**

### Correct Prop Usage
```javascript
// ❌ WRONG - Will cause error
export let params = {};

// ✅ CORRECT - Svelte 5 way
let { params = {} } = $props();
```

## Project Structure
```
frontend/src/
├── components/          # Reusable UI components
├── lib/                # Core utilities and API
│   ├── api.js         # API client and endpoints
│   ├── auth.js        # Authentication logic
│   ├── blockchain.js  # Web3/MetaMask integration
│   └── wallet/        # Wallet connection components
├── routes/            # Page components (SPA routes)
├── assets/            # Static assets
├── tests/             # Test files
├── App.svelte         # Main app component with routing
├── main.js            # App entry point
└── styles.css         # Global styles
```

## Key Files & Components

### Navigation & Layout
- **Main App**: `src/App.svelte`
  - Contains route definitions
  - Handles tooltip positioning
  - Manages route changes
- **Navigation**: `src/components/Navbar.svelte`
  - Top navigation bar
  - Auth button integration
  - Profile link (shows when authenticated)
  - Mobile responsive menu
- **Sidebar**: `src/components/Sidebar.svelte`
  - Side navigation (if used)

### Routes/Pages
All routes are defined in `src/App.svelte`:
```javascript
const routes = {
  '/': Dashboard,
  '/contributions': Contributions,
  '/leaderboard': Leaderboard,
  '/validators': Validators,
  '/participant/:address': ParticipantProfile,  // Public profile view
  '/contribution-type/:id': ContributionTypeDetail,
  '/badge/:id': BadgeDetail,
  '/submit-contribution': SubmitContribution,
  '/my-submissions': MySubmissions,
  '/contributions/:id': EditSubmission,
  '/metrics': Metrics,
  '/profile': Profile,  // Edit own profile (authenticated only)
  '*': NotFound
}
```

#### Profile System
- **`/participant/:address`** - Public participant profile (anyone can view)
  - Shows participant stats, contributions, validator status
  - Shows "Edit Profile" button if viewing own profile
- **`/profile`** - Edit profile page (authenticated users only)
  - Only allows editing display name
  - Redirects to public profile after save with success message

### API Integration (`src/lib/api.js`)
- **Base URL**: `VITE_API_URL` env var or `http://localhost:8000`
- **API Base Path**: `/api/v1`
- **Axios instance** with interceptors for auth
- **Main API objects**:
  - `usersAPI` - User management
  - `contributionsAPI` - Contribution CRUD
  - `leaderboardAPI` - Rankings and stats
  - `statsAPI` - Dashboard statistics

### Authentication (`src/lib/auth.js`)
- **Auth Store**: Svelte store `authState`
- **MetaMask Integration**: Sign-In With Ethereum (SIWE)
- **Key Functions**:
  - `connectWallet()` - Connect MetaMask
  - `signInWithEthereum()` - Complete auth flow
  - `verifyAuth()` - Check auth status
  - `logout()` - Sign out
- **Auth Endpoints** (not /api/v1):
  - `/api/auth/nonce/`
  - `/api/auth/login/`
  - `/api/auth/verify/`
  - `/api/auth/logout/`

### User Store (`src/lib/userStore.js`)
- **Central store for logged-in user data**
- **Key Functions**:
  - `loadUser()` - Fetch user data from API
  - `updateUser(updates)` - Partial update of user data
  - `setUser(userData)` - Set full user data
  - `clearUser()` - Clear on logout
- **Auto-managed**: Loaded on login, cleared on logout
- **Reactive**: Updates reflect immediately in all components using `$userStore`

### Components

#### Data Display
- `LeaderboardTable.svelte` - Ranking table
- `ContributionsList.svelte` - List of contributions
- `StatCard.svelte` - Statistics card
- `Badge.svelte` & `BadgeList.svelte` - Badge display
- `ValidatorStatus.svelte` - Validator info
- `Pagination.svelte` - Page navigation

#### User Interaction
- `AuthButton.svelte` - Login/logout dropdown
  - Shows user name or address in button
  - Dropdown menu with:
    - View Public Profile - Goes to `/participant/:address`
    - Edit Profile - Goes to `/profile`
    - Disconnect - Logs out
  - Reactively updates name from `userStore`
- `SubmitContribution.svelte` - Contribution form
- `Profile.svelte` - User profile editing (name only)

### Wallet Integration (`src/lib/wallet/`)
- `WalletProvider.svelte` - Wallet context provider
- `connector.js` - Wallet connection logic

## State Management

### Reactive State (Svelte 5)
```javascript
// State declaration
let count = $state(0);
let user = $state(null);

// Derived state
let doubled = $derived(count * 2);

// Effects
$effect(() => {
  console.log('Count changed:', count);
});
```

### Stores
- `authState` - Authentication state (from auth.js)
- `userStore` - Current logged-in user data (from userStore.js)
  - Automatically loaded on login/auth verification
  - Updates reactively across all components
  - Cleared on logout
- Uses Svelte's writable stores for global state

## Common Patterns

### API Calls
```javascript
import { getCurrentUser, updateUserProfile } from '../lib/api';

// Fetch data
const user = await getCurrentUser();

// Update data
const updated = await updateUserProfile({ name: 'New Name' });
```

### Using User Store
```javascript
import { userStore } from '../lib/userStore';

// In component - reactive access
$: userName = $userStore.user?.name;

// Update user data (after API call)
userStore.updateUser({ name: 'New Name' });

// Load fresh data from API
await userStore.loadUser();
```

### Protected Routes
Check authentication before allowing access:
```javascript
import { authState } from '../lib/auth.js';

if ($authState.isAuthenticated) {
  // Allow access
} else {
  // Redirect to login
}
```

### Error Handling
```javascript
let error = $state('');

try {
  // API call
} catch (err) {
  error = err.message || 'An error occurred';
}
```

## Environment Variables
Set in `.env` file:
- `VITE_API_URL` - Backend API URL

## Common Commands
```bash
# Activate environment (IMPORTANT!)
cd frontend
source ../backend/env/bin/activate

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Preview production build
npm run preview
```

## Testing
- Test files in `src/tests/`
- Setup file: `src/tests/setupTests.js`
- Run with: `npm test`

## Styling
- Tailwind CSS for utility classes
- Global styles in `src/styles.css`
- Component-scoped styles in `<style>` blocks

## Design Guidelines

### Component Card Wrappers
**IMPORTANT**: When using reusable components in pages, do NOT wrap them in additional card containers.

Components like `RecentContributions`, `FeaturedContributions`, `UserContributions`, etc. already include their own styling and structure. Adding wrapper cards creates unnecessary nesting and visual clutter.

```javascript
// ❌ WRONG - Don't wrap components in cards
<div class="bg-white shadow rounded-lg p-6">
  <RecentContributions />
</div>

// ✅ CORRECT - Use components directly
<RecentContributions />

// ✅ CORRECT - Components can have className for spacing
<FeaturedContributions className="mb-6" />
```

The only exception is when you need to group multiple related elements that aren't already in a component.

## Important Notes

### Component Props in Svelte 5
Always destructure props with `$props()`:
```javascript
// Parent component
<ChildComponent name="John" age={30} />

// Child component
let { name, age = 18 } = $props(); // Default value for age
```

### Derived State in Svelte 5
Use `$derived` for computed values:
```javascript
// ❌ WRONG - $: not allowed in runes mode
$: isOwnProfile = user?.id === currentId;

// ✅ CORRECT - Use $derived
let isOwnProfile = $derived(user?.id === currentId);
```

### Event Handling
```javascript
// Use onclick, not on:click in Svelte 5
<button onclick={() => handleClick()}>Click me</button>
```

### Conditional Rendering
```javascript
{#if condition}
  <div>Show this</div>
{:else if otherCondition}
  <div>Show that</div>
{:else}
  <div>Show default</div>
{/if}
```

### List Rendering
```javascript
{#each items as item, index}
  <div>{index}: {item.name}</div>
{/each}
```

## Navigation Functions
```javascript
import { push, location } from 'svelte-spa-router';

// Navigate programmatically
push('/profile');

// Get current location
$location // reactive store with current path
```

## Authentication Flow
1. User clicks "Connect Wallet"
2. MetaMask prompts for connection
3. Frontend gets nonce from backend
4. User signs message with MetaMask
5. Signed message sent to backend
6. Backend verifies and creates session
7. Cookie set for future requests
8. Profile and protected routes accessible

## Common Issues & Solutions

### Issue: Props not working
**Solution**: Use `$props()` instead of `export let`

### Issue: API calls fail with auth
**Solution**: Check session cookie, verify with `/api/auth/verify/`

### Issue: Navigation not working
**Solution**: Use `push()` from svelte-spa-router, not window.location

### Issue: State not reactive
**Solution**: Use `$state()` for reactive variables

## File Creation Guidelines
- Pages go in `src/routes/`
- Reusable components in `src/components/`
- API functions in `src/lib/api.js`
- New API endpoints need both frontend (api.js) and backend implementation