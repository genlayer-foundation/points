import { afterEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte/svelte5';

import Dashboard from '../routes/Dashboard.svelte';
import { userStore } from '../lib/userStore.js';
import { currentCategory } from '../stores/category.js';

describe('Dashboard role view access', () => {
  afterEach(() => {
    userStore.clearUser();
    currentCategory.set('builder');
  });

  it('renders the dashboard without contribution actions for a read-only viewer', () => {
    currentCategory.set('community');
    userStore.setUser({ can_view_role_sections: true });

    render(Dashboard);

    expect(screen.getByText('View-only access')).toBeDefined();
    expect(screen.queryByRole('link', { name: 'Submit Contribution' })).toBeNull();
  });

  it('keeps the normal dashboard for a user who holds the role', () => {
    currentCategory.set('community');
    userStore.setUser({
      can_view_role_sections: true,
      creator: {},
    });

    render(Dashboard);

    expect(screen.queryByText('View-only access')).toBeNull();
    expect(screen.getByRole('link', { name: 'Submit Contribution' })).toBeDefined();
  });
});
