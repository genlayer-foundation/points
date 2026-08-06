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
  it('shows the generic before-and-after guidance before a contribution type is selected', () => {
    render(ContributionGuidelines);

    expect(screen.getByRole('heading', { name: 'Before you submit' })).toBeTruthy();
    expect(screen.getByText('Weekly limits run Monday 00:00 to Sunday 23:59 UTC')).toBeTruthy();
    expect(screen.queryByText('Quality bar')).toBeNull();
    const accordion = screen
      .getByText('After you submit: reviews, appeals, and slots')
      .closest('details');
    if (!(accordion instanceof HTMLDetailsElement)) {
      throw new Error('Expected post-submission guidance to use a details element');
    }
    expect(accordion.open).toBe(false);
    expect(screen.getByText('More information.')).toBeTruthy();
    expect(screen.getByText('Rejection.')).toBeTruthy();
    expect(screen.getByText('Appeal.')).toBeTruthy();
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
    if (!(accordion instanceof HTMLDetailsElement)) {
      throw new Error('Expected post-submission guidance to use a details element');
    }
    expect(accordion.open).toBe(false);

    await fireEvent.click(screen.getByText('After you submit: reviews, appeals, and slots'));
    expect(accordion.open).toBe(true);
    expect(screen.getByText('More information.')).toBeTruthy();
    expect(screen.getByText('Rejection.')).toBeTruthy();
    expect(screen.getByText('Appeal.')).toBeTruthy();
  });

  it('shows the strict Intelligent Contract warning, router, quality bar, and weekly limit', async () => {
    const onRoute = vi.fn();
    render(ContributionGuidelines, {
      props: {
        contributionType: {
          id: 9,
          name: 'Intelligent Contract',
          slug: 'create-intelligent-contracts',
          max_submissions_per_user_per_week: 3,
        },
        onRoute,
      },
    });

    expect(
      screen.getByRole('heading', { name: 'Before you submit an Intelligent Contract' }),
    ).toBeTruthy();
    expect(screen.getByText('This category is strict. Most submissions are rejected.')).toBeTruthy();
    expect(
      screen.getByText('Lightweight contracts are rejected. This category is not a shortcut to points. A contract must provide real value to the ecosystem to be rewarded.'),
    ).toBeTruthy();
    expect(screen.getByText('3 new submissions per user, each week')).toBeTruthy();
    expect(screen.getByText('A full project with a frontend or product around it')).toBeTruthy();
    expect(screen.getByText('Not a learning exercise.')).toBeTruthy();
    expect(
      screen.getByText('Documented for reuse.'),
    ).toBeTruthy();
    expect(
      screen.getByText('If it would not be useful to someone else building on GenLayer, it is not ready to be submitted.'),
    ).toBeTruthy();
    expect(screen.queryByText('Solves a real trust problem.')).toBeNull();

    await fireEvent.click(screen.getByRole('button', { name: 'Project' }));
    expect(onRoute).toHaveBeenCalledWith('projects');

    await fireEvent.click(screen.getByRole('button', { name: 'Milestone' }));
    expect(onRoute).toHaveBeenCalledWith('milestones');

    expect(screen.getByRole('link', { name: 'Read full guidelines' }).getAttribute('href'))
      .toBe('/contribution-type/9');
  });

  it('replaces Milestone guidance with the eligibility gate when the user has no highlighted projects', () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { id: 10, name: 'Milestones', slug: 'milestones' },
        milestoneEligible: false,
      },
    });

    expect(screen.getByRole('heading', { name: 'Before you submit a Milestone' })).toBeTruthy();
    expect(
      screen.getByText('Milestones are open only for highlighted projects. Highlighted projects are selected by the review team based on use case and real usage potential. Keep building your project through new submissions to get there.'),
    ).toBeTruthy();
    expect(screen.queryByText('Quality bar')).toBeNull();
    expect(screen.getByText('After you submit: reviews, appeals, and slots')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Read full guidelines' }).getAttribute('href'))
      .toBe('/contribution-type/10');
  });

  it('shows the Milestone quality bar when the user has an eligible highlighted project', () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { id: 10, name: 'Milestones', slug: 'milestones' },
        milestoneEligible: true,
      },
    });

    expect(
      screen.getByText('Milestones reward substantial progress on highlighted projects.'),
    ).toBeTruthy();
    expect(screen.getByText('Substantial improvement.')).toBeTruthy();
    expect(screen.getByText('Not repackaging.')).toBeTruthy();
    expect(screen.getByText('Builds on the accepted version.')).toBeTruthy();
    expect(screen.getByText('Documented delta.')).toBeTruthy();
    expect(screen.getByText('Moves the project toward real usage.')).toBeTruthy();
  });

  it('renders the mobile guidance as a collapsed accordion with the slot counter in the header', async () => {
    render(ContributionGuidelines, {
      props: {
        contributionType: { ...projectType, user_weekly_submissions_remaining: 1 },
        mobile: true,
      },
    });

    const disclosure = screen.getByText('Before you submit').closest('details');
    if (!(disclosure instanceof HTMLDetailsElement)) {
      throw new Error('Expected mobile guidance to use a details element');
    }
    expect(disclosure.open).toBe(false);
    expect(screen.getByText('1 of 2 Project slots used this week')).toBeTruthy();

    await fireEvent.click(screen.getByText('Before you submit'));
    expect(disclosure.open).toBe(true);
    expect(screen.getByText('Quality bar')).toBeTruthy();
  });
});
