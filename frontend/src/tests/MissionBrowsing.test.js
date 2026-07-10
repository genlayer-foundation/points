import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';

const mocks = vi.hoisted(() => {
  const createStore = (value) => ({
    subscribe(run) {
      run(value);
      return () => {};
    },
  });

  return {
    push: vi.fn(),
    location: createStore('/all-contributions'),
    getMissions: vi.fn(),
    getAllContributionTypes: vi.fn(),
    getContributionType: vi.fn(),
    getContributionTypeStatistics: vi.fn(),
    getContributionTypeHighlights: vi.fn(),
    getContributions: vi.fn(),
    getAllHighlights: vi.fn(),
    getMission: vi.fn(),
    getUserByAddress: vi.fn(),
  };
});

vi.mock('svelte-spa-router', () => ({
  push: mocks.push,
  location: mocks.location,
  loc: mocks.location,
}));

vi.mock('../lib/missionsStore.js', () => ({
  getMissions: mocks.getMissions,
}));

vi.mock('../lib/api', () => ({
  contributionsAPI: {
    getAllContributionTypes: mocks.getAllContributionTypes,
    getContributionType: mocks.getContributionType,
    getContributionTypeStatistics: mocks.getContributionTypeStatistics,
    getContributionTypeHighlights: mocks.getContributionTypeHighlights,
    getContributions: mocks.getContributions,
    getAllHighlights: mocks.getAllHighlights,
    getMission: mocks.getMission,
  },
  usersAPI: {
    getUserByAddress: mocks.getUserByAddress,
  },
}));

import AllContributions from '../routes/AllContributions.svelte';
import ContributionTypeDetail from '../routes/ContributionTypeDetail.svelte';
import MissionDetail from '../routes/MissionDetail.svelte';

const contributionType = {
  id: 7,
  name: 'Code contributions',
  description: 'Build useful things.',
  category: 'builder',
  is_submittable: true,
  show_in_contributions: true,
};

const activeMission = {
  id: 11,
  name: 'Current mission',
  contribution_type: 7,
  start_date: '2025-01-01T00:00:00Z',
  end_date: '2099-01-01T00:00:00Z',
  is_active: true,
};

const endedMission = {
  id: 12,
  name: 'Archived mission',
  contribution_type: 7,
  start_date: '2024-01-01T00:00:00Z',
  end_date: '2024-02-01T12:00:00Z',
  is_active: false,
};

describe('historical mission browsing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, '', '/all-contributions');

    mocks.getMissions.mockResolvedValue([endedMission, activeMission]);
    mocks.getAllContributionTypes.mockResolvedValue({ data: [contributionType] });
    mocks.getContributionType.mockResolvedValue({ data: contributionType });
    mocks.getContributionTypeStatistics.mockResolvedValue({
      data: [{ id: 7, min_points: 1, max_points: 10, current_multiplier: 1 }],
    });
    mocks.getContributionTypeHighlights.mockResolvedValue({ data: [] });
    mocks.getContributions.mockResolvedValue({ data: { results: [], count: 0 } });
    mocks.getAllHighlights.mockResolvedValue({ data: [] });
    mocks.getMission.mockResolvedValue({
      data: {
        ...endedMission,
        description: 'An archived mission.',
        unique_users: 3,
        contributions_count: 4,
        points_earned: 50,
        contribution_type_details: {
          ...contributionType,
          max_submissions: null,
          submissions_remaining: null,
          is_full: false,
        },
      },
    });
  });

  it('lists ended missions on their contribution type page', async () => {
    render(ContributionTypeDetail, { props: { params: { id: '7' } } });

    await waitFor(() => {
      expect(mocks.getMissions).toHaveBeenCalledWith({
        contribution_type: '7',
        include_inactive: true,
        summary: true,
      });
    });

    expect(await screen.findByText('Archived mission')).toBeTruthy();
    expect(screen.getByText(/Ended Feb 1, 2024/)).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: /Archived mission/ }));
    expect(mocks.push).toHaveBeenCalledWith('/mission/12');
  });

  it('offers ended missions as filters in all contributions', async () => {
    window.history.replaceState({}, '', '/all-contributions?type=7&mission=12');
    render(AllContributions);

    await waitFor(() => {
      expect(mocks.getMissions).toHaveBeenCalledWith({
        include_inactive: true,
        summary: true,
      });
    });

    const missionSelect = screen.getByLabelText('Mission');
    expect(await screen.findByRole('option', { name: 'Archived mission (Ended)' })).toBeTruthy();
    expect(missionSelect.value).toBe('12');

    await waitFor(() => {
      expect(mocks.getContributions).toHaveBeenCalledWith(
        expect.objectContaining({
          contribution_type: '7',
          mission: '12',
        }),
      );
    });
  });

  it('keeps an ended mission readable without offering submissions', async () => {
    render(MissionDetail, { props: { params: { id: '12' } } });

    const submitButton = await screen.findByRole('button', { name: 'Mission ended' });
    expect(submitButton.disabled).toBe(true);
    expect(screen.getByText('An archived mission.')).toBeTruthy();
    expect(screen.getByText('4')).toBeTruthy();
    expect(mocks.getMission).toHaveBeenCalledWith('12');
  });
});
