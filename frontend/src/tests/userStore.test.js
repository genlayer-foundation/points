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

    it('should share one in-flight request across concurrent callers', async () => {
      const mockUser = { id: 1, name: 'Concurrent User' };
      let resolveUser;
      getCurrentUser.mockImplementation(() => new Promise(resolve => {
        resolveUser = resolve;
      }));

      const firstLoad = userStore.loadUser();
      const secondLoad = userStore.loadUser();

      expect(getCurrentUser).toHaveBeenCalledTimes(1);

      resolveUser(mockUser);
      await expect(Promise.all([firstLoad, secondLoad])).resolves.toEqual([mockUser, mockUser]);

      const state = get(userStore);
      expect(state.user).toEqual(mockUser);
      expect(state.loading).toBe(false);
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

  // Every role-gated navigation calls loadUser(). In-flight coalescing only
  // covers overlapping calls, so without a TTL each navigation refetched.
  describe('success-cache TTL', () => {
    const mockUser = { id: 1, name: 'Cached User', address: '0xabc' };

    it('serves sequential loads from cache within the TTL', async () => {
      getCurrentUser.mockResolvedValue(mockUser);

      await userStore.loadUser();
      const second = await userStore.loadUser();
      await userStore.loadUser();

      expect(getCurrentUser).toHaveBeenCalledTimes(1);
      expect(second).toEqual(mockUser);
    });

    it('refetches once the TTL has elapsed', async () => {
      getCurrentUser.mockResolvedValue(mockUser);
      const nowSpy = vi.spyOn(Date, 'now');

      nowSpy.mockReturnValue(1_000_000);
      await userStore.loadUser();
      nowSpy.mockReturnValue(1_000_000 + userStore.USER_CACHE_TTL_MS + 1);
      await userStore.loadUser();

      expect(getCurrentUser).toHaveBeenCalledTimes(2);
      nowSpy.mockRestore();
    });

    it('always refetches with force', async () => {
      getCurrentUser.mockResolvedValue(mockUser);

      await userStore.loadUser();
      await userStore.loadUser({ force: true });

      expect(getCurrentUser).toHaveBeenCalledTimes(2);
    });

    it('does not extend the TTL after a 5xx, and keeps the known user', async () => {
      getCurrentUser.mockResolvedValueOnce(mockUser);
      await userStore.loadUser();

      const serverError = new Error('boom');
      serverError.response = { status: 500 };
      getCurrentUser.mockRejectedValueOnce(serverError);
      await expect(userStore.loadUser({ force: true })).rejects.toThrow('boom');
      expect(get(userStore).user).toEqual(mockUser);

      // The failure must not have refreshed the timestamp, so the next
      // uncached read goes back to the network rather than serving stale data
      // off a TTL the failure extended.
      getCurrentUser.mockResolvedValueOnce(mockUser);
      await userStore.loadUser({ force: true });
      expect(getCurrentUser).toHaveBeenCalledTimes(3);
    });

    it('clears the cache on 401 so the next load refetches', async () => {
      getCurrentUser.mockResolvedValueOnce(mockUser);
      await userStore.loadUser();

      const authError = new Error('unauthenticated');
      authError.response = { status: 401 };
      getCurrentUser.mockRejectedValueOnce(authError);
      await expect(userStore.loadUser({ force: true })).rejects.toThrow('unauthenticated');
      expect(get(userStore).user).toBeNull();

      getCurrentUser.mockResolvedValueOnce(mockUser);
      await userStore.loadUser();
      expect(getCurrentUser).toHaveBeenCalledTimes(3);
    });
  });
});
