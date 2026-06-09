import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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
  let originalClipboard;

  beforeEach(() => {
    originalClipboard = navigator.clipboard;
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      configurable: true
    });
  });

  it('copies only the submission id from the card', async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true
    });

    render(SubmissionCard, {
      props: {
        submission: makeSubmission({ id: 'submission-123' }),
        notes: []
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Copy ID' }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('submission-123');
    });
    expect(screen.queryByRole('button', { name: /Copy review context/i })).toBeNull();
  });

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
      expect(screen.getByText('Accept proposal')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Submit Accept Proposal' })).toBeTruthy();
    });

    expect(screen.queryByRole('button', { name: 'Accept & Create Contribution' })).toBeNull();
  });

  it('shows the builder project rubric in reject proposal state', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'reject',
          proposed_staff_reply: 'The repository does not build.',
          proposed_by_details: { name: 'AI Steward' },
          rubric_review: {
            action: 'reject',
            confidence: 'medium',
            gate_failures: ['repo_does_not_build'],
            sections: {},
            extras: [],
            overall_reason: 'The repository does not build.'
          }
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
      expect(screen.getAllByText('Reject proposal').length).toBeGreaterThan(0);
      expect(screen.getByText('Gate failures force a reject proposal. Clear all gate failures to propose accept or request info.')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Submit Reject Proposal' })).toBeTruthy();
    });
  });

  it('shows proposal criterion reasons instead of criterion descriptions while reviewing a builder project proposal', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'accept',
          proposed_staff_reply: 'The project meets the rubric.',
          proposed_by_details: { name: 'AI Steward' },
          rubric_review: {
            action: 'accept',
            confidence: 'high',
            gate_failures: [],
            sections: {
              genlayer_fit: { score: 4, reason: 'Strong fit because the contract adjudicates a contested outcome.' },
              contract_quality: { score: 3, reason: '' },
              engineering: { score: 4, reason: 'The repository builds and includes useful docs.' },
              frontend_ux: { score: 2, reason: '' }
            },
            extras: [],
            overall_reason: 'The proposal has enough evidence to accept.'
          }
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
          7: ['accept', 'reject']
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
      expect(screen.getByText('GenLayer fit')).toBeTruthy();
      expect(screen.getByText('Strong fit because the contract adjudicates a contested outcome.')).toBeTruthy();
      expect(screen.queryByText('Trustless adjudication must matter. No stakes or contested outcome caps this low.')).toBeNull();
    });
  });

  it('shows the builder project rubric as a direct accept evaluation without criterion reasons', async () => {
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
          points: 10,
          staff_reply: ''
        },
        permissions: {
          7: ['accept', 'reject']
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
      expect(screen.getByText('Accept evaluation')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Accept & Create Contribution' })).toBeTruthy();
    });

    expect(screen.queryByLabelText('GenLayer fit reason optional')).toBeNull();
    expect(screen.queryByText('Overall reason')).toBeNull();
  });

  it('submits the builder project rubric payload for direct reviews', async () => {
    const onReview = vi.fn();
    render(SubmissionCard, {
      props: {
        submission: makeSubmission(),
        showReviewForm: true,
        onReview,
        onPropose: vi.fn(),
        reviewData: {
          action: 'accept',
          user: 9,
          contribution_type: 7,
          points: 10,
          staff_reply: ''
        },
        permissions: {
          7: ['accept', 'reject']
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

    await fireEvent.change(screen.getByLabelText('GenLayer fit'), { target: { value: '4' } });
    await fireEvent.click(screen.getByLabelText('Live deployment'));
    await fireEvent.click(screen.getByRole('button', { name: 'Accept & Create Contribution' }));

    await waitFor(() => {
      expect(onReview).toHaveBeenCalledTimes(1);
    });
    const payload = onReview.mock.calls[0][1].rubric_review;
    expect(payload).toEqual(expect.objectContaining({
      gate_failures: [],
      extras: ['live_deployment'],
      overall_reason: ''
    }));
    expect(payload.sections.genlayer_fit).toEqual({ score: 4, reason: '' });
  });

  it('recalculates builder project points from criteria while preserving extras and allowing manual overrides', async () => {
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
          points: 10,
          staff_reply: ''
        },
        permissions: {
          7: ['accept', 'reject']
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

    const pointsInput = screen.getByLabelText('Points');
    await waitFor(() => {
      expect(pointsInput.value).toBe('0');
    });

    await fireEvent.change(screen.getByLabelText('GenLayer fit'), { target: { value: '5' } });
    await fireEvent.change(screen.getByLabelText('Contract quality'), { target: { value: '5' } });
    await fireEvent.change(screen.getByLabelText('Engineering'), { target: { value: '5' } });
    await fireEvent.change(screen.getByLabelText('Frontend / UX'), { target: { value: '5' } });
    await waitFor(() => {
      expect(pointsInput.value).toBe('50');
    });

    await fireEvent.click(screen.getByLabelText('Demo video'));
    await waitFor(() => {
      expect(pointsInput.value).toBe('50');
    });

    await fireEvent.input(pointsInput, { target: { value: '7' } });
    expect(pointsInput.value).toBe('7');

    await fireEvent.change(screen.getByLabelText('Frontend / UX'), { target: { value: '4' } });
    await waitFor(() => {
      expect(pointsInput.value).toBe('7');
    });

    await fireEvent.click(screen.getByLabelText('Live deployment'));
    await waitFor(() => {
      expect(pointsInput.value).toBe('7');
    });
  });

  it('shows and submits the rubric when a direct accept selected type is builder project', async () => {
    const onReview = vi.fn();
    const standardType = {
      id: 8,
      name: 'Standard Builder',
      category: 'builder',
      min_points: 0,
      max_points: 10,
      review_flow: null
    };
    const projectType = {
      id: 7,
      name: 'Builder Project',
      category: 'builder',
      min_points: 0,
      max_points: 100,
      review_flow: 'builder_project'
    };

    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          contribution_type: 8,
          contribution_type_details: standardType
        }),
        showReviewForm: true,
        onReview,
        onPropose: vi.fn(),
        reviewData: {
          action: 'accept',
          user: 9,
          contribution_type: 7,
          points: 75,
          staff_reply: ''
        },
        permissions: {
          8: ['accept', 'reject'],
          7: ['accept', 'reject']
        },
        contributionTypes: [standardType, projectType],
        multipliers: { 7: 1, 8: 1 },
        templates: [],
        notes: [],
        enableRubricReview: true
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Project rubric')).toBeTruthy();
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Accept & Create Contribution' }));

    await waitFor(() => {
      expect(onReview).toHaveBeenCalledTimes(1);
    });
    expect(onReview.mock.calls[0][1]).toEqual(expect.objectContaining({
      contribution_type: 7,
      rubric_review: expect.objectContaining({
        gate_failures: [],
        overall_reason: ''
      })
    }));
  });

  it('selects the gate rejection template when a direct reviewer chooses a gate failure', async () => {
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
          points: 10,
          staff_reply: ''
        },
        permissions: {
          7: ['accept', 'reject']
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
        templates: [
          {
            id: 99,
            label: 'Reject: Project Does Not Build',
            text: 'The project does not build from the submitted repository.',
            action: 'reject'
          }
        ],
        notes: [],
        enableRubricReview: true
      }
    });

    await fireEvent.click(screen.getByLabelText('Repo does not build or work'));

    await waitFor(() => {
      expect(screen.getByText('Reject evaluation')).toBeTruthy();
      expect(screen.getByRole('button', { name: 'Reject Submission' })).toBeTruthy();
      expect(screen.getByDisplayValue('The project does not build from the submitted repository.')).toBeTruthy();
    });
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
