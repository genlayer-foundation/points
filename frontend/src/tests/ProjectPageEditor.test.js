import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/svelte/svelte5';
import ProjectPageEditor from '../routes/ProjectPageEditor.svelte';
import { contributionsAPI, projectsAPI, usersAPI } from '../lib/api';
import { renderWithEffects, waitForApiCall } from './testHelpers';

const getProjectMock = /** @type {import('vitest').Mock} */ (projectsAPI.get);
const updateProfileMock = /** @type {import('vitest').Mock} */ (projectsAPI.updateProfile);
const uploadImageMock = /** @type {import('vitest').Mock} */ (projectsAPI.uploadImage);
const searchUsersMock = /** @type {import('vitest').Mock} */ (usersAPI.searchUsers);
const getContributionsMock = /** @type {import('vitest').Mock} */ (contributionsAPI.getContributions);
const validAbout = 'BuildersClaw helps teams coordinate builder opportunities, showcase validated work, and connect submitted contributions to a clear project profile in the Portal.';

const project = {
  id: 1,
  slug: 'buildersclaw',
  title: 'BuildersClaw',
  description: 'BuildersClaw connects companies with builders.',
  author: 'BuildersClaw Team',
  hero_image_url: '',
  hero_image_url_tablet: '',
  hero_image_url_mobile: '',
  user_profile_image_url: '',
  url: 'https://buildersclaw.xyz',
  github_url: 'https://github.com/buildersclaw/buildersclaw',
  x_url: '',
  telegram_url: '',
  discord_url: '',
  demo_url: '',
  details: validAbout,
  participants: [],
  related_contributions: [],
  can_edit: true,
};

describe('ProjectPageEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getProjectMock.mockResolvedValue({ data: project });
    updateProfileMock.mockImplementation((_slug, data) => Promise.resolve({
      data: {
        ...project,
        ...data,
        participants: [],
        related_contributions: [],
      }
    }));
    searchUsersMock.mockResolvedValue({ data: { results: [] } });
    getContributionsMock.mockResolvedValue({ data: { results: [] } });
    uploadImageMock.mockResolvedValue({
      data: {
        url: 'https://res.cloudinary.com/demo/image/upload/tally/projects/buildersclaw/logos/logo.png',
      },
    });
    Object.defineProperty(URL, 'createObjectURL', {
      writable: true,
      value: vi.fn(() => 'blob:local-preview'),
    });
  });

  it('loads structured project fields without rendering a preview pane', async () => {
    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');

    expect(screen.getByText('Edit project profile')).toBeDefined();
    const description = /** @type {HTMLTextAreaElement} */ (screen.getByLabelText('One-liner'));
    const about = /** @type {HTMLTextAreaElement} */ (screen.getByLabelText('About'));
    expect(description.value).toBe('BuildersClaw connects companies with builders.');
    expect(about.value).toContain(validAbout);
    expect(screen.queryByText('Public project page')).toBeNull();
    expect(screen.getByText('Related submissions')).toBeDefined();
    expect(screen.queryByLabelText('Callout text')).toBeNull();
  });

  it('does not render the editor when the project is not editable by the user', async () => {
    getProjectMock.mockResolvedValueOnce({ data: { ...project, can_edit: false } });

    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');

    expect(screen.getByText('Project editor unavailable')).toBeDefined();
    expect(screen.getByText('You do not have permission to edit this project.')).toBeDefined();
    expect(screen.queryByRole('button', { name: /save changes/i })).toBeNull();
  });

  it('saves profile fields directly', async () => {
    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfileMock).toHaveBeenCalledWith(
        'buildersclaw',
        expect.objectContaining({
          description: 'BuildersClaw connects companies with builders.',
          details: validAbout,
          url: 'https://buildersclaw.xyz',
          github_url: 'https://github.com/buildersclaw/buildersclaw',
          x_url: '',
          telegram_url: '',
          discord_url: '',
          demo_url: '',
          participant_ids: [],
          related_contribution_ids: [],
        })
      );
    });
  });

  it('renders compact link and image fields without the markdown import tab', async () => {
    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');

    expect(screen.queryByRole('button', { name: /markdown/i })).toBeNull();
    expect(screen.getByText('Project links')).toBeDefined();
    expect(screen.getByText('Project images')).toBeDefined();

    for (const button of screen.getAllByRole('button', { name: 'URL' })) {
      await fireEvent.click(button);
    }
    await fireEvent.input(screen.getByLabelText(/logo url/i), {
      target: { value: 'https://cdn.example.com/logo.png' },
    });
    await fireEvent.input(screen.getByLabelText(/desktop banner url/i), {
      target: { value: 'https://cdn.example.com/desktop.png' },
    });
    await fireEvent.input(screen.getByLabelText(/ipad banner url/i), {
      target: { value: 'https://cdn.example.com/tablet.png' },
    });
    await fireEvent.input(screen.getByLabelText(/mobile banner url/i), {
      target: { value: 'https://cdn.example.com/mobile.png' },
    });
    await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfileMock).toHaveBeenCalledWith(
        'buildersclaw',
        expect.objectContaining({
          hero_image_url: 'https://cdn.example.com/desktop.png',
          hero_image_url_tablet: 'https://cdn.example.com/tablet.png',
          hero_image_url_mobile: 'https://cdn.example.com/mobile.png',
          user_profile_image_url: 'https://cdn.example.com/logo.png',
        })
      );
    });
  });

  it('shows an uploaded image in the preview immediately after upload', async () => {
    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    const file = new File(['image-bytes'], 'logo.png', { type: 'image/png' });

    await fireEvent.change(screen.getByLabelText(/logo upload/i), {
      target: { files: [file] },
    });

    await waitFor(() => {
      expect(uploadImageMock).toHaveBeenCalled();
      expect(screen.getByAltText('Logo preview').getAttribute('src')).toBe(
        'https://res.cloudinary.com/demo/image/upload/tally/projects/buildersclaw/logos/logo.png'
      );
    });
  });

  it('adds participants through search and saves their ids', async () => {
    searchUsersMock.mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 9,
            name: 'Project Participant',
            address: '0x0000000000000000000000000000000000000009',
            profile_image_url: '',
          },
        ],
      },
    });

    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    await fireEvent.input(screen.getByLabelText('Search participants'), {
      target: { value: 'Project Participant' },
    });

    await waitFor(() => {
      expect(searchUsersMock).toHaveBeenCalledWith('Project Participant');
      expect(screen.getByRole('button', { name: /Project Participant/i })).toBeDefined();
    });

    await fireEvent.click(screen.getByRole('button', { name: /Project Participant/i }));
    await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfileMock).toHaveBeenCalledWith(
        'buildersclaw',
        expect.objectContaining({ participant_ids: [9], related_contribution_ids: [] })
      );
    });
  });

  it('selects related submissions from selected participant contributions', async () => {
    searchUsersMock.mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 9,
            name: 'Project Participant',
            address: '0x0000000000000000000000000000000000000009',
            profile_image_url: '',
          },
        ],
      },
    });
    getContributionsMock.mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 42,
            title: 'Built the project interface',
            notes: 'Accepted work.',
            points: 20,
            frozen_global_points: 42,
            contribution_date: '2026-05-01T12:00:00Z',
            user_details: {
              id: 9,
              name: 'Project Participant',
              address: '0x0000000000000000000000000000000000000009',
              profile_image_url: '',
            },
            contribution_type_name: 'Project Submission',
          },
        ],
      },
    });

    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    await fireEvent.input(screen.getByLabelText('Search participants'), {
      target: { value: 'Project Participant' },
    });
    await waitFor(() => expect(screen.getByRole('button', { name: /Project Participant/i })).toBeDefined());
    await fireEvent.click(screen.getByRole('button', { name: /Project Participant/i }));

    await waitFor(() => {
      expect(getContributionsMock).toHaveBeenCalledWith(
        expect.objectContaining({ user_address: '0x0000000000000000000000000000000000000009' })
      );
      expect(screen.getByLabelText('Search submissions')).toBeDefined();
    });

    await fireEvent.focus(screen.getByLabelText('Search submissions'));
    await fireEvent.input(screen.getByLabelText('Search submissions'), {
      target: { value: 'interface' },
    });
    await fireEvent.click(screen.getByRole('button', { name: /Built the project interface/i }));
    await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfileMock).toHaveBeenCalledWith(
        'buildersclaw',
        expect.objectContaining({
          participant_ids: [9],
          related_contribution_ids: [42],
        })
      );
    });
  });

  it('preserves owner related submissions even when the owner was not explicitly in participants', async () => {
    getProjectMock.mockResolvedValueOnce({
      data: {
        ...project,
        user: 7,
        user_name: 'Project Owner',
        user_address: '0x0000000000000000000000000000000000000007',
        participants: [],
        related_contributions: [
          {
            id: 77,
            title: 'Owner project submission',
            points: 12,
            frozen_global_points: 12,
            contribution_date: '2026-05-02T12:00:00Z',
            user_details: {
              id: 7,
              name: 'Project Owner',
              address: '0x0000000000000000000000000000000000000007',
              profile_image_url: '',
            },
            contribution_type_name: 'Project Submission',
          },
        ],
      },
    });

    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfileMock).toHaveBeenCalledWith(
        'buildersclaw',
        expect.objectContaining({
          participant_ids: [7],
          related_contribution_ids: [77],
        })
      );
    });
  });

  it('preserves migrated related submissions by treating their user as a participant', async () => {
    getProjectMock.mockResolvedValueOnce({
      data: {
        ...project,
        user: 7,
        user_name: 'Project Owner',
        user_address: '0x0000000000000000000000000000000000000007',
        participants: [],
        related_contributions: [
          {
            id: 88,
            title: 'Migrated featured build submission',
            points: 18,
            frozen_global_points: 18,
            contribution_date: '2026-05-03T12:00:00Z',
            user_details: {
              id: 8,
              name: 'Original Contributor',
              address: '0x0000000000000000000000000000000000000008',
              profile_image_url: '',
            },
            contribution_type_name: 'Project Submission',
          },
        ],
      },
    });

    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => {
      expect(updateProfileMock).toHaveBeenCalledWith(
        'buildersclaw',
        expect.objectContaining({
          participant_ids: [7, 8],
          related_contribution_ids: [88],
        })
      );
    });
  });

  it('blocks saving incomplete profiles', async () => {
    getProjectMock.mockResolvedValueOnce({ data: { ...project, details: '' } });

    renderWithEffects(ProjectPageEditor, { props: { params: { slug: 'buildersclaw' } } });

    await waitForApiCall(projectsAPI.get, 'buildersclaw');
    const saveButton = /** @type {HTMLButtonElement} */ (screen.getByRole('button', { name: /save changes/i }));
    expect(saveButton.disabled).toBe(true);
    expect(updateProfileMock).not.toHaveBeenCalled();
  });
});
