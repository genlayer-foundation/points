import { fireEvent, render, screen, waitFor, within } from '@testing-library/svelte/svelte5';
import { push } from 'svelte-spa-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import EditSubmission from '../routes/EditSubmission.svelte';

const mocks = vi.hoisted(() => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  },
  getAllContributionTypes: vi.fn(),
  getContributionType: vi.fn(),
  getMission: vi.fn(),
  getAcceptedProjects: vi.fn(),
  getMissions: vi.fn(),
  trackEvent: vi.fn()
}));

vi.mock('../lib/api.js', () => ({
  default: mocks.api,
  contributionsAPI: {
    getAllContributionTypes: mocks.getAllContributionTypes,
    getContributionType: mocks.getContributionType,
    getMission: mocks.getMission
  },
  submissionsAPI: {
    getAcceptedProjects: mocks.getAcceptedProjects
  }
}));

vi.mock('../lib/missionsStore.js', () => ({
  getMissions: mocks.getMissions
}));

vi.mock('../lib/analytics.js', () => ({
  getAnalyticsContext: (properties) => properties,
  getLifecycleDurationMs: () => 0,
  getLifecycleDurations: () => ({}),
  markLifecycleTime: () => false,
  trackEvent: mocks.trackEvent
}));

vi.mock('../lib/auth.js', async () => {
  const { readable } = await import('svelte/store');
  return {
    authState: readable({
      isAuthenticated: true,
      address: '0xcommunity',
      loading: false,
      error: null
    })
  };
});

vi.mock('../lib/userStore.js', async () => {
  const { readable } = await import('svelte/store');
  return {
    userStore: readable({
      user: {
        address: '0xcommunity',
        builder: true,
        validator: false,
        creator: false,
        twitter_connection: null,
        discord_connection: null,
        github_connection: null
      },
      loading: false,
      error: null
    })
  };
});

const genericEvidenceType = {
  id: 91,
  name: 'Other',
  slug: 'other',
  is_generic: true,
  order: 99,
  url_patterns: []
};

const communityType = {
  id: 3,
  name: 'Community Event',
  slug: 'community-event',
  category: 'community',
  description: 'Organize and document a community event.',
  is_submittable: true,
  is_full: false,
  user_weekly_is_full: false,
  min_points: 10,
  max_points: 40,
  accepted_evidence_url_types: [genericEvidenceType],
  required_evidence_url_types: [],
  required_social_accounts: [],
  required_discord_roles: []
};

const builderType = {
  ...communityType,
  id: 1,
  name: 'Builder Project',
  slug: 'projects',
  category: 'builder'
};

const validatorType = {
  ...communityType,
  id: 2,
  name: 'Validator Testing',
  slug: 'validator-testing',
  category: 'validator'
};

const otherCommunityType = {
  ...communityType,
  id: 4,
  name: 'Community AMA',
  slug: 'community-ama'
};

function makeSubmission(overrides = {}) {
  return {
    id: 42,
    can_edit: true,
    has_appeal: false,
    state: 'pending',
    contribution_type: communityType.id,
    contribution_type_name: communityType.name,
    contribution_type_details: {
      id: communityType.id,
      name: communityType.name,
      slug: communityType.slug,
      category: communityType.category
    },
    contribution_date: '2026-07-18T12:00:00Z',
    title: 'Community call recap',
    notes: 'Hosted the weekly call and published the recording.',
    staff_reply: '',
    more_info_requests: [],
    mission: null,
    project_contribution: null,
    milestone_version: null,
    evidence_items: [
      {
        id: 81,
        description: 'Event recording',
        url: 'https://example.com/community-call',
        url_type: genericEvidenceType
      }
    ],
    ...overrides
  };
}

function renderEditor(submission = makeSubmission()) {
  mocks.api.get.mockResolvedValue({ data: submission });
  return render(EditSubmission, {
    props: { params: { id: String(submission.id) } }
  });
}

describe('EditSubmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(Element.prototype, 'animate', {
      configurable: true,
      value: vi.fn(() => ({
        cancel: vi.fn(),
        currentTime: 0,
        effect: null,
        onfinish: null,
        playState: 'finished'
      }))
    });
    Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
      configurable: true,
      value: vi.fn(function showModal() {
        this.setAttribute('open', '');
      })
    });
    Object.defineProperty(HTMLDialogElement.prototype, 'close', {
      configurable: true,
      value: vi.fn(function close() {
        this.removeAttribute('open');
      })
    });
    mocks.api.put.mockResolvedValue({ data: {} });
    mocks.api.delete.mockResolvedValue({ data: {} });
    mocks.getAllContributionTypes.mockResolvedValue({
      data: [builderType, validatorType, communityType, otherCommunityType]
    });
    mocks.getContributionType.mockResolvedValue({ data: communityType });
    mocks.getMission.mockResolvedValue({ data: null });
    mocks.getAcceptedProjects.mockResolvedValue({ data: [] });
    mocks.getMissions.mockResolvedValue([]);
    sessionStorage.clear();
  });

  it('opens a pending Community submission in the current edit UI', async () => {
    renderEditor();

    expect(await screen.findByRole('heading', { name: 'Edit submission' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Submit Contribution' })).toBeNull();

    const communityTab = screen.getByRole('button', { name: 'Community' });
    expect(communityTab.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: 'Builder' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Validator' })).toBeTruthy();
    expect(await screen.findByDisplayValue('Community Event')).toBeTruthy();
    expect(screen.queryByText('Creators only')).toBeNull();
    expect(await screen.findByRole('button', { name: 'Save changes' })).toBeTruthy();
  });

  it('applies live role gating instead of exposing validator types', async () => {
    renderEditor();
    await screen.findByRole('button', { name: 'Save changes' });

    await fireEvent.click(screen.getByRole('button', { name: 'Validator' }));

    expect(await screen.findByText('Validators only')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Save changes' })).toBeNull();

    await fireEvent.click(screen.getByRole('button', { name: 'Community' }));
    expect(screen.queryByText('Creators only')).toBeNull();
    await fireEvent.click(
      screen.getByRole('button', { name: 'Open contribution type menu' })
    );
    expect(screen.queryByText('Community AMA')).toBeNull();
    await fireEvent.click(await screen.findByText('Community Event'));
    expect(await screen.findByRole('button', { name: 'Save changes' })).toBeTruthy();
  });

  it('blocks submissions that the API marks as non-editable', async () => {
    renderEditor(makeSubmission({ can_edit: false }));

    expect(
      await screen.findByRole('heading', { name: 'Submission unavailable' })
    ).toBeTruthy();
    expect(screen.getByText('This submission can no longer be edited.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull();
    expect(mocks.getAllContributionTypes).not.toHaveBeenCalled();
  });

  it('offers retry only for a transient submission load failure', async () => {
    mocks.api.get
      .mockRejectedValueOnce(new Error('Network unavailable'))
      .mockResolvedValueOnce({ data: makeSubmission() });
    render(EditSubmission, {
      props: { params: { id: '42' } }
    });

    expect(
      await screen.findByText("We couldn't load this submission. Please try again.")
    ).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { name: 'Edit submission' })).toBeTruthy();
    expect(mocks.api.get).toHaveBeenCalledTimes(2);
  });

  it('pauses appealed submissions while preserving the option to remove them', async () => {
    renderEditor(makeSubmission({ has_appeal: true, state: 'pending' }));

    expect(await screen.findByText('Editing is paused')).toBeTruthy();
    expect(screen.getByText('Appeal under review')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Save changes' })).toBeNull();
    expect(
      await screen.findByRole('button', { name: 'Remove submission' })
    ).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Community' }).disabled).toBe(true);
  });

  it('shows initialization errors when contribution details cannot be rendered', async () => {
    mocks.getAllContributionTypes.mockResolvedValue({ data: [] });
    mocks.getContributionType.mockRejectedValue(new Error('Type unavailable'));
    renderEditor();

    expect(
      await screen.findByText("This submission's contribution type could not be loaded.")
    ).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Save changes' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Remove submission' })).toBeTruthy();
  });

  it('preserves evidence ids and an existing mission without requiring recaptcha', async () => {
    const mission = {
      id: 12,
      name: 'Community activation',
      contribution_type: communityType.id,
      is_active: false
    };
    mocks.getMissions.mockResolvedValue([mission]);
    renderEditor(makeSubmission({ mission }));

    const saveButton = await screen.findByRole('button', { name: 'Save changes' });
    expect(screen.getByRole('button', { name: 'Builder' }).disabled).toBe(true);
    expect(screen.getByRole('button', { name: 'Validator' }).disabled).toBe(true);
    expect(screen.getByRole('button', { name: 'Community' }).disabled).toBe(true);
    expect(screen.getByDisplayValue('Community activation').disabled).toBe(true);
    expect(screen.queryByText(/reCAPTCHA/i)).toBeNull();

    await fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mocks.api.put).toHaveBeenCalledTimes(1);
    });
    const [path, payload] = mocks.api.put.mock.calls[0];
    expect(path).toBe('/submissions/42/');
    expect(payload).toMatchObject({
      contribution_type: communityType.id,
      contribution_date: '2026-07-18T00:00:00Z',
      title: 'Community call recap',
      notes: 'Hosted the weekly call and published the recording.',
      mission: mission.id,
      project_contribution: null,
      evidence_items: [
        {
          id: 81,
          description: 'Event recording',
          url: 'https://example.com/community-call'
        }
      ]
    });
    expect(payload).not.toHaveProperty('recaptcha');
    expect(mocks.getMissions).toHaveBeenCalledWith({ include_inactive: true });
    expect(mocks.getAcceptedProjects).toHaveBeenCalledWith(42);
    expect(push).toHaveBeenCalledWith('/my-submissions');
  });

  it('sends a required response separately when saving a more-info edit', async () => {
    renderEditor(makeSubmission({
      state: 'more_info_needed',
      contribution_type: builderType.id,
      contribution_type_name: builderType.name,
      contribution_type_details: {
        id: builderType.id,
        name: builderType.name,
        slug: builderType.slug,
        category: builderType.category
      },
      staff_reply: 'Add release documentation.',
      more_info_requests: [{
        id: 37,
        message: 'Add release documentation.',
        user_name: 'Builder Steward',
        created_at: '2026-07-19T12:00:00Z',
        response: null
      }]
    }));

    expect(await screen.findByText('Changes requested')).toBeTruthy();
    expect(screen.getByText('Add release documentation.')).toBeTruthy();
    const typeInput = await screen.findByDisplayValue('Builder Project');
    await waitFor(() => expect(typeInput.disabled).toBe(false));
    const responseInput = screen.getByRole('textbox', { name: 'What did you change?' });
    expect(screen.getByRole('button', { name: 'Save and resubmit' })).toBeTruthy();

    await fireEvent.input(responseInput, {
      target: { value: '  Added release and setup documentation.  ' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Save and resubmit' }));

    await waitFor(() => {
      expect(mocks.api.put).toHaveBeenCalledTimes(1);
    });
    const [, payload] = mocks.api.put.mock.calls[0];
    expect(payload.more_info_response).toEqual({
      request_id: 37,
      message: 'Added release and setup documentation.'
    });
    expect(payload.notes).toBe('Hosted the weekly call and published the recording.');
    expect(payload.evidence_items[0]).toMatchObject({ id: 81 });
    expect(payload).not.toHaveProperty('recaptcha');
    expect(sessionStorage.getItem('submissionUpdateSuccess')).toContain('back in review');
  });

  it('removes an editable submission from the branded confirmation dialog', async () => {
    renderEditor();
    await screen.findByRole('button', { name: 'Save changes' });

    await fireEvent.click(screen.getByRole('button', { name: 'Remove submission' }));
    const dialog = await screen.findByRole('alertdialog');
    expect(within(dialog).getByRole('heading', { name: 'Remove submission?' })).toBeTruthy();

    await fireEvent.click(
      within(dialog).getByRole('button', { name: 'Remove submission' })
    );

    await waitFor(() => {
      expect(mocks.api.delete).toHaveBeenCalledWith('/submissions/42/');
      expect(push).toHaveBeenCalledWith('/my-submissions');
    });
  });

  it('opens deletion as a modal and restores focus when cancellation closes it', async () => {
    renderEditor();
    await screen.findByRole('button', { name: 'Save changes' });

    const removeButton = screen.getByRole('button', { name: 'Remove submission' });
    removeButton.focus();
    await fireEvent.click(removeButton);

    const dialog = await screen.findByRole('alertdialog');
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);
    expect(dialog.hasAttribute('open')).toBe(true);
    expect(document.activeElement).toBe(
      within(dialog).getByRole('button', { name: 'Keep editing' })
    );

    await fireEvent.click(
      within(dialog).getByRole('button', { name: 'Keep editing' })
    );

    await waitFor(() => {
      expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(1);
      expect(document.activeElement).toBe(removeButton);
    });
    expect(screen.queryByRole('alertdialog')).toBeNull();
  });

  it('shows deletion errors while an appeal keeps edit details hidden', async () => {
    mocks.api.delete.mockRejectedValueOnce({
      response: { data: { detail: 'This submission could not be removed.' } }
    });
    renderEditor(makeSubmission({ has_appeal: true, state: 'pending' }));

    await fireEvent.click(
      await screen.findByRole('button', { name: 'Remove submission' })
    );
    const dialog = await screen.findByRole('alertdialog');
    await fireEvent.click(
      within(dialog).getByRole('button', { name: 'Remove submission' })
    );

    expect(
      await screen.findByText('This submission could not be removed.')
    ).toBeTruthy();
    expect(screen.queryByRole('alertdialog')).toBeNull();
  });
});
