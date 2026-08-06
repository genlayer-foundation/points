import { fireEvent, render, screen } from '@testing-library/svelte/svelte5';
import { describe, expect, it, vi } from 'vitest';
import ContributionGuidelines from '../components/portal/ContributionGuidelines.svelte';

const projectType = {
  id: 7,
  name: 'Projects',
  slug: 'projects',
  max_submissions_per_user_per_week: 2,
};

describe('ContributionGuidelines', () => {
  it('shows only a minimal pre-flight card before a contribution type is selected', () => {
    render(ContributionGuidelines);

    expect(screen.getByRole('heading', { name: 'Before you submit' })).toBeTruthy();
    expect(screen.getByText('Weekly limits run Monday 00:00 to Sunday 23:59 UTC')).toBeTruthy();
    expect(screen.queryByText('Quality bar')).toBeNull();
    expect(screen.queryByText('After you submit: reviews, appeals, and slots')).toBeNull();
    expect(screen.queryByText('More information.', { exact: false })).toBeNull();
  });

  it('shows the Project panel with the static limit when no personal usage data exists', () => {
    render(ContributionGuidelines, { props: { contributionType: projectType } });

    expect(screen.getByRole('heading', { name: 'Before you submit a Project' })).toBeTruthy();
    expect(screen.getByText('2 new Project submissions per user, each week')).toBeTruthy();
    expect(screen.getByText('Monday 00:00 to Sunday 23:59 UTC')).toBeTruthy();
    expect(screen.getByText('Quality bar')).toBeTruthy();
    expect(screen.getByText('Solves a real trust problem.')).toBeTruthy();
    expect(
      screen.getByText('Milestones are open only for highlighted projects. Cosmetic changes do not qualify.'),
    ).toBeTruthy();
  });

  it('personalizes the slot counter when weekly usage data is available', () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { ...projectType, user_weekly_submissions_remaining: 1 },
      },
    });

    expect(screen.getByText('You have used 1 of 2 Project slots this week')).toBeTruthy();
    expect(screen.getByText('Resets Monday 00:00 UTC')).toBeTruthy();
    expect(screen.getByRole('img', { name: '1 of 2 weekly slots used' })).toBeTruthy();
  });

  it('switches the counter to a warning when no weekly slots remain', () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { ...projectType, user_weekly_submissions_remaining: 0 },
      },
    });

    expect(screen.getByText('You have used your 2 Project slots for this week.')).toBeTruthy();
    expect(screen.getByText('Resets Monday 00:00 UTC')).toBeTruthy();
  });

  it('routes to the sibling categories when the router entries are clicked', async () => {
    const onRoute = vi.fn();
    render(ContributionGuidelines, {
      props: { contributionType: projectType, onRoute },
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Intelligent Contract' }));
    expect(onRoute).toHaveBeenCalledWith('create-intelligent-contracts');

    await fireEvent.click(screen.getByRole('button', { name: 'Milestone' }));
    expect(onRoute).toHaveBeenCalledWith('milestones');
  });

  it('renders the router entries as plain text without an onRoute callback', () => {
    render(ContributionGuidelines, { props: { contributionType: projectType } });

    expect(screen.queryByRole('button', { name: 'Milestone' })).toBeNull();
    expect(screen.getByText('Milestone')).toBeTruthy();
  });

  it('keeps the post-submission process collapsed behind an accordion', async () => {
    render(ContributionGuidelines, { props: { contributionType: projectType } });

    const accordion = screen
      .getByText('After you submit: reviews, appeals, and slots')
      .closest('details');
    expect(accordion.open).toBe(false);

    await fireEvent.click(screen.getByText('After you submit: reviews, appeals, and slots'));
    expect(accordion.open).toBe(true);
    expect(screen.getByText('More information.')).toBeTruthy();
    expect(screen.getByText('Rejection.')).toBeTruthy();
    expect(screen.getByText('Appeal.')).toBeTruthy();
  });

  it('shows the Intelligent Contract quality bar for the contract type', () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { id: 9, name: 'Intelligent Contract', slug: 'create-intelligent-contracts' },
      },
    });

    expect(
      screen.getByRole('heading', { name: 'Before you submit an Intelligent Contract' }),
    ).toBeTruthy();
    expect(screen.getByText('Not a learning exercise.')).toBeTruthy();
    expect(
      screen.getByText('Acceptance for this category is strict. Lightweight contracts are rejected.'),
    ).toBeTruthy();
    expect(screen.queryByText('Solves a real trust problem.')).toBeNull();
  });

  it('leads the Milestone panel with an eligibility warning when the user has no highlighted projects', () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { id: 10, name: 'Milestones', slug: 'milestones' },
        milestoneEligible: false,
      },
    });

    expect(screen.getByRole('heading', { name: 'Before you submit a Milestone' })).toBeTruthy();
    expect(screen.getByText('You have no highlighted Project contributions yet.')).toBeTruthy();
  });

  it('renders the mobile guidance as a collapsed accordion with the slot counter in the header', async () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { ...projectType, user_weekly_submissions_remaining: 1 },
        mobile: true,
      },
    });

    const disclosure = screen.getByText('Before you submit').closest('details');
    expect(disclosure).toBeTruthy();
    expect(disclosure.open).toBe(false);
    expect(screen.getByText('1 of 2 Project slots used this week')).toBeTruthy();

    await fireEvent.click(screen.getByText('Before you submit'));
    expect(disclosure.open).toBe(true);
    expect(screen.getByText('Quality bar')).toBeTruthy();
  });
});
