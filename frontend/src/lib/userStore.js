import { writable, get } from 'svelte/store';
import { getCurrentUser } from './api';

// Create the user store
function createUserStore() {
  const { subscribe, set, update } = writable({
    user: null,
    loading: false,
    error: null
  });
  let loadUserPromise = null;

  return {
    subscribe,
    
    // Load user data from API
    async loadUser() {
      if (loadUserPromise) {
        return loadUserPromise;
      }

      update(state => ({ ...state, loading: true, error: null }));

      loadUserPromise = (async () => {
        try {
          const userData = await getCurrentUser();
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
      update(state => ({
        ...state,
        user: userData,
        error: null
      }));
    },
    
    // Clear user data (on logout)
    clearUser() {
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
