import { render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { describe, expect, it, vi } from 'vitest';
import SubmissionCard from '../components/SubmissionCard.svelte';

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
    contribution_type_details: {
      id: 7,
      name: 'Builder Project',
      category: 'builder',
      min_points: 0,
      max_points: 100,
      review_flow: 'builder_project'
    },
    contribution_date: '2026-06-01T12:00:00Z',
    created_at: '2026-06-01T12:00:00Z',
    notes: 'Project submission notes',
    title: 'Project submission',
    state: 'pending',
    state_display: 'Pending Review',
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
    proposed_confidence: null,
    proposed_template: null,
    proposed_template_name: null,
    rubric_review: null,
    notes_count: 0,
    is_interesting: false,
    has_appeal: false,
    appeal_reason: '',
    mission: null,
    contribution: null,
    ...overrides
  };
}

describe('SubmissionCard', () => {
  it('opens directly to the project proposal rubric for proposal-only stewards', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission(),
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose: vi.fn(),
        reviewData: {
          action: 'accept',
          user: 9,
          contribution_type: 7,
          points: 0,
          staff_reply: ''
        },
        permissions: {
          7: ['propose']
        },
        contributionTypes: [
          {
            id: 7,
            name: 'Builder Project',
            category: 'builder',
            min_points: 0,
            max_points: 100,
            review_flow: 'builder_project'
          }
        ],
        multipliers: { 7: 1 },
        templates: [],
        notes: [],
        enableRubricReview: true
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Project rubric')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Submit Proposal' })).toBeTruthy();
    });

    expect(screen.queryByRole('button', { name: 'Accept & Create Contribution' })).toBeNull();
  });

  it('normalizes request_more_info proposal actions before choosing a review view', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'request_more_info',
          proposed_staff_reply: 'Please add deployment evidence.'
        }),
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose: vi.fn(),
        reviewData: {
          action: 'accept',
          user: 9,
          contribution_type: 7,
          points: 0,
          staff_reply: ''
        },
        permissions: {
          7: ['request_more_info']
        },
        contributionTypes: [
          {
            id: 7,
            name: 'Builder Project',
            category: 'builder',
            min_points: 0,
            max_points: 100,
            review_flow: 'builder_project'
          }
        ],
        multipliers: { 7: 1 },
        templates: [],
        notes: [],
        enableRubricReview: true
      }
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Request Information' })).toBeTruthy();
    });

    expect(screen.queryByRole('button', { name: 'Accept & Create Contribution' })).toBeNull();
  });
});
