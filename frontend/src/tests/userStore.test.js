import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { userStore } from '../lib/userStore';

// Mock the API
vi.mock('../lib/api', () => ({
  getCurrentUser: vi.fn()
}));

import { getCurrentUser } from '../lib/api';

describe('userStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    userStore.clearUser();
    // Clear all mocks
    vi.clearAllMocks();
  });

  describe('loadUser', () => {
    it('should load user data successfully', async () => {
      const mockUser = {
        id: 1,
        name: 'Test User',
        email: 'test@example.com',
        address: '0x123456789'
      };

      getCurrentUser.mockResolvedValue(mockUser);

      await userStore.loadUser();

      const state = get(userStore);
      expect(state.user).toEqual(mockUser);
      expect(state.loading).toBe(false);
      expect(state.error).toBe(null);
      expect(getCurrentUser).toHaveBeenCalledTimes(1);
    });

    it('should handle loading error', async () => {
      const errorMessage = 'Failed to fetch user';
      getCurrentUser.mockRejectedValue(new Error(errorMessage));

      await expect(userStore.loadUser()).rejects.toThrow(errorMessage);

      const state = get(userStore);
      expect(state.user).toBe(null);
      expect(state.loading).toBe(false);
      expect(state.error).toBe(errorMessage);
    });

    it('should set loading state while fetching', async () => {
      getCurrentUser.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ name: 'User' }), 100))
      );

      const loadPromise = userStore.loadUser();
      
      // Check loading state immediately
      const state = get(userStore);
      expect(state.loading).toBe(true);

      await loadPromise;
      
      // Check loading state after completion
      const finalState = get(userStore);
      expect(finalState.loading).toBe(false);
    });
  });

  describe('updateUser', () => {
    it('should update existing user data', () => {
      // Set initial user
      userStore.setUser({
        id: 1,
        name: 'Original Name',
        email: 'test@example.com',
        address: '0x123'
      });

      // Update only the name
      userStore.updateUser({ name: 'Updated Name' });

      const state = get(userStore);
      expect(state.user.name).toBe('Updated Name');
      expect(state.user.email).toBe('test@example.com');
      expect(state.user.address).toBe('0x123');
    });

    it('should not update if user is null', () => {
      userStore.clearUser();
      userStore.updateUser({ name: 'New Name' });

      const state = get(userStore);
      expect(state.user).toBe(null);
    });

    it('should update multiple fields at once', () => {
      userStore.setUser({
        id: 1,
        name: 'Original Name',
        email: 'test@example.com',
        address: '0x123'
      });

      userStore.updateUser({ 
        name: 'Updated Name',
        email: 'newemail@example.com'
      });

      const state = get(userStore);
      expect(state.user.name).toBe('Updated Name');
      expect(state.user.email).toBe('newemail@example.com');
      expect(state.user.address).toBe('0x123');
    });
  });

  describe('setUser', () => {
    it('should set complete user data', () => {
      const userData = {
        id: 1,
        name: 'Test User',
        email: 'test@example.com',
        address: '0x123456789'
      };

      userStore.setUser(userData);

      const state = get(userStore);
      expect(state.user).toEqual(userData);
      expect(state.error).toBe(null);
    });

    it('should clear error when setting user', () => {
      // Set an error first
      userStore.clearUser();
      getCurrentUser.mockRejectedValue(new Error('Error'));
      userStore.loadUser().catch(() => {}); // Ignore error

      // Now set user
      userStore.setUser({ name: 'User' });

      const state = get(userStore);
      expect(state.error).toBe(null);
    });
  });

  describe('clearUser', () => {
    it('should reset store to initial state', () => {
      // Set some data
      userStore.setUser({
        id: 1,
        name: 'Test User',
        email: 'test@example.com'
      });

      // Clear the store
      userStore.clearUser();

      const state = get(userStore);
      expect(state.user).toBe(null);
      expect(state.loading).toBe(false);
      expect(state.error).toBe(null);
    });
  });

  describe('getUser', () => {
    it('should return current user data non-reactively', () => {
      const userData = {
        id: 1,
        name: 'Test User',
        email: 'test@example.com'
      };

      userStore.setUser(userData);

      const user = userStore.getUser();
      expect(user).toEqual(userData);
    });

    it('should return null when no user is set', () => {
      userStore.clearUser();
      const user = userStore.getUser();
      expect(user).toBe(null);
    });
  });

  describe('subscription', () => {
    it('should notify subscribers when user data changes', () => {
      const callback = vi.fn();
      const unsubscribe = userStore.subscribe(callback);

      // Initial call
      expect(callback).toHaveBeenCalledTimes(1);

      // Update user
      userStore.setUser({ name: 'User 1' });
      expect(callback).toHaveBeenCalledTimes(2);
      expect(callback).toHaveBeenLastCalledWith(
        expect.objectContaining({
          user: { name: 'User 1' }
        })
      );

      // Update again
      userStore.updateUser({ name: 'User 2' });
      expect(callback).toHaveBeenCalledTimes(3);

      // Clear user
      userStore.clearUser();
      expect(callback).toHaveBeenCalledTimes(4);

      unsubscribe();
    });
  });
});