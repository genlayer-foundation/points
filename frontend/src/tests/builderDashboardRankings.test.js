import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte/svelte5';

import Dashboard from '../routes/Dashboard.svelte';
import { leaderboardAPI, statsAPI } from '../lib/api.js';
import { currentCategory } from '../stores/category.js';

const getLeaderboardMock = /** @type {import('vitest').Mock} */ (leaderboardAPI.getLeaderboard);
const getMonthlyLeaderboardMock = /** @type {import('vitest').Mock} */ (
  leaderboardAPI.getMonthlyLeaderboardByType
);

/**
 * @param {number} id
 * @param {string} name
 * @param {number} points
 */
function rankingEntry(id, name, points) {
  return {
    rank: id,
    user_id: id,
    user_name: name,
    total_points: points,
  };
}

describe('Builder dashboard rankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentCategory.set('builder');

    statsAPI.getDashboardStats.mockResolvedValue({ data: {} });
    getLeaderboardMock.mockResolvedValue({
      data: {
        results: [
          rankingEntry(1, 'All Time One', 500),
          rankingEntry(2, 'All Time Two', 400),
          rankingEntry(3, 'All Time Three', 300),
          rankingEntry(4, 'All Time Four', 200),
          rankingEntry(5, 'All Time Five', 100),
        ],
      },
    });
    getMonthlyLeaderboardMock.mockResolvedValue({
      data: [
        rankingEntry(11, 'Recent One', 90),
        rankingEntry(12, 'Recent Two', 80),
        rankingEntry(13, 'Recent Three', 70),
      ],
    });
  });

  afterEach(() => {
    currentCategory.set('builder');
  });

  it('shows five all-time contributors and a separate 30-day podium', async () => {
    render(Dashboard);

    await waitFor(() => {
      expect(getLeaderboardMock).toHaveBeenCalledWith({
        type: 'builder',
        order: 'asc',
        limit: 5,
      });
      expect(getMonthlyLeaderboardMock).toHaveBeenCalledWith(
        'builder',
        3,
        expect.objectContaining({
          start_date: expect.any(String),
          end_date: expect.any(String),
        })
      );
    });

    expect(screen.getByText('All-time builder contributors')).toBeDefined();
    expect(screen.getByText('Last 30 Days Podium')).toBeDefined();

    for (const name of [
      'All Time One',
      'All Time Two',
      'All Time Three',
      'All Time Four',
      'All Time Five',
      'Recent One',
      'Recent Two',
      'Recent Three',
    ]) {
      expect(screen.getByText(name)).toBeDefined();
    }
  });
});
