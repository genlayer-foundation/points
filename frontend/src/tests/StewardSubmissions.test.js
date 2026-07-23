import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { querystring } from 'svelte-spa-router';
import StewardSubmissions from '../routes/StewardSubmissions.svelte';
import { authState } from '../lib/auth.js';
import { contributionsAPI, leaderboardAPI, stewardAPI } from '../lib/api.js';
import { userStore } from '../lib/userStore.js';

const contributionType = {
  id: 7,
  name: 'Builder Project',
  category: 'builder',
  min_points: 0,
  max_points: 100,
  review_flow: null
};

function makeSubmission(overrides = {}) {
  return {
    id: 42,
    user: 9,
    user_details: {
      id: 9,
      name: 'Project Builder',
      address: '0x1234567890abcdef'
    },
    contribution_type: 7,
    contribution_type_details: contributionType,
    contribution_date: '2026-06-01T12:00:00Z',
    created_at: '2026-06-01T12:00:00Z',
    notes: 'Project submission notes.',
    title: 'Project submission',
    state: 'accepted',
    state_display: 'Accepted',
    staff_reply: '',
    evidence_items: [],
    proposed_points: null,
    proposed_action: null,
    proposed_contribution_type: null,
    proposed_user: null,
    proposed_user_details: null,
    proposed_staff_reply: '',
    proposed_create_highlight: false,
    proposed_highlight_title: '',
    proposed_highlight_description: '',
    proposed_by: null,
    proposed_at: null,
    proposed_by_details: null,
    has_proposal: false,
    escalated_at: null,
    proposal_review_status: null,
    proposal_review_feedback: '',
    proposal_is_ai: false,
    rubric_review: null,
    ai_analysis: null,
    notes_count: 0,
    is_interesting: true,
    has_appeal: false,
    appeal_reason: '',
    appealed_at: null,
    more_info_requests: [],
    mission: null,
    contribution: null,
    project_contribution: null,
    ...overrides
  };
}

describe('Steward submissions queue shortcuts', () => {
  let queryValue;

  beforeEach(() => {
    vi.clearAllMocks();
    queryValue = '';
    querystring.subscribe = vi.fn((run) => {
      run(queryValue);
      return () => {};
    });

    authState.setAuthenticated(true, '0x123');
    userStore.setUser({ id: 5, steward_tier: 3 });
    window.history.replaceState({}, '', '/stewards/submissions');

    contributionsAPI.getAllContributionTypes.mockResolvedValue({ data: [contributionType] });
    contributionsAPI.getAllMissions.mockResolvedValue({ data: [] });
    leaderboardAPI.getActiveMultipliers = vi.fn().mockResolvedValue({ data: [] });
    stewardAPI.getMyPermissions.mockResolvedValue({ data: { 7: ['accept'] } });
    stewardAPI.getTemplates.mockResolvedValue({ data: [] });
    stewardAPI.getStewards.mockResolvedValue({ data: [] });
    stewardAPI.getSubmissions = vi.fn().mockResolvedValue({
      data: { results: [], count: 0 }
    });
    stewardAPI.toggleInteresting = vi.fn();
    stewardAPI.proposeSubmission = vi.fn();
  });

  afterEach(() => {
    authState.setAuthenticated(false);
    userStore.clearUser();
  });

  it('sets the intended status when applying each queue shortcut', async () => {
    render(StewardSubmissions);
    await waitFor(() => expect(stewardAPI.getSubmissions).toHaveBeenCalled());

    await fireEvent.click(screen.getByRole('button', { name: 'AI-reviewed, unassigned' }));
    await waitFor(() => {
      expect(stewardAPI.getSubmissions.mock.calls.at(-1)[0]).toMatchObject({
        state: 'pending',
        has_ai_analysis: true,
        assigned_to: 'unassigned'
      });
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Escalated' }));
    await waitFor(() => {
      expect(stewardAPI.getSubmissions.mock.calls.at(-1)[0]).toMatchObject({
        state: 'pending',
        is_escalated: true
      });
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Apex queue' }));
    await waitFor(() => {
      expect(stewardAPI.getSubmissions.mock.calls.at(-1)[0]).toMatchObject({
        state: 'accepted',
        is_interesting: true
      });
    });
  });

  it('removes a submission after it is unmarked in the Apex queue', async () => {
    queryValue = `status=accepted&q=${encodeURIComponent('status:accepted is:interesting')}`;
    const submission = makeSubmission();
    stewardAPI.getSubmissions.mockResolvedValue({
      data: { results: [submission], count: 1 }
    });
    stewardAPI.toggleInteresting.mockResolvedValue({
      data: { ...submission, is_interesting: false }
    });

    render(StewardSubmissions);
    const interesting = await screen.findByRole('checkbox', { name: 'Interesting' });

    await fireEvent.click(interesting);

    await waitFor(() => {
      expect(stewardAPI.toggleInteresting).toHaveBeenCalledWith(42, false);
      expect(screen.getByText('No submissions found matching your filters.')).toBeTruthy();
      expect(screen.getByText('0')).toBeTruthy();
    });
  });

  it('uses the last applied query when updating queue flags', async () => {
    queryValue = `status=accepted&q=${encodeURIComponent('status:accepted is:interesting')}`;
    const submission = makeSubmission();
    stewardAPI.getSubmissions.mockResolvedValue({
      data: { results: [submission], count: 1 }
    });
    stewardAPI.toggleInteresting.mockResolvedValue({
      data: { ...submission, is_interesting: false }
    });

    render(StewardSubmissions);
    const interesting = await screen.findByRole('checkbox', { name: 'Interesting' });
    const search = screen.getByPlaceholderText('Search URL or text, or type sort:-reviewed...');

    await fireEvent.input(search, { target: { value: 'status:accepted not:interesting' } });
    await fireEvent.click(interesting);

    await waitFor(() => {
      expect(stewardAPI.getSubmissions).toHaveBeenCalledTimes(1);
      expect(screen.getByText('No submissions found matching your filters.')).toBeTruthy();
      expect(screen.getByText('0')).toBeTruthy();
    });
  });

  it('removes a submission when a replacement proposal clears its escalation', async () => {
    queryValue = `status=pending&q=${encodeURIComponent('is:escalated')}`;
    const submission = makeSubmission({
      state: 'pending',
      state_display: 'Pending Review',
      escalated_at: '2026-06-02T12:00:00Z',
      is_interesting: false
    });
    stewardAPI.getMyPermissions.mockResolvedValue({ data: { 7: ['propose'] } });
    stewardAPI.getSubmissions.mockResolvedValue({
      data: { results: [submission], count: 1 }
    });
    stewardAPI.proposeSubmission.mockResolvedValue({
      data: {
        ...submission,
        escalated_at: null,
        has_proposal: true,
        proposed_action: 'accept'
      }
    });

    render(StewardSubmissions);
    const propose = await screen.findByRole('button', { name: 'Propose acceptance' });

    await fireEvent.click(propose);

    await waitFor(() => {
      expect(stewardAPI.proposeSubmission).toHaveBeenCalledWith(42, expect.objectContaining({
        proposed_action: 'accept'
      }));
      expect(screen.getByText('No submissions found matching your filters.')).toBeTruthy();
      expect(screen.getByText('0')).toBeTruthy();
    });
  });
});
