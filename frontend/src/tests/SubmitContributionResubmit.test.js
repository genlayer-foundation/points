import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SubmitContribution from '../routes/SubmitContribution.svelte';

const mocks = vi.hoisted(() => ({
  query: 'resubmit=rejected-42&mission=999&type=998',
  push: vi.fn(),
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn()
  },
  getAllContributionTypes: vi.fn(),
  getContributionType: vi.fn(),
  getMission: vi.fn(),
  getAcceptedProjects: vi.fn(),
  getMissions: vi.fn(),
  trackEvent: vi.fn(),
  authStore: /** @type {import('svelte/store').Writable<any> | null} */ (null)
}));

vi.mock('svelte-spa-router', () => ({
  push: mocks.push,
  querystring: {
    subscribe(run) {
      run(mocks.query);
      return () => {};
    }
  }
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

vi.mock('../lib/auth.js', async () => {
  const { writable } = await import('svelte/store');
  mocks.authStore = writable({
    isAuthenticated: true,
    address: '0xbuilder',
    loading: false,
    error: null
  });
  return {
    authState: mocks.authStore
  };
});

vi.mock('../lib/userStore.js', async () => {
  const { readable } = await import('svelte/store');
  return {
    userStore: readable({
      user: {
        address: '0xbuilder',
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

vi.mock('../lib/analytics.js', () => ({
  getAnalyticsContext: (properties) => properties,
  getLifecycleDurationMs: () => 0,
  getLifecycleDurations: () => ({}),
  markLifecycleTime: () => false,
  trackEvent: mocks.trackEvent
}));

const genericEvidenceType = {
  id: 91,
  name: 'Other',
  slug: 'other',
  is_generic: true,
  order: 99,
  url_patterns: []
};

const builderType = {
  id: 7,
  name: 'Builder Project',
  slug: 'projects',
  category: 'builder',
  description: 'Build a project.',
  is_submittable: true,
  is_full: false,
  user_weekly_is_full: false,
  min_points: 10,
  max_points: 100,
  accepted_evidence_url_types: [genericEvidenceType],
  required_evidence_url_types: [],
  required_social_accounts: [],
  required_discord_roles: []
};

function rejectedSource(overrides = {}) {
  return {
    id: 'rejected-42',
    state: 'rejected',
    contribution_type: builderType.id,
    contribution_type_name: builderType.name,
    contribution_type_details: builderType,
    contribution_date: '2026-07-18T12:00:00Z',
    title: 'Original project title',
    notes: 'Original project notes',
    staff_reply: 'The evidence did not describe the final release.',
    mission: null,
    project_contribution: null,
    evidence_items: [{
      id: 81,
      description: 'Release evidence',
      url: 'https://example.com/original-release',
      url_type: genericEvidenceType
    }],
    ...overrides
  };
}

describe('rejected contribution resubmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.query = 'resubmit=rejected-42&mission=999&type=998';
    mocks.api.get.mockResolvedValue({ data: rejectedSource() });
    mocks.api.post.mockResolvedValue({ data: { id: 'new-submission-84' } });
    mocks.getAllContributionTypes.mockResolvedValue({ data: [builderType] });
    mocks.getContributionType.mockResolvedValue({ data: builderType });
    mocks.getMission.mockResolvedValue({ data: null });
    mocks.getAcceptedProjects.mockResolvedValue({ data: [] });
    mocks.getMissions.mockResolvedValue([]);
    mocks.authStore?.set({
      isAuthenticated: true,
      address: '0xbuilder',
      loading: false,
      error: null
    });
    sessionStorage.clear();
    window.grecaptcha = {
      render: vi.fn(() => 12),
      getResponse: vi.fn(() => 'recaptcha-token'),
      reset: vi.fn()
    };
  });

  it('clones every supported field without record ids and creates a new row', async () => {
    render(SubmitContribution);

    expect(await screen.findByRole('heading', { name: 'Resubmit contribution' })).toBeTruthy();
    expect(screen.getByText('Original rejection reason')).toBeTruthy();
    const typeInput = await screen.findByDisplayValue('Builder Project');
    await waitFor(() => expect(typeInput.disabled).toBe(false));
    expect(screen.getByDisplayValue('Original project title')).toBeTruthy();
    expect(screen.getByDisplayValue('Original project notes')).toBeTruthy();
    expect(screen.getByDisplayValue('https://example.com/original-release')).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: 'Resubmit Contribution' }));

    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledTimes(1));
    expect(mocks.api.put).not.toHaveBeenCalled();
    const [path, payload] = mocks.api.post.mock.calls[0];
    expect(path).toBe('/submissions/');
    expect(payload).toMatchObject({
      contribution_type: builderType.id,
      contribution_date: '2026-07-18T00:00:00Z',
      title: 'Original project title',
      notes: 'Original project notes',
      recaptcha: 'recaptcha-token',
      evidence_items: [{
        description: 'Release evidence',
        url: 'https://example.com/original-release'
      }]
    });
    expect(payload.evidence_items[0]).not.toHaveProperty('id');
    expect(mocks.getMission).not.toHaveBeenCalledWith(999);
    expect(mocks.push).toHaveBeenCalledWith(
      '/my-submissions?submission=new-submission-84'
    );
    expect(sessionStorage.getItem('submissionUpdateSuccess')).toContain(
      'corrected contribution'
    );
  });

  it('keeps cloned content but requires a new selection for an expired mission', async () => {
    const expiredMission = {
      id: 55,
      name: 'Expired build mission',
      contribution_type: builderType.id,
      is_active: false,
      end_date: '2026-01-01T00:00:00Z',
      is_full: false
    };
    mocks.api.get.mockResolvedValue({
      data: rejectedSource({ mission: { id: 55, name: expiredMission.name } })
    });
    mocks.getMission.mockResolvedValue({ data: expiredMission });

    render(SubmitContribution);

    expect(await screen.findByRole('heading', { name: 'Resubmit contribution' })).toBeTruthy();
    expect(await screen.findByText(/is no longer accepting submissions/)).toBeTruthy();
    expect(screen.getByText(/copied details are intact/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Resubmit Contribution' })).toBeNull();
    expect(mocks.getMission).toHaveBeenCalledWith(55);
    expect(mocks.getMission).not.toHaveBeenCalledWith(999);
  });

  it('preserves cloned content but does not preselect a retired type', async () => {
    const retiredType = {
      ...builderType,
      name: 'Retired Builder Type',
      is_submittable: false
    };
    const replacementType = {
      ...builderType,
      id: 8,
      name: 'Current Builder Type',
      slug: 'current-builder-type'
    };
    mocks.api.get.mockResolvedValue({
      data: rejectedSource({
        contribution_type_name: retiredType.name,
        contribution_type_details: retiredType
      })
    });
    mocks.getAllContributionTypes.mockResolvedValue({
      data: [retiredType, replacementType]
    });

    render(SubmitContribution);

    expect(await screen.findByText(/no longer accepts direct submissions/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Resubmit Contribution' })).toBeNull();
    await fireEvent.click(screen.getByText(replacementType.name));
    expect(screen.getByDisplayValue('Original project title')).toBeTruthy();
    expect(screen.getByDisplayValue('https://example.com/original-release')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Resubmit Contribution' })).toBeTruthy();
  });

  it('preserves cloned content but does not preselect a full type', async () => {
    const fullType = {
      ...builderType,
      name: 'Full Builder Type',
      is_full: true
    };
    const replacementType = {
      ...builderType,
      id: 8,
      name: 'Current Builder Type',
      slug: 'current-builder-type'
    };
    mocks.api.get.mockResolvedValue({
      data: rejectedSource({
        contribution_type_name: fullType.name,
        contribution_type_details: fullType
      })
    });
    mocks.getAllContributionTypes.mockResolvedValue({
      data: [fullType, replacementType]
    });

    render(SubmitContribution);

    expect(await screen.findByText(/is currently full/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Resubmit Contribution' })).toBeNull();
    await fireEvent.click(screen.getByText(replacementType.name));
    expect(screen.getByDisplayValue('Original project notes')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Resubmit Contribution' })).toBeTruthy();
  });

  it('prefills an active mission and keeps the normal POST path', async () => {
    const activeMission = {
      id: 55,
      name: 'Active build mission',
      contribution_type: builderType.id,
      is_active: true,
      is_full: false,
      user_is_full: false
    };
    mocks.api.get.mockResolvedValue({
      data: rejectedSource({ mission: { id: 55, name: activeMission.name } })
    });
    mocks.getMissions.mockResolvedValue([activeMission]);

    render(SubmitContribution);

    const missionInput = await screen.findByDisplayValue(activeMission.name);
    await waitFor(() => expect(missionInput.disabled).toBe(false));
    await fireEvent.click(screen.getByRole('button', { name: 'Resubmit Contribution' }));

    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledTimes(1));
    expect(mocks.api.post.mock.calls[0][1]).toMatchObject({
      contribution_type: builderType.id,
      mission: activeMission.id,
      recaptcha: 'recaptcha-token'
    });
  });

  it('prefills an available linked project for a milestone clone', async () => {
    const milestoneType = {
      ...builderType,
      name: 'Milestones',
      slug: 'milestones'
    };
    const linkedProject = {
      id: 301,
      title: 'Original highlighted project',
      next_milestone_version: 3
    };
    mocks.api.get.mockResolvedValue({
      data: rejectedSource({
        contribution_type_name: milestoneType.name,
        contribution_type_details: milestoneType,
        project_contribution: linkedProject
      })
    });
    mocks.getAllContributionTypes.mockResolvedValue({ data: [milestoneType] });
    mocks.getAcceptedProjects.mockResolvedValue({ data: [linkedProject] });

    render(SubmitContribution);

    const typeInput = await screen.findByDisplayValue(milestoneType.name);
    await waitFor(() => expect(typeInput.disabled).toBe(false));
    await fireEvent.click(screen.getByRole('button', { name: 'Resubmit Contribution' }));

    await waitFor(() => expect(mocks.api.post).toHaveBeenCalledTimes(1));
    expect(mocks.api.post.mock.calls[0][1]).toMatchObject({
      contribution_type: milestoneType.id,
      project_contribution: String(linkedProject.id),
      recaptcha: 'recaptcha-token'
    });
  });

  it('refuses to prefill a source that is no longer rejected', async () => {
    mocks.api.get.mockResolvedValue({
      data: rejectedSource({ state: 'pending' })
    });

    render(SubmitContribution);

    expect(await screen.findByRole('heading', { name: 'Unable to start resubmission' })).toBeTruthy();
    expect(screen.getByText(/still rejected/)).toBeTruthy();
    expect(mocks.getAllContributionTypes).not.toHaveBeenCalled();
  });

  it('surfaces source loading failures and supports retry', async () => {
    mocks.api.get
      .mockRejectedValueOnce(new Error('Network unavailable'))
      .mockResolvedValueOnce({ data: rejectedSource() });

    render(SubmitContribution);

    expect(await screen.findByText(/couldn't load the rejected submission/)).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { name: 'Resubmit contribution' })).toBeTruthy();
    expect(mocks.api.get).toHaveBeenCalledTimes(2);
  });

  it('loads the owner-scoped source after signing in without remounting', async () => {
    mocks.authStore?.set({
      isAuthenticated: false,
      address: null,
      loading: false,
      error: null
    });

    render(SubmitContribution);

    expect(await screen.findByText('Authentication Required')).toBeTruthy();
    expect(mocks.api.get).not.toHaveBeenCalled();

    mocks.authStore?.set({
      isAuthenticated: true,
      address: '0xbuilder',
      loading: false,
      error: null
    });

    expect(await screen.findByRole('heading', { name: 'Resubmit contribution' })).toBeTruthy();
    expect(mocks.api.get).toHaveBeenCalledWith('/submissions/rejected-42/');
  });
});
