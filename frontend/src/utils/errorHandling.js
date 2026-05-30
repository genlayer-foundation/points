/**
 * Error Handling Utilities
 * Provides standardized error handling, logging, and user feedback
 */

/**
 * Fetch with error handling and retry capability
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options
 * @param {number} maxRetries - Maximum number of retries (default: 2)
 * @returns {Promise<Response>}
 */
export async function fetchWithRetry(url, options = {}, maxRetries = 2) {
  let lastError;

  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      const response = await fetch(url, {
        ...options,
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response;
    } catch (error) {
      lastError = error;
      console.error(`[v0] Fetch attempt ${attempt}/${maxRetries + 1} failed:`, error.message);

      // Don't retry on client errors (4xx)
      if (error instanceof TypeError && error.message.includes('HTTP 4')) {
        throw error;
      }

      // Wait before retrying (exponential backoff)
      if (attempt <= maxRetries) {
        const delayMs = Math.pow(2, attempt - 1) * 500; // 500ms, 1s, 2s...
        await new Promise((resolve) => setTimeout(resolve, delayMs));
      }
    }
  }

  throw lastError;
}

/**
 * Format error message for user display
 * @param {Error} error - Error object
 * @param {string} defaultMessage - Default message if error is unrecognizable
 * @returns {string} User-friendly error message
 */
export function formatErrorMessage(error, defaultMessage = 'Something went wrong') {
  if (!error) return defaultMessage;

  if (typeof error === 'string') return error;

  const message = error.message || '';

  // Network errors
  if (message.includes('Failed to fetch') || message.includes('Network')) {
    return 'Unable to connect. Please check your internet connection.';
  }

  // Timeout errors
  if (message.includes('timeout') || message.includes('Timeout')) {
    return 'Request took too long. Please try again.';
  }

  // HTTP errors
  if (message.includes('HTTP 401')) {
    return 'You are not logged in. Please log in and try again.';
  }
  if (message.includes('HTTP 403')) {
    return 'You do not have permission to access this resource.';
  }
  if (message.includes('HTTP 404')) {
    return 'The requested resource was not found.';
  }
  if (message.includes('HTTP 500')) {
    return 'Server error. Please try again later.';
  }
  if (message.includes('HTTP')) {
    return 'An error occurred while loading data. Please try again.';
  }

  return defaultMessage;
}

/**
 * Logger with [v0] prefix for debugging
 * @param {string} message - Log message
 * @param {any} data - Optional data to log
 */
export function logError(message, data = null) {
  console.error(`[v0] ${message}`, data || '');
}

export function logWarn(message, data = null) {
  console.warn(`[v0] ${message}`, data || '');
}

export function logInfo(message, data = null) {
  console.info(`[v0] ${message}`, data || '');
}

/**
 * Create error state management for components
 * Usage in component:
 * let { error, isLoading, setError, clearError, setLoading } = createErrorState();
 */
export function createErrorState() {
  return {
    error: '',
    isLoading: false,
    retryCount: 0,
    maxRetries: 3,

    setError(message) {
      this.error = message;
    },

    clearError() {
      this.error = '';
    },

    setLoading(loading) {
      this.isLoading = loading;
    },

    canRetry() {
      return this.retryCount < this.maxRetries;
    },

    incrementRetry() {
      this.retryCount++;
    },

    resetRetry() {
      this.retryCount = 0;
    },

    reset() {
      this.error = '';
      this.isLoading = false;
      this.retryCount = 0;
    },
  };
}
