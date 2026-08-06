import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { get } from 'svelte/store';
import { push } from 'svelte-spa-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SubmissionCard from '../components/SubmissionCard.svelte';
import { toastStore } from '../lib/toastStore.js';

function makeSubmission(overrides = {}) {
  return {
    id: 42,
    contribution_type: 7,
    contribution_type_name: 'Builder Project',
    contribution_type_details: {
      id: 7,
      name: 'Builder Project',
      category: 'builder',
      min_points: 0,
      max_points: 100
    },
    contribution_date: '2026-06-01T12:00:00Z',
    created_at: '2026-06-01T12:00:00Z',
    notes: 'Project submission notes',
    state: 'pending',
    state_display: 'Pending Review',
    staff_reply: '',
    evidence_items: [],
    more_info_requests: [],
    mission: null,
    project_contribution: null,
    milestone_version: null,
    contribution: null,
    has_appeal: false,
    ...overrides
  };
}

describe('SubmissionCard', () => {
  let originalClipboard;
  let originalExecCommand;

  beforeEach(() => {
    originalClipboard = navigator.clipboard;
    originalExecCommand = document.execCommand;
    vi.clearAllMocks();
    toastStore.clearAll();
  });

  afterEach(() => {
    Object.defineProperty(navigator, 'clipboard', {
      value: originalClipboard,
      configurable: true
    });
    if (originalExecCommand) document.execCommand = originalExecCommand;
    else delete document.execCommand;
  });

  it('renders only submitter-facing submission metadata', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          has_proposal: true,
          proposal_is_ai: true,
          proposed_action: 'reject',
          proposed_by_details: { name: 'Private AI Steward' },
          proposed_staff_reply: 'Private proposed rejection reason',
          rubric_review: { overall_reason: 'Private rubric rationale' },
          notes_count: 4,
          ai_analysis: { synthesis: 'Private AI synthesis' }
        })
      }
    });

    expect(screen.getByRole('heading', { name: 'Builder Project' })).toBeTruthy();
    expect(screen.getByText('Pending Review')).toBeTruthy();
    expect(screen.queryByText('Proposal')).toBeNull();
    expect(screen.queryByText('4 notes')).toBeNull();
    expect(screen.queryByText('Private AI synthesis')).toBeNull();
    expect(screen.queryByText('Review outcome')).toBeNull();
    expect(screen.queryByText('Private AI Steward')).toBeNull();
    expect(screen.queryByText('Private proposed rejection reason')).toBeNull();
    expect(screen.queryByText('Private rubric rationale')).toBeNull();
  });

  it('copies only the submission id from the card', async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true
    });

    render(SubmissionCard, {
      props: { submission: makeSubmission({ id: 'submission-123' }) }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Copy ID' }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('submission-123');
    });
  });

  it('reports a rejected legacy clipboard copy and removes its textarea', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      value: undefined,
      configurable: true
    });
    document.execCommand = vi.fn().mockReturnValue(false);
    render(SubmissionCard, {
      props: { submission: makeSubmission({ id: 'submission-123' }) }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Copy ID' }));

    await waitFor(() => {
      expect(get(toastStore)).toEqual(expect.arrayContaining([
        expect.objectContaining({
          type: 'error',
          message: 'Failed to copy submission ID: Clipboard copy was rejected'
        })
      ]));
    });
    expect(document.querySelector('textarea')).toBeNull();
  });

  it('shows mission, milestone, and linked project details', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          contribution_type_name: 'Milestone',
          contribution_type_details: {
            id: 8,
            name: 'Milestone',
            category: 'builder',
            slug: 'milestones'
          },
          mission: { id: 15, name: 'Build the Future' },
          milestone_version: 3,
          project_contribution: {
            title: 'Reference Project',
            link: 'https://example.com/project',
            github_url: 'https://github.com/example/project'
          }
        })
      }
    });

    expect(screen.getByRole('heading', { name: /Build the Future/ })).toBeTruthy();
    expect(screen.getByText('Milestone')).toBeTruthy();
    expect(screen.getByText('Milestone v3')).toBeTruthy();
    expect(screen.getByText('Reference Project')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'View Project' }).getAttribute('href')).toBe('https://example.com/project');
    expect(screen.getByRole('link', { name: 'Project Repository' }).getAttribute('href')).toBe('https://github.com/example/project');
  });

  it('shows submission notes and both evidence formats', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          notes: '**Implemented** the complete flow.',
          evidence_items: [
            {
              id: 1,
              description: 'Pull request',
              url: 'https://github.com/example/project/pull/1',
              url_type: { name: 'GitHub' }
            },
            { id: 2, description: 'Tested by the project team', url: '' }
          ]
        })
      }
    });

    expect(screen.getByText('Implemented')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'https://github.com/example/project/pull/1' })).toBeTruthy();
    expect(screen.getByText('Tested by the project team')).toBeTruthy();
  });

  it('uses structured more-info requests instead of duplicating the staff response', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'more_info_needed',
          state_display: 'More Information Needed',
          staff_reply: 'Please add more evidence.',
          more_info_requests: [{
            id: 2,
            message: 'Please add more evidence.',
            user_name: 'Test Steward',
            created_at: '2026-06-02T12:00:00Z'
          }]
        })
      }
    });

    expect(screen.getByText('More information requested')).toBeTruthy();
    expect(screen.getByText('Please add more evidence.')).toBeTruthy();
    expect(screen.getByText(/Requested by Test Steward/)).toBeTruthy();
    expect(screen.queryByText('Staff Response')).toBeNull();
  });

  it('renders each submitter response separately from the steward request', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'pending',
          more_info_requests: [{
            id: 2,
            message: 'Please add repository setup instructions.',
            user_name: 'Test Steward',
            created_at: '2026-06-02T12:00:00Z',
            response: {
              id: 4,
              message: 'Added a setup section to the README.',
              user_name: 'Project Builder',
              created_at: '2026-06-03T12:00:00Z'
            }
          }]
        })
      }
    });

    expect(screen.getByText('Please add repository setup instructions.')).toBeTruthy();
    expect(screen.getByText('Your response')).toBeTruthy();
    expect(screen.getByText('Added a setup section to the README.')).toBeTruthy();
  });

  it('requires an inline response before directly resubmitting unchanged details', async () => {
    const onResubmit = vi.fn().mockResolvedValue();
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'more_info_needed',
          state_display: 'More Information Needed',
          more_info_requests: [{
            id: 23,
            message: 'Document the latest repository changes.',
            response: null
          }]
        }),
        onResubmit
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Resubmit' }));
    const responseInput = screen.getByRole('textbox', { name: 'What did you change?' });
    const sendButton = screen.getByRole('button', { name: 'Send response and resubmit' });
    expect(responseInput.required).toBe(true);
    expect(responseInput.maxLength).toBe(1000);
    expect(sendButton.disabled).toBe(true);

    await fireEvent.input(responseInput, {
      target: { value: '  Updated the repository and release notes.  ' }
    });
    expect(sendButton.disabled).toBe(false);
    await fireEvent.click(sendButton);

    await waitFor(() => {
      expect(onResubmit).toHaveBeenCalledWith(42, {
        request_id: 23,
        message: 'Updated the repository and release notes.'
      });
    });
  });

  it('keeps the inline response open and surfaces resubmission errors', async () => {
    const onResubmit = vi.fn().mockRejectedValue({
      response: {
        data: {
          evidence_items: 'At least one current evidence URL is required.'
        }
      }
    });
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'more_info_needed',
          state_display: 'More Information Needed',
          more_info_requests: [{
            id: 23,
            message: 'Add current evidence.',
            response: null
          }]
        }),
        onResubmit
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Resubmit' }));
    await fireEvent.input(screen.getByRole('textbox', { name: 'What did you change?' }), {
      target: { value: 'Updated the repository evidence.' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Send response and resubmit' }));

    expect((await screen.findByRole('alert')).textContent).toContain(
      'At least one current evidence URL is required.'
    );
    expect(screen.getByRole('textbox', { name: 'What did you change?' })).toBeTruthy();
  });

  it('shows the final staff response and awarded contribution after acceptance', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'accepted',
          state_display: 'Accepted',
          staff_reply: 'Accepted after the follow-up evidence.',
          more_info_requests: [{ id: 3, message: 'Please add more evidence.' }],
          contribution: {
            id: 99,
            contribution_type: 7,
            contribution_type_details: {
              id: 7,
              name: 'Builder Project',
              category: 'builder'
            },
            contribution_date: '2026-06-01T12:00:00Z',
            frozen_global_points: 42
          }
        })
      }
    });

    expect(screen.getByText('Staff Response')).toBeTruthy();
    expect(screen.getByText('Accepted after the follow-up evidence.')).toBeTruthy();
    expect(screen.getByText('42 pts')).toBeTruthy();
  });

  it('submits a trimmed appeal reason for a rejected submission', async () => {
    const onAppeal = vi.fn().mockResolvedValue();
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'rejected',
          state_display: 'Rejected',
          staff_reply: 'The evidence does not support the claim.'
        }),
        onAppeal
      }
    });

    expect(screen.getByText('Rejection Reason')).toBeTruthy();
    const submitButton = screen.getByRole('button', { name: 'Submit Appeal' });
    expect(submitButton.disabled).toBe(true);

    await fireEvent.input(screen.getByLabelText('Appeal reason'), {
      target: { value: '  The missing evidence is now attached.  ' }
    });
    await fireEvent.click(submitButton);

    await waitFor(() => {
      expect(onAppeal).toHaveBeenCalledWith(42, 'The missing evidence is now attached.');
    });
    expect(screen.getByLabelText('Appeal reason').value).toBe('');
  });

  it('keeps Appeal available while routing rejected Resubmit to a new form', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          id: 'rejected-42',
          state: 'rejected',
          state_display: 'Rejected',
          staff_reply: 'Correct the evidence and try again.'
        }),
        onAppeal: vi.fn()
      }
    });

    expect(screen.getByRole('button', { name: 'Submit Appeal' })).toBeTruthy();
    expect(screen.getByText(/creates a new, editable contribution/)).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Resubmit' }));
    expect(push).toHaveBeenCalledWith('/submit-contribution?resubmit=rejected-42');
  });

  it('does not offer a second appeal and shows an appeal under review', () => {
    const { unmount } = render(SubmissionCard, {
      props: {
        submission: makeSubmission({
          state: 'rejected',
          state_display: 'Rejected',
          has_appeal: true
        }),
        onAppeal: vi.fn()
      }
    });

    expect(screen.getByText(/already appealed this submission/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Submit Appeal' })).toBeNull();
    unmount();

    render(SubmissionCard, {
      props: {
        submission: makeSubmission({ has_appeal: true })
      }
    });
    expect(screen.getByText('Your appeal is under review')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull();
  });

  it('opens the contribution editor with mission context when available', async () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({ mission: { id: 15, name: 'Build the Future' } })
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));

    expect(push).toHaveBeenCalledWith('/contributions/42?mission=15');
  });

  it('renders a terminal canceled state without edit actions', () => {
    render(SubmissionCard, {
      props: {
        submission: makeSubmission({ state: 'canceled', state_display: 'Canceled' })
      }
    });

    expect(screen.getByText('Canceled by user')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull();
  });
});
