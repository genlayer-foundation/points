import { writable, get } from 'svelte/store';
import { getCurrentUser } from './api';

const USER_CACHE_TTL_MS = 30 * 1000;

// Create the user store
function createUserStore() {
  const { subscribe, set, update } = writable({
    user: null,
    loading: false,
    error: null
  });
  let loadUserPromise = null;
  // Every role-gated navigation calls loadUser(), and in-flight coalescing only
  // covers overlapping calls, so sequential navigation used to refetch every
  // time. Route guards are a UX gate, not a security boundary (the backend
  // enforces permissions on every request), so a short success cache is safe.
  // Pass { force: true } wherever state must be re-read immediately.
  let lastLoadedAt = 0;

  return {
    subscribe,

    USER_CACHE_TTL_MS,

    // Load user data from API
    async loadUser({ force = false } = {}) {
      if (loadUserPromise) {
        return loadUserPromise;
      }

      const state = get({ subscribe });
      if (
        !force
        && state.user
        && Date.now() - lastLoadedAt < USER_CACHE_TTL_MS
      ) {
        return state.user;
      }

      update(state => ({ ...state, loading: true, error: null }));

      loadUserPromise = (async () => {
        try {
          const userData = await getCurrentUser();
          // Only successful loads start the TTL; failures must never extend it.
          lastLoadedAt = Date.now();
          update(state => ({
            ...state,
            user: userData,
            loading: false,
            error: null
          }));
          return userData;
        } catch (err) {
          // Only a definitive auth rejection means "no user". On network/5xx
          // failures keep any previously loaded user so role gating and journey
          // state don't reset while the backend is down.
          const status = err.response?.status;
          const unauthenticated = status === 401 || status === 403;
          update(state => ({
            ...state,
            user: unauthenticated ? null : state.user,
            loading: false,
            error: err.message || 'Failed to load user data'
          }));
          throw err;
        } finally {
          loadUserPromise = null;
        }
      })();

      return loadUserPromise;
    },
    
    // Update user data (partial update)
    updateUser(updates) {
      update(state => ({
        ...state,
        user: state.user ? { ...state.user, ...updates } : null
      }));
    },
    
    // Set full user data
    setUser(userData) {
      lastLoadedAt = Date.now();
      update(state => ({
        ...state,
        user: userData,
        error: null
      }));
    },

    // Clear user data (on logout)
    clearUser() {
      lastLoadedAt = 0;
      set({
        user: null,
        loading: false,
        error: null
      });
    },
    
    // Get current user data (non-reactive)
    getUser() {
      return get(this).user;
    }
  };
}

export const userStore = createUserStore();
