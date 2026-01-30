import { contributionsAPI } from './api.js';

// Cache TTL: 5 minutes
const CACHE_TTL = 5 * 60 * 1000;

// Store for cached missions by query key
const cache = new Map();

// Store for in-flight requests to deduplicate concurrent calls
const pendingRequests = new Map();

/**
 * Normalize params to a consistent cache key
 * @param {Object} params - Query parameters
 * @returns {string} - Normalized cache key
 */
function getCacheKey(params = {}) {
  // Sort params alphabetically and convert to string
  const sortedEntries = Object.entries(params)
    .filter(([_, v]) => v !== undefined && v !== null)
    .sort(([a], [b]) => a.localeCompare(b));
  return JSON.stringify(sortedEntries);
}

/**
 * Check if cached entry is still valid
 * @param {Object} entry - Cache entry with data and timestamp
 * @returns {boolean} - Whether the cache entry is still valid
 */
function isCacheValid(entry) {
  if (!entry) return false;
  return Date.now() - entry.timestamp < CACHE_TTL;
}

/**
 * Get missions with caching and request deduplication
 * @param {Object} params - Query parameters (is_active, category, etc.)
 * @returns {Promise<Array>} - Array of missions
 */
export async function getMissions(params = {}) {
  const cacheKey = getCacheKey(params);

  // Check cache first
  const cached = cache.get(cacheKey);
  if (isCacheValid(cached)) {
    return cached.data;
  }

  // Check if there's already a pending request for this key
  const pending = pendingRequests.get(cacheKey);
  if (pending) {
    // Wait for the existing request instead of making a new one
    return pending;
  }

  // Create new request and store the promise
  const requestPromise = (async () => {
    try {
      const response = await contributionsAPI.getMissions(params);
      const missions = response.data.results || response.data || [];

      // Store in cache
      cache.set(cacheKey, {
        data: missions,
        timestamp: Date.now()
      });

      return missions;
    } finally {
      // Remove from pending requests when done
      pendingRequests.delete(cacheKey);
    }
  })();

  pendingRequests.set(cacheKey, requestPromise);
  return requestPromise;
}

/**
 * Prefetch missions for common queries to warm the cache
 * Call this in parent components to avoid duplicate requests from children
 * @param {Array<Object>} paramsList - Array of param objects to prefetch
 */
export async function prefetchMissions(paramsList) {
  await Promise.all(paramsList.map(params => getMissions(params)));
}

/**
 * Clear the missions cache
 * Useful when missions might have changed (e.g., after admin updates)
 */
export function clearMissionsCache() {
  cache.clear();
}

/**
 * Invalidate a specific cache entry
 * @param {Object} params - Query parameters to invalidate
 */
export function invalidateMissionsCache(params = {}) {
  const cacheKey = getCacheKey(params);
  cache.delete(cacheKey);
}
