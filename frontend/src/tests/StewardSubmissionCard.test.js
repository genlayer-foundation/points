import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte/svelte5';
import { describe, expect, it, vi } from 'vitest';
import StewardSubmissionCard from '../components/StewardSubmissionCard.svelte';

const contributionType = {
  id: 7,
  name: 'Builder Project',
  category: 'builder',
  min_points: 0,
  max_points: 100,
  review_flow: null
};

function makeAIAnalysis() {
  return {
    id: 77,
    action: 'accept',
    confidence: 'high',
    sections: {
      genlayer_fit: { score: 4, reason: 'GenLayer is central to the project.' },
      contract_quality: { score: 3, reason: 'The contract is well structured.' },
      engineering: { score: 4, reason: 'The repository is maintainable.' },
      frontend_ux: { score: 3, reason: 'The application is usable.' }
    },
    synthesis: 'The project meets the review bar.'
  };
}

function makeSubmission(overrides = {}) {
  return {
    id: 42,
    user: 9,
    user_details: {
      id: 9,
      name: 'Project Builder',
      address: '0x1234567890abcdef',
      profile_image_url: 'https://example.com/project-builder.png',
      github_connection: { platform_username: 'builder-gh' },
      twitter_connection: { platform_username: 'builder-x' },
      discord_connection: { platform_username: 'builder-discord' }
    },
    contribution_type: 7,
    contribution_type_details: contributionType,
    contribution_date: '2026-06-01T12:00:00Z',
    created_at: '2026-06-01T12:00:00Z',
    notes: 'Project submission notes with enough detail for the reviewer.',
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
    proposal_review_status: null,
    proposal_review_feedback: '',
    proposal_is_ai: false,
    rubric_review: null,
    ai_analysis: null,
    notes_count: 0,
    is_interesting: false,
    has_appeal: false,
    appeal_reason: '',
    more_info_requests: [],
    mission: null,
    contribution: null,
    project_contribution: null,
    ...overrides
  };
}

function renderCard(props = {}) {
  return render(StewardSubmissionCard, {
    props: {
      submission: makeSubmission(),
      showReviewForm: false,
      contributionTypes: [contributionType],
      notes: [],
      ...props
    }
  });
}

function reviewProps({ permissions, onReview = vi.fn(), onPropose = vi.fn() }) {
  return {
    submission: makeSubmission(),
    showReviewForm: true,
    onReview,
    onPropose,
    reviewData: {
      action: 'accept',
      user: 9,
      contribution_type: 7,
      points: 0,
      staff_reply: ''
    },
    permissions: { 7: permissions },
    contributionTypes: [contributionType],
    multipliers: { 7: 1 },
    templates: [],
    notes: [],
    enableRubricReview: false
  };
}

describe('StewardSubmissionCard', () => {
  it('consolidates the submitter profile, avatar, socials, and submission date in the header', () => {
    renderCard();

    const profileLink = screen.getByRole('link', { name: 'View Project Builder profile' });
    expect(profileLink.getAttribute('href')).toBe('/participant/9');
    expect(screen.getByRole('img', { name: 'Project Builder' })).toBeTruthy();
    expect(screen.getByText('View profile')).toBeTruthy();
    expect(screen.getByText(/Submitted /)).toBeTruthy();

    const githubLink = screen.getByRole('link', { name: 'GitHub: @builder-gh' });
    const xLink = screen.getByRole('link', { name: 'X: @builder-x' });
    expect(githubLink.getAttribute('href')).toBe('https://github.com/builder-gh');
    expect(xLink.getAttribute('href')).toBe('https://x.com/builder-x');
    expect(screen.getByLabelText('Discord: builder-discord')).toBeTruthy();
  });

  it('keeps submission and internal notes collapsed until requested', async () => {
    renderCard({
      submission: makeSubmission({ notes_count: 1 }),
      notes: [{
        id: 13,
        user_name: 'Steward One',
        message: 'Private stewardship note',
        created_at: '2026-06-02T12:00:00Z'
      }]
    });

    const submissionNotes = screen.getByRole('button', { name: 'Show submission notes' });
    const internalNotes = screen.getByRole('button', { name: 'Show internal notes' });
    expect(submissionNotes.getAttribute('aria-expanded')).toBe('false');
    expect(internalNotes.getAttribute('aria-expanded')).toBe('false');
    expect(document.getElementById('submission-notes-42')).toBeNull();
    expect(document.getElementById('internal-notes-42')).toBeNull();
    expect(screen.queryByText('Private stewardship note')).toBeNull();
    expect(screen.queryByPlaceholderText('Add a note...')).toBeNull();

    await fireEvent.click(submissionNotes);
    expect(screen.getByRole('button', { name: 'Hide submission notes' }).getAttribute('aria-expanded')).toBe('true');
    expect(document.getElementById('submission-notes-42')).toBeTruthy();

    await fireEvent.click(internalNotes);
    expect(screen.getByRole('button', { name: 'Hide internal notes' }).getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByText('Private stewardship note')).toBeTruthy();
    expect(screen.getByPlaceholderText('Add a note...')).toBeTruthy();
  });

  it('shows the compact AI proposal context without a competing human proposal', () => {
    const aiAnalysis = makeAIAnalysis();
    renderCard({
      submission: makeSubmission({
        has_proposal: true,
        proposal_is_ai: true,
        proposed_action: 'accept',
        proposed_by_details: { name: 'AI Steward' },
        ai_analysis: aiAnalysis
      })
    });

    expect(screen.getByRole('button', { name: 'Show AI review synthesis' })).toBeTruthy();
    expect(screen.getByText(/Recommends Accept/)).toBeTruthy();
    expect(screen.queryByText(aiAnalysis.synthesis)).toBeNull();
    expect(screen.queryByText('Human proposal')).toBeNull();
    expect(screen.queryByText('AI Steward')).toBeNull();
  });

  it('shows a human proposal instead of the historical AI summary', () => {
    renderCard({
      submission: makeSubmission({
        has_proposal: true,
        proposal_is_ai: false,
        proposed_action: 'reject',
        proposed_by: 21,
        proposed_by_details: { name: 'Human Reviewer' },
        proposed_at: '2026-06-02T12:00:00Z',
        proposal_review_status: 'pending_review',
        ai_analysis: makeAIAnalysis()
      })
    });

    expect(screen.getByText('Human proposal')).toBeTruthy();
    expect(screen.getByText('Human Reviewer')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Show AI review synthesis' })).toBeNull();
    expect(screen.queryByText('AI review')).toBeNull();
  });

  it('lets a different direct reviewer question a pending human proposal in a dialog', async () => {
    const onQuestionProposal = vi.fn().mockResolvedValue();
    renderCard({
      ...reviewProps({ permissions: ['accept'] }),
      submission: makeSubmission({
        has_proposal: true,
        proposal_is_ai: false,
        proposed_action: 'accept',
        proposed_by: 21,
        proposed_by_details: { name: 'Human Reviewer' },
        proposed_at: '2026-06-02T12:00:00Z',
        proposal_review_status: 'pending_review'
      }),
      currentUserId: 22,
      onQuestionProposal
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Question proposal' }));
    const dialog = screen.getByRole('dialog', { name: 'Question proposal' });
    await fireEvent.input(within(dialog).getByLabelText('Feedback'), {
      target: { value: 'Please re-check the deployment evidence before accepting.' }
    });
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Question proposal' }));

    await waitFor(() => {
      expect(onQuestionProposal).toHaveBeenCalledWith(
        42,
        'Please re-check the deployment evidence before accepting.'
      );
    });
    expect(screen.queryByRole('dialog', { name: 'Question proposal' })).toBeNull();
  });

  it('renders all builder project rubric rows and reviews immutable frontend AI analysis', async () => {
    const builderProjectType = {
      ...contributionType,
      review_flow: 'builder_project'
    };
    const aiAnalysis = makeAIAnalysis();
    aiAnalysis.sections.frontend_ux = {
      score: 3,
      reason: 'Immutable AI frontend assessment.'
    };
    renderCard({
      ...reviewProps({ permissions: ['accept', 'reject'] }),
      submission: makeSubmission({
        contribution_type_details: builderProjectType,
        has_proposal: true,
        proposal_is_ai: false,
        proposed_action: 'accept',
        proposed_by: 21,
        proposed_by_details: { name: 'Human Reviewer' },
        proposal_review_status: 'pending_review',
        rubric_review: {
          action: 'accept',
          gate_failures: [],
          sections: {
            genlayer_fit: { score: 4, reason: 'Human fit assessment.' },
            contract_quality: { score: 4, reason: 'Human contract assessment.' },
            engineering: { score: 4, reason: 'Human engineering assessment.' },
            frontend_ux: { score: 1, reason: 'Human frontend assessment.' }
          },
          extras: [],
          overall_reason: 'Human proposal rationale.'
        },
        ai_analysis: aiAnalysis
      }),
      contributionTypes: [builderProjectType],
      permissions: { 7: ['accept', 'reject'] },
      currentUserId: 22,
      enableRubricReview: true
    });

    expect(screen.getByLabelText('GenLayer fit')).toBeTruthy();
    expect(screen.getByLabelText('Contract quality')).toBeTruthy();
    expect(screen.getByLabelText('Engineering')).toBeTruthy();
    expect(screen.getByLabelText('Frontend / UX')).toBeTruthy();
    const benchmarkMenu = screen.getByLabelText('Open AI feedback section');
    expect([...benchmarkMenu.options].map(option => option.value)).toEqual([
      '',
      'decision',
      'genlayer_fit',
      'contract_quality',
      'engineering',
      'frontend_ux',
      'synthesis'
    ]);

    const feedbackButtons = screen.getAllByRole('button', { name: 'Flag AI issue' });
    expect(feedbackButtons).toHaveLength(4);
    await fireEvent.click(feedbackButtons[3]);

    const dialog = await screen.findByRole('dialog', { name: 'Review Frontend / UX' });
    expect(within(dialog).getByText('3 / 5')).toBeTruthy();
    expect(within(dialog).getByText('Immutable AI frontend assessment.')).toBeTruthy();
    expect(within(dialog).queryByText('Human frontend assessment.')).toBeNull();
  });

  it('routes every outcome through proposals for a proposal-only steward', async () => {
    const onReview = vi.fn();
    const onPropose = vi.fn();
    renderCard(reviewProps({ permissions: ['propose'], onReview, onPropose }));

    await waitFor(() => {
      expect(screen.getByRole('group', { name: 'Review outcome' })).toBeTruthy();
      expect(['Accept', 'Request info', 'Reject'].map(name =>
        screen.getByRole('button', { name, exact: true }).textContent.trim()
      )).toEqual([
        'Accept',
        'Request info',
        'Reject'
      ]);
      expect(screen.getByRole('button', { name: 'Propose acceptance' })).toBeTruthy();
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Propose acceptance' }));
    await fireEvent.click(screen.getByRole('button', { name: 'Request info', exact: true }));
    await fireEvent.click(screen.getByRole('button', { name: 'Propose requesting information' }));
    await fireEvent.click(screen.getByRole('button', { name: 'Reject', exact: true }));
    await fireEvent.click(screen.getByRole('button', { name: 'Propose rejection' }));

    expect(onReview).not.toHaveBeenCalled();
    expect(onPropose).toHaveBeenCalledTimes(3);
    expect(onPropose.mock.calls.map(([, payload]) => payload.proposed_action)).toEqual([
      'accept',
      'more_info',
      'reject'
    ]);
    expect(onPropose).toHaveBeenNthCalledWith(1, 42, expect.objectContaining({
      proposed_action: 'accept',
      proposed_contribution_type: 7,
      proposed_user: 9
    }));
  });

  it('uses a proposal only for outcomes without direct authority in a mixed permission set', async () => {
    const onReview = vi.fn();
    const onPropose = vi.fn();
    renderCard(reviewProps({
      permissions: ['propose', 'reject', 'request_more_info'],
      onReview,
      onPropose
    }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Propose acceptance' })).toBeTruthy());
    await fireEvent.click(screen.getByRole('button', { name: 'Propose acceptance' }));

    await fireEvent.click(screen.getByRole('button', { name: 'Reject', exact: true }));
    expect(screen.getByText('Final decision')).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Reject submission' }));

    await fireEvent.click(screen.getByRole('button', { name: 'Request info', exact: true }));
    expect(screen.getByText('Final decision')).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Request information' }));

    expect(onPropose).toHaveBeenCalledTimes(1);
    expect(onPropose).toHaveBeenCalledWith(42, expect.objectContaining({
      proposed_action: 'accept'
    }));
    expect(onReview).toHaveBeenCalledTimes(2);
    expect(onReview.mock.calls.map(([, payload]) => payload.action)).toEqual([
      'reject',
      'more_info'
    ]);
  });

  it('keeps reviewer notes and template IDs scoped to their outcome', async () => {
    const onReview = vi.fn();
    renderCard({
      ...reviewProps({ permissions: ['accept', 'reject'], onReview }),
      submission: makeSubmission({
        has_proposal: true,
        proposal_is_ai: false,
        proposed_action: 'accept',
        proposed_staff_reply: 'The project looks ready to accept.',
        proposed_template: 11,
        proposed_by: 21,
        proposed_by_details: { name: 'Human Reviewer' },
        proposal_review_status: 'pending_review'
      }),
      templates: [
        { id: 11, action: 'accept', label: 'Accept template', text: 'The project looks ready to accept.' },
        { id: 12, action: 'reject', label: 'Reject template', text: 'The deployment cannot be verified.' }
      ],
      currentUserId: 22
    });

    const response = await screen.findByLabelText('Reviewer note (optional)');
    expect(response.value).toBe('The project looks ready to accept.');

    await fireEvent.click(screen.getByRole('button', { name: 'Reject', exact: true }));
    const rejection = screen.getByLabelText('Rejection reason');
    expect(rejection.value).toBe('');
    await fireEvent.input(rejection, { target: { value: 'The deployment cannot be verified.' } });

    await fireEvent.click(screen.getByRole('button', { name: 'Accept', exact: true }));
    expect(screen.getByLabelText('Reviewer note (optional)').value).toBe('The project looks ready to accept.');

    await fireEvent.click(screen.getByRole('button', { name: 'Reject', exact: true }));
    expect(screen.getByLabelText('Rejection reason').value).toBe('The deployment cannot be verified.');
    await fireEvent.click(screen.getByRole('button', { name: 'Reject submission' }));

    expect(onReview).toHaveBeenCalledWith(42, expect.objectContaining({
      action: 'reject',
      staff_reply: 'The deployment cannot be verified.',
      template_id: null
    }));
  });

  it('does not hydrate an unavailable proposal outcome into a permitted fallback', async () => {
    const onReview = vi.fn();
    renderCard({
      ...reviewProps({ permissions: ['reject'], onReview }),
      submission: makeSubmission({
        has_proposal: true,
        proposal_is_ai: false,
        proposed_action: 'accept',
        proposed_staff_reply: 'The project looks ready to accept.',
        proposed_template: 11,
        proposed_by: 21,
        proposed_by_details: { name: 'Human Reviewer' },
        proposal_review_status: 'pending_review'
      }),
      templates: [
        { id: 11, action: 'accept', label: 'Accept template', text: 'The project looks ready to accept.' },
        { id: 12, action: 'reject', label: 'Reject template', text: 'The deployment cannot be verified.' }
      ],
      currentUserId: 22
    });

    const rejection = await screen.findByLabelText('Rejection reason');
    expect(rejection.value).toBe('');
    await fireEvent.click(screen.getByRole('button', { name: 'Reject submission' }));

    expect(onReview).toHaveBeenCalledWith(42, expect.objectContaining({
      action: 'reject',
      staff_reply: '',
      template_id: null
    }));
  });
});
