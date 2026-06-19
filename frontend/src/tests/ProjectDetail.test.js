import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/svelte/svelte5';
import ProjectDetail from '../routes/ProjectDetail.svelte';
import { projectsAPI } from '../lib/api';
import { renderWithEffects, waitForApiCall } from './testHelpers';

const getProjectMock = /** @type {import('vitest').Mock} */ (projectsAPI.get);

const baseProject = {
  id: 1,
  slug: 'cognocracy',
  title: 'Cognocracy',
  description: 'A governance project built on GenLayer.',
  author: 'Cognocracy Team',
  hero_image_url: 'https://example.com/cognocracy.jpg',
  hero_image_url_tablet: '',
  hero_image_url_mobile: '',
  user_name: 'Builder',
  user_profile_image_url: '',
  url: 'https://cognocracy.example.com',
  github_url: '',
  x_url: '',
  telegram_url: '',
  discord_url: '',
  demo_url: '',
  details: '',
  participants: [],
  related_contributions: [],
};

describe('ProjectDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getProjectMock.mockResolvedValue({ data: baseProject });
  });

  it('loads a project and shows quiet empty states when optional data is missing', async () => {
    renderWithEffects(ProjectDetail, { props: { params: { slug: 'cognocracy' } } });

    await waitForApiCall(projectsAPI.get, 'cognocracy');

    await waitFor(() => {
      expect(screen.getByText('Cognocracy')).toBeDefined();
    });

    expect(projectsAPI.get).toHaveBeenCalledWith('cognocracy');
    expect(screen.queryByRole('link', { name: /github/i })).toBeNull();
    expect(screen.queryByText('Total decisions made')).toBeNull();
    expect(screen.queryByText('Total value governed')).toBeNull();
    expect(screen.queryByText('Coming soon')).toBeNull();
    expect(screen.queryByText('No related contributions have been linked to this project yet.')).toBeNull();
  });

  it('renders project links, about media, demo, participants, and related submissions when present', async () => {
    getProjectMock.mockResolvedValueOnce({
      data: {
        ...baseProject,
        github_url: 'https://github.com/example/cognocracy',
        x_url: 'https://x.com/cognocracy',
        discord_url: 'https://discord.gg/abc123',
        demo_url: 'https://youtu.be/dQw4w9WgXcQ',
        details: [
          'A detailed project profile.',
          '',
          '<Image src="https://example.com/project.png" caption="Product dashboard" />',
          '',
          '<Video url="https://youtu.be/dQw4w9WgXcQ" title="Product walkthrough" caption="Demo walkthrough" />',
        ].join('\n'),
        participants: [
          {
            id: 1,
            name: 'Project Builder',
            address: '0x0000000000000000000000000000000000000001',
            profile_image_url: ''
          }
        ],
        related_contributions: [
          {
            id: 42,
            title: 'Built the project interface',
            notes: 'Accepted project work.',
            points: 20,
            frozen_global_points: 42,
            contribution_date: '2026-05-01T12:00:00Z',
            user: {
              name: 'Project Builder',
              address: '0x0000000000000000000000000000000000000001',
              profile_image_url: ''
            },
            contribution_type: {
              name: 'Project Submission',
              category: 'builder'
            }
          }
        ],
      }
    });

    renderWithEffects(ProjectDetail, { props: { params: { slug: 'cognocracy' } } });

    await waitForApiCall(projectsAPI.get, 'cognocracy');

    await waitFor(() => {
      expect(screen.getByText('Built the project interface')).toBeDefined();
      expect(screen.getAllByText('Project Builder').length).toBeGreaterThan(0);
    });

    expect(screen.getByRole('link', { name: /GitHub: cognocracy/i })).toBeDefined();
    expect(screen.getByRole('link', { name: /X: @cognocracy/i })).toBeDefined();
    expect(screen.getByRole('link', { name: /Discord: Cognocracy/i })).toBeDefined();
    expect(screen.getAllByText('Demo').length).toBeGreaterThan(0);
    expect(screen.getByText('A detailed project profile.')).toBeDefined();
    expect(screen.getByAltText('Product dashboard')).toBeDefined();
    expect(screen.getByText('Product dashboard')).toBeDefined();
    expect(screen.getByTitle('Product walkthrough')).toBeDefined();
    expect(screen.getByText('Demo walkthrough')).toBeDefined();
  });

  it('shows a GitHub username for project-wide GitHub URLs', async () => {
    getProjectMock.mockResolvedValueOnce({
      data: {
        ...baseProject,
        github_url: 'https://github.com/example',
      }
    });

    renderWithEffects(ProjectDetail, { props: { params: { slug: 'cognocracy' } } });

    await waitForApiCall(projectsAPI.get, 'cognocracy');

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /GitHub: example/i })).toBeDefined();
    });
  });
});
