import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte/svelte5';
import { flushSync } from 'svelte';
import AuthButton from '../components/AuthButton.svelte';
import { writable } from 'svelte/store';

// Mock auth functions
vi.mock('../lib/auth', () => {
  const authStateStore = writable({
    isAuthenticated: false,
    address: null,
    loading: false,
    error: null
  });

  return {
    authState: authStateStore,
    signInWithEthereum: vi.fn(),
    logout: vi.fn(),
    verifyAuth: vi.fn()
  };
});

// Mock user store
vi.mock('../lib/userStore', () => {
  const userStoreData = writable({
    user: null,
    loading: false,
    error: null
  });

  return {
    userStore: userStoreData
  };
});

// Mock svelte-spa-router
vi.mock('svelte-spa-router', () => ({
  push: vi.fn()
}));

import { authState, signInWithEthereum, logout, verifyAuth } from '../lib/auth';
import { userStore } from '../lib/userStore';
import { push } from 'svelte-spa-router';

describe('AuthButton Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Reset stores to default state
    authState.set({
      isAuthenticated: false,
      address: null,
      loading: false,
      error: null
    });
    
    userStore.set({
      user: null,
      loading: false,
      error: null
    });

    // Default mock implementations
    verifyAuth.mockResolvedValue(true);
    signInWithEthereum.mockResolvedValue({ success: true });
    logout.mockResolvedValue();
  });

  describe('Unauthenticated State', () => {
    it('should display "Connect Wallet" button when not authenticated', () => {
      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      expect(button.textContent).toContain('Connect Wallet');
    });

    it('should call signInWithEthereum when clicked while unauthenticated', async () => {
      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      
      await fireEvent.click(button);
      
      expect(signInWithEthereum).toHaveBeenCalledTimes(1);
    });

    it('should verify auth on mount', async () => {
      render(AuthButton);
      
      await waitFor(() => {
        expect(verifyAuth).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe('Authenticated State', () => {
    beforeEach(() => {
      authState.set({
        isAuthenticated: true,
        address: '0x1234567890abcdef',
        loading: false,
        error: null
      });
    });

    it('should display truncated address when authenticated without name', () => {
      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      expect(button.textContent).toContain('0x1234...cdef');
    });

    it('should display user name when available', () => {
      userStore.set({
        user: { 
          name: 'John Doe',
          address: '0x1234567890abcdef'
        },
        loading: false,
        error: null
      });

      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      expect(button.textContent).toContain('John Doe');
      expect(button.textContent).not.toContain('0x1234');
    });

    it('should show dropdown menu when clicked while authenticated', async () => {
      const { getByRole, getByText } = render(AuthButton);
      const button = getByRole('button');
      
      await fireEvent.click(button);
      flushSync();
      
      expect(getByText('View Public Profile')).toBeTruthy();
      expect(getByText('Edit Profile')).toBeTruthy();
      expect(getByText('Disconnect')).toBeTruthy();
    });

    it('should display full address in dropdown', async () => {
      const { getByRole, getByText } = render(AuthButton);
      const button = getByRole('button');
      
      await fireEvent.click(button);
      flushSync();
      
      expect(getByText('0x1234567890abcdef')).toBeTruthy();
    });

    it('should navigate to public profile when "View Public Profile" is clicked', async () => {
      const { getByRole, getByText } = render(AuthButton);
      const button = getByRole('button');
      
      await fireEvent.click(button);
      flushSync();
      
      const profileLink = getByText('View Public Profile');
      await fireEvent.click(profileLink);
      
      expect(push).toHaveBeenCalledWith('/participant/0x1234567890abcdef');
    });

    it('should navigate to edit profile when "Edit Profile" is clicked', async () => {
      const { getByRole, getByText } = render(AuthButton);
      const button = getByRole('button');
      
      await fireEvent.click(button);
      flushSync();
      
      const editLink = getByText('Edit Profile');
      await fireEvent.click(editLink);
      
      expect(push).toHaveBeenCalledWith('/profile');
    });

    it('should call logout when "Disconnect" is clicked', async () => {
      const { getByRole, getByText } = render(AuthButton);
      const button = getByRole('button');
      
      await fireEvent.click(button);
      flushSync();
      
      const disconnectButton = getByText('Disconnect');
      await fireEvent.click(disconnectButton);
      
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('should close dropdown when clicking outside', async () => {
      const { getByRole, queryByText, container } = render(AuthButton);
      const button = getByRole('button');
      
      // Open dropdown
      await fireEvent.click(button);
      flushSync();
      expect(queryByText('View Public Profile')).toBeTruthy();
      
      // Click outside
      await fireEvent.click(container);
      flushSync();
      
      // Dropdown should be closed
      expect(queryByText('View Public Profile')).toBeFalsy();
    });
  });

  describe('Name Updates', () => {
    it('should reactively update displayed name when user store changes', async () => {
      authState.set({
        isAuthenticated: true,
        address: '0x1234567890abcdef',
        loading: false,
        error: null
      });

      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      
      // Initially shows address
      expect(button.textContent).toContain('0x1234...cdef');
      
      // Update user store with name
      userStore.set({
        user: { 
          name: 'Alice Smith',
          address: '0x1234567890abcdef'
        },
        loading: false,
        error: null
      });
      
      await waitFor(() => {
        expect(button.textContent).toContain('Alice Smith');
        expect(button.textContent).not.toContain('0x1234');
      });
    });

    it('should fall back to address when name is removed', async () => {
      authState.set({
        isAuthenticated: true,
        address: '0x1234567890abcdef',
        loading: false,
        error: null
      });

      userStore.set({
        user: { 
          name: 'Bob Jones',
          address: '0x1234567890abcdef'
        },
        loading: false,
        error: null
      });

      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      
      expect(button.textContent).toContain('Bob Jones');
      
      // Remove name
      userStore.set({
        user: { 
          name: null,
          address: '0x1234567890abcdef'
        },
        loading: false,
        error: null
      });
      
      await waitFor(() => {
        expect(button.textContent).toContain('0x1234...cdef');
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading spinner when loading', () => {
      authState.set({
        isAuthenticated: false,
        address: null,
        loading: true,
        error: null
      });

      const { container } = render(AuthButton);
      const spinner = container.querySelector('.loading-spinner');
      expect(spinner).toBeTruthy();
    });

    it('should disable button while loading', () => {
      authState.set({
        isAuthenticated: false,
        address: null,
        loading: true,
        error: null
      });

      const { getByRole } = render(AuthButton);
      const button = getByRole('button');
      expect(button.disabled).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should display error message when auth fails', async () => {
      authState.set({
        isAuthenticated: false,
        address: null,
        loading: false,
        error: 'Connection failed'
      });

      const { getByText } = render(AuthButton);
      expect(getByText('Connection failed')).toBeTruthy();
    });

    it('should auto-dismiss error after 5 seconds', async () => {
      vi.useFakeTimers();
      
      authState.set({
        isAuthenticated: false,
        address: null,
        loading: false,
        error: 'Test error'
      });

      const { queryByText } = render(AuthButton);
      expect(queryByText('Test error')).toBeTruthy();
      
      // Fast-forward 5 seconds
      vi.advanceTimersByTime(5000);
      await waitFor(() => {
        expect(queryByText('Test error')).toBeFalsy();
      });
      
      vi.useRealTimers();
    });
  });
});