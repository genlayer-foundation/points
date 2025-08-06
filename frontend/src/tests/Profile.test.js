import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte/svelte5';
import { flushSync } from 'svelte';
import Profile from '../routes/Profile.svelte';
import { push } from 'svelte-spa-router';
import { authState } from '../lib/auth';
import { userStore } from '../lib/userStore';

// Mock the API
vi.mock('../lib/api', () => ({
  getCurrentUser: vi.fn(),
  updateUserProfile: vi.fn()
}));

// Mock svelte-spa-router
vi.mock('svelte-spa-router', () => ({
  push: vi.fn()
}));

// Mock auth and user stores
vi.mock('../lib/auth', () => ({
  authState: {
    subscribe: vi.fn((fn) => {
      fn({ isAuthenticated: true, address: '0x123456789' });
      return { unsubscribe: vi.fn() };
    })
  }
}));

vi.mock('../lib/userStore', () => ({
  userStore: {
    updateUser: vi.fn()
  }
}));

import { getCurrentUser, updateUserProfile } from '../lib/api';

describe('Profile Component', () => {
  const mockUser = {
    id: 1,
    name: 'Test User',
    email: 'test@example.com',
    address: '0x123456789',
    leaderboard_entry: {
      rank: 5,
      total_points: 100
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    
    // Default mock implementations
    getCurrentUser.mockResolvedValue(mockUser);
    updateUserProfile.mockResolvedValue({ ...mockUser, name: 'Updated Name' });
  });

  it('should render edit profile page with correct title', async () => {
    const { getByText } = render(Profile);
    
    await waitFor(() => {
      expect(getByText('Edit Profile')).toBeTruthy();
    });
  });

  it('should load and display user data on mount', async () => {
    const { getByText, getByDisplayValue } = render(Profile);
    
    await waitFor(() => {
      expect(getCurrentUser).toHaveBeenCalledTimes(1);
      expect(getByText('0x123456789')).toBeTruthy();
      expect(getByDisplayValue('Test User')).toBeTruthy();
    });
  });

  it('should display wallet address but not email', async () => {
    const { getByText, queryByText } = render(Profile);
    
    await waitFor(() => {
      expect(getByText('0x123456789')).toBeTruthy();
      expect(queryByText('test@example.com')).toBeFalsy();
    });
  });

  it('should enable save button only when name changes', async () => {
    const { getByRole, getByLabelText } = render(Profile);
    
    await waitFor(() => {
      const saveButton = getByRole('button', { name: /save changes/i });
      expect(saveButton.disabled).toBe(true);
    });

    const nameInput = getByLabelText(/display name/i);
    await fireEvent.input(nameInput, { target: { value: 'New Name' } });
    flushSync();

    const saveButton = getByRole('button', { name: /save changes/i });
    expect(saveButton.disabled).toBe(false);
  });

  it('should save profile changes and redirect to public profile', async () => {
    const { getByRole, getByLabelText } = render(Profile);
    
    await waitFor(() => {
      expect(getCurrentUser).toHaveBeenCalled();
    });

    const nameInput = getByLabelText(/display name/i);
    await fireEvent.input(nameInput, { target: { value: 'New Name' } });
    flushSync();

    const saveButton = getByRole('button', { name: /save changes/i });
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(updateUserProfile).toHaveBeenCalledWith({ name: 'New Name' });
      expect(userStore.updateUser).toHaveBeenCalledWith({ name: 'New Name' });
      expect(sessionStorage.getItem('profileUpdateSuccess')).toBe('Profile updated successfully!');
      expect(push).toHaveBeenCalledWith('/participant/0x123456789');
    });
  });

  it('should handle save errors gracefully', async () => {
    const errorMessage = 'Failed to update profile';
    updateUserProfile.mockRejectedValue(new Error(errorMessage));

    const { getByRole, getByLabelText, getByText } = render(Profile);
    
    await waitFor(() => {
      expect(getCurrentUser).toHaveBeenCalled();
    });

    const nameInput = getByLabelText(/display name/i);
    await fireEvent.input(nameInput, { target: { value: 'New Name' } });
    flushSync();

    const saveButton = getByRole('button', { name: /save changes/i });
    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(getByText(errorMessage)).toBeTruthy();
      expect(push).not.toHaveBeenCalled();
    });
  });

  it('should handle cancel and redirect to public profile', async () => {
    const { getByRole } = render(Profile);
    
    await waitFor(() => {
      expect(getCurrentUser).toHaveBeenCalled();
    });

    const cancelButton = getByRole('button', { name: /cancel/i });
    await fireEvent.click(cancelButton);

    expect(push).toHaveBeenCalledWith('/participant/0x123456789');
  });

  it('should display loading state initially', () => {
    getCurrentUser.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve(mockUser), 100))
    );

    const { getByText } = render(Profile);
    expect(getByText('Loading profile...')).toBeTruthy();
  });

  it('should display error when profile fails to load', async () => {
    const errorMessage = 'Failed to load profile';
    getCurrentUser.mockRejectedValue(new Error(errorMessage));

    const { getByText } = render(Profile);

    await waitFor(() => {
      expect(getByText(errorMessage)).toBeTruthy();
    });
  });

  it('should show helper text for name field', async () => {
    const { getByText } = render(Profile);
    
    await waitFor(() => {
      expect(getByText('This name will be displayed on your public profile')).toBeTruthy();
    });
  });

  it('should disable save button while saving', async () => {
    updateUserProfile.mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve(mockUser), 100))
    );

    const { getByRole, getByLabelText } = render(Profile);
    
    await waitFor(() => {
      expect(getCurrentUser).toHaveBeenCalled();
    });

    const nameInput = getByLabelText(/display name/i);
    await fireEvent.input(nameInput, { target: { value: 'New Name' } });
    flushSync();

    const saveButton = getByRole('button', { name: /save changes/i });
    await fireEvent.click(saveButton);

    // Button should show "Saving..." and be disabled
    expect(getByRole('button', { name: /saving/i })).toBeTruthy();
    expect(saveButton.disabled).toBe(true);
  });
});