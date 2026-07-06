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
    proposal_review_status: null,
    proposal_review_feedback: '',
    proposal_questioned_by: null,
    proposal_questioned_by_details: null,
    proposal_questioned_at: null,
    rubric_review: null,
    notes_count: 0,
    is_interesting: false,
    has_appeal: false,
    appeal_reason: '',
    more_info_requests: [],
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

  it('shows more information requests in a dedicated panel', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'pending',
          state_display: 'Pending Review',
          more_info_requests: [
            {
              id: 1,
              message: 'Please add a working demo link and deployment notes.',
              user_name: 'Test Steward',
              created_at: '2026-06-02T12:00:00Z'
            }
          ]
        }),
        notes: []
      }
    });

    expect(screen.getByText('More information requested')).toBeTruthy();
    expect(screen.getByText('Please add a working demo link and deployment notes.')).toBeTruthy();
    expect(screen.getByText(/Requested by Test Steward/)).toBeTruthy();
  });

  it('uses structured more-info requests instead of duplicating staff response', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'more_info_needed',
          state_display: 'More Information Needed',
          staff_reply: 'Please add more evidence.',
          more_info_requests: [
            {
              id: 2,
              message: 'Please add more evidence.',
              user_name: 'Test Steward',
              created_at: '2026-06-02T12:00:00Z'
            }
          ]
        }),
        notes: []
      }
    });

    expect(screen.getByText('More information requested')).toBeTruthy();
    expect(screen.queryByText('Staff Response')).toBeNull();
  });

  it('shows final staff response after a historical more-info request', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'accepted',
          state_display: 'Accepted',
          staff_reply: 'Accepted after the follow-up evidence.',
          more_info_requests: [
            {
              id: 3,
              message: 'Please add more evidence.',
              user_name: 'Test Steward',
              created_at: '2026-06-02T12:00:00Z'
            }
          ]
        }),
        notes: []
      }
    });

    expect(screen.getByText('More information requested')).toBeTruthy();
    expect(screen.getByText('Staff Response')).toBeTruthy();
    expect(screen.getByText('Accepted after the follow-up evidence.')).toBeTruthy();
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

  it('shows the proposal overall reason in the existing project rubric', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'accept',
          proposed_by: 21,
          proposed_by_details: { name: 'Proposal Reviewer' },
          proposed_user_details: {
            id: 9,
            name: 'Project Builder',
            address: '0x1234567890abcdef',
            display_name: 'Project Builder'
          },
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
            extras: ['live_deployment'],
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
          7: ['accept', 'reject', 'propose']
        },
        contributionTypes: [
          {
            id: 7,
            name: 'Builder Project',
            category: 'builder',
            min_points: 0,
            max_points: 100,
            review_flow: 'builder_project',
            rubric_extra_points: 2
          }
        ],
        multipliers: { 7: 1 },
        templates: [],
        notes: [],
        currentUserId: 21,
        enableRubricReview: true
      }
    });

    await waitFor(() => {
      expect(screen.getByText('Project rubric')).toBeTruthy();
      expect(screen.getByText('Overall reason')).toBeTruthy();
      expect(screen.getByText('The proposal has enough evidence to accept.')).toBeTruthy();
    });
    expect(screen.queryByText('Proposal evaluation')).toBeNull();
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
            max_points: 200,
            review_flow: 'builder_project',
            rubric_extra_points: 2
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
      expect(pointsInput.value).toBe('52');
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

  it('lets final reviewers question pending proposals with feedback', async () => {
    const onQuestionProposal = vi.fn().mockResolvedValue();
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'reject',
          proposed_staff_reply: 'Rejecting too quickly.',
          proposed_by: 21,
          proposed_by_details: { name: 'Proposal Reviewer' },
          proposal_review_status: 'pending_review'
        }),
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose: vi.fn(),
        onQuestionProposal,
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
        currentUserId: 22,
        enableRubricReview: true
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Question proposal' }));
    await fireEvent.input(screen.getByLabelText('Feedback to reviewer'), {
      target: { value: 'Please check the repository evidence first.' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Send feedback' }));

    await waitFor(() => {
      expect(onQuestionProposal).toHaveBeenCalledWith(
        42,
        'Please check the repository evidence first.'
      );
    });
  });

  it('lets final reviewers question proposals on more-info submissions', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'more_info_needed',
          state_display: 'More Information Needed',
          has_proposal: true,
          proposed_action: 'reject',
          proposed_staff_reply: 'Rejecting too quickly.',
          proposed_by: 21,
          proposed_by_details: { name: 'Proposal Reviewer' },
          proposal_review_status: 'pending_review',
          more_info_requests: []
        }),
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose: vi.fn(),
        onQuestionProposal: vi.fn().mockResolvedValue(),
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
        currentUserId: 22,
        enableRubricReview: true
      }
    });

    expect(screen.getByRole('button', { name: 'Question proposal' })).toBeTruthy();
  });

  it('preserves typed question feedback if the proposal becomes non-questionable mid-edit', async () => {
    const pendingProposal = makeSubmission({
      has_proposal: true,
      proposed_action: 'reject',
      proposed_staff_reply: 'Rejecting too quickly.',
      proposed_by: 21,
      proposed_by_details: { name: 'Proposal Reviewer' },
      proposal_review_status: 'pending_review'
    });
    const { rerender } = render(SubmissionCard, {
      props: {
        submission: pendingProposal,
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose: vi.fn(),
        onQuestionProposal: vi.fn().mockResolvedValue(),
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
        currentUserId: 22,
        enableRubricReview: true
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Question proposal' }));
    await fireEvent.input(screen.getByLabelText('Feedback to reviewer'), {
      target: { value: 'Draft feedback that should not be lost.' }
    });

    await rerender({
      submission: makeSubmission({
        id: pendingProposal.id,
        has_proposal: true,
        proposed_action: 'reject',
        proposed_by: 21,
        proposed_by_details: { name: 'Proposal Reviewer' },
        proposal_review_status: 'questioned',
        proposal_review_feedback: 'Someone else already questioned this proposal.'
      })
    });

    expect(screen.queryByLabelText('Feedback to reviewer')).toBeNull();

    await rerender({ submission: pendingProposal });
    await fireEvent.click(screen.getByRole('button', { name: 'Question proposal' }));

    expect(screen.getByLabelText('Feedback to reviewer').value).toBe(
      'Draft feedback that should not be lost.'
    );
  });

  it('shows questioned proposal feedback and hides final review actions from other stewards', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'reject',
          proposed_by: 21,
          proposed_by_details: { name: 'Proposal Reviewer' },
          proposal_review_status: 'questioned',
          proposal_review_feedback: 'Please check the repository evidence first.',
          proposal_questioned_by_details: { name: 'Senior Steward' },
          proposal_questioned_at: '2026-06-03T12:00:00Z'
        }),
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose: vi.fn(),
        onQuestionProposal: vi.fn(),
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
        currentUserId: 22,
        enableRubricReview: true
      }
    });

    expect(screen.getByText('Questioned')).toBeTruthy();
    expect(screen.getByText(/Feedback from Senior Steward/)).toBeTruthy();
    expect(screen.getByText('Please check the repository evidence first.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Reject Submission' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Accept & Create Contribution' })).toBeNull();
  });

  it('lets the original proposer revise a questioned proposal from the proposal form', async () => {
    const onPropose = vi.fn();
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposed_action: 'reject',
          proposed_staff_reply: 'Rejecting too quickly.',
          proposed_by: 21,
          proposed_by_details: { name: 'Proposal Reviewer' },
          proposal_review_status: 'questioned',
          proposal_review_feedback: 'Please check the repository evidence first.',
          rubric_review: {
            action: 'reject',
            confidence: 'medium',
            gate_failures: [],
            sections: {
              genlayer_fit: { score: 1, reason: '' },
              contract_quality: { score: 1, reason: '' },
              engineering: { score: 1, reason: '' },
              frontend_ux: { score: 1, reason: '' }
            },
            extras: [],
            overall_reason: 'The reviewer still thinks this should be rejected.'
          }
        }),
        showReviewForm: true,
        onReview: vi.fn(),
        onPropose,
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
        currentUserId: 21,
        enableRubricReview: true
      }
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Submit Reject Proposal' })).toBeTruthy();
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Submit Reject Proposal' }));

    await waitFor(() => {
      expect(onPropose).toHaveBeenCalledTimes(1);
    });
    expect(onPropose.mock.calls[0][1]).toEqual(expect.objectContaining({
      proposed_action: 'reject',
      proposed_staff_reply: 'Rejecting too quickly.'
    }));
  });
});
