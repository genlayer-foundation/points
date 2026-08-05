import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte/svelte5';

const mocks = vi.hoisted(() => ({
  claimLink: vi.fn(),
  clearRedirect: vi.fn(),
  getCurrentUser: vi.fn(),
  push: vi.fn(),
  showError: vi.fn(),
  showSuccess: vi.fn(),
  authState: {
    subscribe: vi.fn((run) => {
      run({ isAuthenticated: true });
      return () => {};
    }),
    resetVerification: vi.fn(),
    setAuthenticated: vi.fn(),
  },
}));

vi.mock('svelte-spa-router', () => ({
  params: {
    subscribe(run) {
      run({ token: 'claim-token' });
      return () => {};
    },
  },
  push: mocks.push,
}));

vi.mock('../lib/auth.js', () => ({
  authState: mocks.authState,
}));

vi.mock('../lib/api.js', () => ({
  getCurrentUser: mocks.getCurrentUser,
  journeyAPI: {},
  poapsAPI: {
    claimLink: mocks.claimLink,
  },
  socialAPI: {},
}));

vi.mock('../lib/poapRedirect.js', () => ({
  clearPoapClaimRedirect: mocks.clearRedirect,
}));

vi.mock('../lib/toastStore.js', () => ({
  showError: mocks.showError,
  showSuccess: mocks.showSuccess,
}));

import PoapClaim from '../routes/PoapClaim.svelte';
import { userStore } from '../lib/userStore.js';


describe('POAP mint-link access', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    userStore.clearUser();
    mocks.claimLink.mockResolvedValue({ data: {} });
  });

  it('waits for permission refresh and does not claim for a read-only viewer', async () => {
    let resolveUser;
    mocks.getCurrentUser.mockImplementationOnce(() => new Promise((resolve) => {
      resolveUser = resolve;
    }));

    render(PoapClaim);

    await waitFor(() => expect(mocks.getCurrentUser).toHaveBeenCalledTimes(1));
    expect(mocks.claimLink).not.toHaveBeenCalled();

    resolveUser({ can_view_role_sections: true, creator: null });

    expect(await screen.findByRole('heading', { name: 'View-only access' })).toBeTruthy();
    expect(mocks.claimLink).not.toHaveBeenCalled();
    expect(mocks.clearRedirect).toHaveBeenCalledWith('claim-token');
  });

  it('claims only after refreshed permissions allow it', async () => {
    mocks.getCurrentUser.mockResolvedValue({
      can_view_role_sections: false,
      creator: null,
    });

    render(PoapClaim);

    await waitFor(() => expect(mocks.claimLink).toHaveBeenCalledWith('claim-token'));
    expect(mocks.getCurrentUser.mock.invocationCallOrder[0])
      .toBeLessThan(mocks.claimLink.mock.invocationCallOrder[0]);
  });
});
