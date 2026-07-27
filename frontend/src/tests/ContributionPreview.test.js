import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/svelte/svelte5';
import { push } from 'svelte-spa-router';
import ContributionPreview from '../routes/ContributionPreview.svelte';
import { contributionsAPI } from '../lib/api';
import { renderWithEffects } from './testHelpers';

const getContributionMock = /** @type {import('vitest').Mock} */ (contributionsAPI.getContribution);
const getContributionsMock = /** @type {import('vitest').Mock} */ (contributionsAPI.getContributions);

/**
 * @param {number} id
 * @param {string} title
 */
function contribution(id, title) {
  return {
    id,
    title,
    notes: `${title} notes`,
    contribution_date: '2026-07-01T12:00:00Z',
    frozen_global_points: 10,
    contribution_type_details: {
      category: 'builder',
      name: 'Build',
    },
    user_details: {
      name: 'Builder',
      address: '0x123',
    },
  };
}

describe('ContributionPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getContributionMock.mockImplementation((id) =>
      Promise.resolve({
        data: contribution(Number(id), Number(id) === 1 ? 'First contribution' : 'Second contribution'),
      })
    );
    getContributionsMock.mockResolvedValue({
      data: {
        results: [
          contribution(1, 'First contribution'),
          contribution(2, 'Second contribution'),
        ],
      },
    });
  });

  it('loads the new contribution when its route id changes', async () => {
    const { rerender } = /** @type {any} */ (renderWithEffects(ContributionPreview, {
      props: { params: { id: '1' } },
    }));

    await waitFor(() => {
      expect(screen.getByText('First contribution')).toBeDefined();
    });

    await fireEvent.click(screen.getByRole('link', { name: /Second contribution/ }));
    expect(push).toHaveBeenCalledWith('/builders/contribution/2');

    await rerender({ params: { id: '2' } });

    await waitFor(() => {
      expect(contributionsAPI.getContribution).toHaveBeenCalledWith('2');
      expect(screen.getByRole('heading', { name: 'Second contribution' })).toBeDefined();
    });
  });
});
