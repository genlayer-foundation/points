import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';

const mocks = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  replace: vi.fn(),
  startBuilderJourney: vi.fn(),
  deploymentStatus: vi.fn(),
  linkGithubAccount: vi.fn(),
  completeBuilderJourney: vi.fn(),
  listSocialTasks: vi.fn(),
  completeSocialTask: vi.fn(),
  getValidatorBalance: vi.fn(),
  refreshTwitterUsername: vi.fn(),
  refreshDiscordUsername: vi.fn(),
  refreshGithubUsername: vi.fn(),
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showWarning: vi.fn(),
}));

vi.mock('svelte-spa-router', () => ({
  replace: mocks.replace,
}));

vi.mock('../lib/auth.js', async () => {
  const { get, writable } = await import('svelte/store');
  const store = writable({
    isAuthenticated: true,
    address: '0x1111111111111111111111111111111111111111',
    provider: null,
  });
  return {
    authState: {
      subscribe: store.subscribe,
      get: () => get(store),
    },
  };
});

vi.mock('../lib/api.js', () => ({
  getCurrentUser: mocks.getCurrentUser,
  journeyAPI: {
    startBuilderJourney: mocks.startBuilderJourney,
    deploymentStatus: mocks.deploymentStatus,
    linkGithubAccount: mocks.linkGithubAccount,
    completeBuilderJourney: mocks.completeBuilderJourney,
  },
  socialTasksAPI: {
    list: mocks.listSocialTasks,
    complete: mocks.completeSocialTask,
  },
  socialAPI: {
    refreshTwitterUsername: mocks.refreshTwitterUsername,
    refreshDiscordUsername: mocks.refreshDiscordUsername,
    refreshGithubUsername: mocks.refreshGithubUsername,
  },
}));

vi.mock('../lib/blockchain.js', () => ({
  getValidatorBalance: mocks.getValidatorBalance,
}));

vi.mock('../lib/toastStore.js', () => ({
  showError: mocks.showError,
  showSuccess: mocks.showSuccess,
  showWarning: mocks.showWarning,
}));

import BuilderJourney from '../routes/BuilderJourney.svelte';
import { userStore } from '../lib/userStore.js';

const builderCandidate = {
  id: 1,
  name: 'Builder Candidate',
  builder: null,
  has_builder_welcome: true,
  has_community_link_github: true,
  github_connection: { platform_username: 'builder-candidate' },
};

describe('Builder journey completion recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    userStore.clearUser();
    userStore.setUser(builderCandidate);
    mocks.listSocialTasks.mockResolvedValue({
      data: [{
        slug: 'star-genlayer-boilerplate',
        title: 'Star the boilerplate',
        status: 'completed',
        points: 25,
      }],
    });
    mocks.deploymentStatus.mockResolvedValue({ data: { has_deployments: false } });
    mocks.getValidatorBalance.mockResolvedValue({ balance: 0n, formatted: '0.0000' });
  });

  it('recovers from stale CSRF and ignores a failed post-success profile refresh', async () => {
    const csrfError = {
      response: { status: 403, data: { detail: 'CSRF Failed: CSRF token incorrect.' } },
    };
    const completedUser = {
      ...builderCandidate,
      builder: { created_at: '2026-08-04T00:00:00Z' },
    };
    mocks.completeBuilderJourney
      .mockRejectedValueOnce(csrfError)
      .mockResolvedValueOnce({ data: { user: completedUser } });
    mocks.getCurrentUser.mockRejectedValueOnce(new Error('profile refresh unavailable'));

    render(BuilderJourney);
    const button = await screen.findByRole('button', { name: 'Claim Builder Role' });
    await waitFor(() => expect(/** @type {HTMLButtonElement} */ (button).disabled).toBe(false));
    await fireEvent.click(button);

    await waitFor(() => expect(mocks.completeBuilderJourney).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith('/builders'));
    expect(mocks.showSuccess).toHaveBeenCalledWith('Builder role claimed.');
    expect(mocks.showError).not.toHaveBeenCalled();
  });
});
