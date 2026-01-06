import { writable, get } from 'svelte/store';
import { getCurrentUser } from './api';

// Create the user store
function createUserStore() {
  const { subscribe, set, update } = writable({
    user: null,
    loading: false,
    error: null
  });

  return {
    subscribe,
    
    // Load user data from API
    async loadUser() {
      update(state => ({ ...state, loading: true, error: null }));
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
        update(state => ({
          ...state,
          user: null,
          loading: false,
          error: err.message || 'Failed to load user data'
        }));
        throw err;
      }
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

// Export singleton instance
export const userStore = createUserStore();

// Helper to get just the user data in components
export function getUserData() {
  let userData = null;
  userStore.subscribe(state => {
    userData = state.user;
  })();
  return userData;
}