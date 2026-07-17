import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';

const mocks = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  replace: vi.fn(),
  startRoleJourney: vi.fn(),
  communityJourney: vi.fn(),
  linkXAccount: vi.fn(),
  linkDiscordAccount: vi.fn(),
  verifyCommunityPost: vi.fn(),
  completeCommunityJourney: vi.fn(),
  listSocialTasks: vi.fn(),
  completeSocialTask: vi.fn(),
  refreshTwitterUsername: vi.fn(),
  refreshDiscordUsername: vi.fn(),
  refreshGithubUsername: vi.fn(),
}));

vi.mock('svelte-spa-router', () => ({
  replace: mocks.replace,
}));

vi.mock('../lib/api.js', () => ({
  getCurrentUser: mocks.getCurrentUser,
  journeyAPI: {
    startRoleJourney: mocks.startRoleJourney,
    communityJourney: mocks.communityJourney,
    linkXAccount: mocks.linkXAccount,
    linkDiscordAccount: mocks.linkDiscordAccount,
    verifyCommunityPost: mocks.verifyCommunityPost,
    completeCommunityJourney: mocks.completeCommunityJourney,
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

import CommunityJourney from '../routes/CommunityJourney.svelte';
import CommunityJourneyGate from '../routes/CommunityJourneyGate.svelte';
import { userStore } from '../lib/userStore.js';

const nonCreator = {
  id: 1,
  name: 'Community Member',
  creator: false,
  has_community_welcome: true,
};

const completedJourney = {
  complete: true,
  steps: {
    link_x: { done: true },
    link_discord: { done: true },
    follow_x: { done: true },
    join_discord: { done: true },
    x_post: { done: true },
  },
};

function expectNoJourneyRequests() {
  expect(mocks.startRoleJourney).not.toHaveBeenCalled();
  expect(mocks.communityJourney).not.toHaveBeenCalled();
  expect(mocks.listSocialTasks).not.toHaveBeenCalled();
}

describe('Community journey membership and recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    userStore.clearUser();
    mocks.getCurrentUser.mockResolvedValue(nonCreator);
    mocks.startRoleJourney.mockResolvedValue({ data: {} });
    mocks.communityJourney.mockResolvedValue({ data: completedJourney });
    mocks.listSocialTasks.mockResolvedValue({ data: [] });
  });

  it('redirects a confirmed Creator before mounting journey APIs', async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...nonCreator, creator: true });

    render(CommunityJourneyGate);

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith('/community'));
    expect(mocks.getCurrentUser).toHaveBeenCalledTimes(1);
    expectNoJourneyRequests();
  });

  it('shows a neutral profile retry state without touching journey APIs', async () => {
    mocks.getCurrentUser.mockRejectedValueOnce(new Error('network unavailable'));

    render(CommunityJourneyGate);

    expect(await screen.findByRole('heading', { name: "We couldn't verify your profile" })).toBeTruthy();
    expectNoJourneyRequests();

    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(mocks.getCurrentUser).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(mocks.communityJourney).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('Creator journey complete')).toBeTruthy();
  });

  it('loads the journey only after a refreshed non-Creator profile', async () => {
    render(CommunityJourneyGate);

    await waitFor(() => expect(mocks.getCurrentUser).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mocks.communityJourney).toHaveBeenCalledTimes(1));
    expect(mocks.listSocialTasks).toHaveBeenCalledWith({ category: 'community' });
    expect(await screen.findByText('Creator journey complete')).toBeTruthy();
  });

  it('defensively redirects a Creator when the journey component is mounted directly', async () => {
    userStore.setUser({ ...nonCreator, creator: true });

    render(CommunityJourney);

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith('/community'));
    expectNoJourneyRequests();
  });

  it('replaces a failed initial journey load with an explicit retry state', async () => {
    userStore.setUser(nonCreator);
    mocks.communityJourney.mockRejectedValueOnce(new Error('request timed out'));

    render(CommunityJourney);

    expect(await screen.findByRole('heading', { name: "Your journey couldn't be loaded" })).toBeTruthy();
    expect(screen.queryByLabelText('0 of 5 steps complete')).toBeNull();

    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    await waitFor(() => expect(mocks.communityJourney).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('Creator journey complete')).toBeTruthy();
  });
});
