import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte/svelte5';

import Dashboard from '../routes/Dashboard.svelte';
import { contributionsAPI, leaderboardAPI, statsAPI } from '../lib/api.js';
import { currentCategory } from '../stores/category.js';


describe('Community dashboard rankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentCategory.set('community');

    statsAPI.getDashboardStats.mockResolvedValue({ data: {} });
    contributionsAPI.getContributions.mockResolvedValue({ data: { results: [] } });
    leaderboardAPI.getLeaderboard.mockResolvedValue({ data: { results: [] } });
    leaderboardAPI.getCommunityPodium.mockResolvedValue({
      data: [
        { rank: 1, user: 1, user_details: { id: 1, name: 'Accepted One' }, total_points: 300 },
        { rank: 2, user: 2, user_details: { id: 2, name: 'Accepted Two' }, total_points: 200 },
        { rank: 3, user: 3, user_details: { id: 3, name: 'Third Place' }, total_points: 100 },
      ],
    });
  });

  afterEach(() => {
    currentCategory.set('builder');
  });

  it('uses all-time leaderboard totals and a separate accepted-submission podium', async () => {
    render(Dashboard);

    await waitFor(() => {
      expect(leaderboardAPI.getLeaderboard).toHaveBeenCalledWith({
        type: 'community',
        order: 'asc',
        limit: 5,
      });
      expect(leaderboardAPI.getCommunityPodium).toHaveBeenCalledTimes(1);
    });

    expect(leaderboardAPI.getMonthlyLeaderboardByType).not.toHaveBeenCalled();
    expect(screen.getByText('All-time XP and Community points')).toBeDefined();
    expect(screen.getByText('Accepted Submissions Podium')).toBeDefined();
    expect(screen.getByText('Accepted One')).toBeDefined();
    expect(screen.getByText('Accepted Two')).toBeDefined();
    expect(screen.getByText('Third Place')).toBeDefined();
  });
});
