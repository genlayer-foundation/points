# Error Handling Guide

This guide explains how to properly handle errors in the Points application for better user experience and debugging.

## Overview

The application implements three levels of error handling:

1. **Global Error Boundary** - Catches component render errors
2. **API Error Handling** - Handles fetch failures with retry logic
3. **User-Facing Errors** - Displays user-friendly error messages

---

## 1. Global Error Boundary

The `ErrorBoundary.svelte` component wraps the entire app and catches any unhandled component errors.

### Usage

In `App.svelte`:

```svelte
<script>
  import ErrorBoundary from './components/ErrorBoundary.svelte';
</script>

<ErrorBoundary>
  <Router />
</ErrorBoundary>
```

### Features

- Displays user-friendly error message
- Provides "Try Again" button to reset error state
- Shows error details for debugging (in console)
- Graceful fallback UI when errors occur

---

## 2. API Error Handling Utilities

Import from `src/utils/errorHandling.js`:

### fetchWithRetry()

Fetches data with automatic retry logic and timeout handling.

```svelte
<script>
  import { fetchWithRetry, formatErrorMessage } from '../utils/errorHandling.js';

  let data = $state(null);
  let error = $state('');
  let isLoading = $state(false);

  async function loadData() {
    isLoading = true;
    error = '';
    
    try {
      const response = await fetchWithRetry('/api/data');
      data = await response.json();
    } catch (err) {
      error = formatErrorMessage(err, 'Failed to load data');
    } finally {
      isLoading = false;
    }
  }
</script>

<!-- Template -->
{#if isLoading}
  <div>Loading...</div>
{:else if error}
  <div class="error-message">
    <p>{error}</p>
    <button onclick={loadData}>Retry</button>
  </div>
{:else}
  <!-- Display data -->
  {#each data as item}
    <div>{item.name}</div>
  {/each}
{/if}
```

**Features:**
- Automatic retry with exponential backoff (500ms, 1s, 2s)
- 10-second request timeout
- Max 3 retries by default
- Skips retry on client errors (4xx)

### formatErrorMessage()

Converts error objects into user-friendly messages.

```svelte
import { formatErrorMessage } from '../utils/errorHandling.js';

try {
  const response = await fetch('/api/data');
} catch (error) {
  const message = formatErrorMessage(error);
  // Output: "Unable to connect. Please check your internet connection."
  // or: "Request took too long. Please try again."
  // or: "An error occurred while loading data. Please try again."
}
```

**Supported Error Types:**
- Network errors → "Unable to connect..."
- Timeout errors → "Request took too long..."
- 401 Unauthorized → "You are not logged in..."
- 403 Forbidden → "You do not have permission..."
- 404 Not Found → "The resource was not found..."
- 500 Server Error → "Server error..."
- Unknown errors → Custom default message

### Logging Utilities

Use these for consistent debug logging:

```svelte
import { logError, logWarn, logInfo } from '../utils/errorHandling.js';

logError('Failed to load missions', error);
logWarn('Retrying failed request', { attempt: 2 });
logInfo('Data loaded successfully', data);
```

Output in console:
```
[v0] Failed to load missions {error}
[v0] Retrying failed request {attempt: 2}
[v0] Data loaded successfully {data}
```

---

## 3. Complete Component Example

Here's a complete example of proper error handling in a component:

```svelte
<script>
  import { fetchWithRetry, formatErrorMessage } from '../utils/errorHandling.js';

  let isLoading = $state(false);
  let error = $state('');
  let data = $state(null);
  let retryCount = $state(0);
  const maxRetries = 3;

  async function loadData() {
    isLoading = true;
    error = '';
    
    try {
      const response = await fetchWithRetry('/api/my-data');
      data = await response.json();
      retryCount = 0; // Reset on success
    } catch (err) {
      console.error('Failed to load data:', err);
      error = formatErrorMessage(err, 'Failed to load data');
      retryCount++;
    } finally {
      isLoading = false;
    }
  }

  function handleRetry() {
    if (retryCount >= maxRetries) {
      error = 'Maximum retries exceeded. Please try again later.';
      return;
    }
    loadData();
  }

  onMount(() => {
    loadData();
  });
</script>

<div class="component">
  {#if isLoading}
    <div class="spinner">Loading...</div>
  {:else if error}
    <div class="error-alert">
      <div class="error-icon">⚠️</div>
      <p>{error}</p>
      {#if retryCount < maxRetries}
        <button class="retry-btn" onclick={handleRetry}>
          Try Again
        </button>
      {/if}
    </div>
  {:else if data}
    <!-- Render data -->
    <div>
      {#each data as item}
        <div>{item.name}</div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .error-alert {
    background: #fee;
    border: 1px solid #fcc;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }

  .retry-btn {
    margin-top: 12px;
    padding: 8px 16px;
    background: #0066cc;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .spinner {
    text-align: center;
    padding: 24px;
    color: #666;
  }
</style>
```

---

## 4. Best Practices

### DO:
- ✅ Use `fetchWithRetry()` for all API calls
- ✅ Set both `isLoading` and `error` states
- ✅ Show user-friendly error messages
- ✅ Provide retry mechanism to users
- ✅ Use logging utilities for debugging
- ✅ Handle both success and error cases in UI

### DON'T:
- ❌ Use bare `fetch()` without error handling
- ❌ Only `console.error()` without user feedback
- ❌ Show raw error messages to users
- ❌ Leave users in loading state forever
- ❌ Ignore errors silently
- ❌ Mix old localStorage-based error handling with new approach

---

## 5. Migration from Old Error Handling

### Before (Old Way):
```svelte
try {
  const data = await fetch('/api/data');
} catch (error) {
  console.error("Failed to load:", error);
  // User sees nothing - stuck in loading state
}
```

### After (New Way):
```svelte
import { fetchWithRetry, formatErrorMessage } from '../utils/errorHandling.js';

try {
  const response = await fetchWithRetry('/api/data');
  data = await response.json();
} catch (error) {
  error = formatErrorMessage(error);
  // User sees clear error message with retry option
}
```

---

## 6. Related Issues

- **Issue #4**: Add user-facing error handling and retry mechanisms
- **Issue #5**: Add error boundary component to prevent app crashes

See ISSUES.md for detailed issue information.

---

## Support

For questions or improvements to error handling, please refer to:
- GitHub Issues: https://github.com/Endijuan33/points/issues
- ISSUES.md: Local tracking of known issues
