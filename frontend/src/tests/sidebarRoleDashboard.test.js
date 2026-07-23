import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte/svelte5';

const router = vi.hoisted(() => ({
  location: /** @type {import('svelte/store').Writable<string> | null} */ (null),
  push: vi.fn(),
}));

vi.mock('svelte-spa-router', async () => {
  const { writable } = await import('svelte/store');
  router.location = writable('/builders');
  return {
    location: router.location,
    push: router.push,
  };
});

import Sidebar from '../components/Sidebar.svelte';
import { authState } from '../lib/auth.js';
import { userStore } from '../lib/userStore.js';

/** @param {string} path */
function setLocation(path) {
  if (!router.location) throw new Error('Router mock was not initialized');
  router.location.set(path);
}

describe('Sidebar role dashboard link', () => {
  afterEach(() => {
    authState.setAuthenticated(false);
    userStore.clearUser();
    vi.clearAllMocks();
  });

  for (const [category, rolePath] of [
    ['builder', '/builders'],
    ['validator', '/validators'],
    ['community', '/community'],
  ]) {
    it(`shows the ${category} dashboard only for read-only role access`, () => {
      authState.setAuthenticated(true);
      userStore.setUser({ can_view_role_sections: true });
      setLocation(rolePath);

      render(Sidebar);

      const dashboardLinks = screen.getAllByRole('link', { name: 'Dashboard' });
      expect(dashboardLinks).toHaveLength(2);
      expect(dashboardLinks.every((link) => link.getAttribute('href') === `${rolePath}/dashboard`))
        .toBe(true);
    });
  }

  it('does not add a redundant dashboard link for an earned role', () => {
    authState.setAuthenticated(true);
    userStore.setUser({
      can_view_role_sections: true,
      builder: {},
    });
    setLocation('/builders');

    render(Sidebar);

    expect(screen.queryByRole('link', { name: 'Dashboard' })).toBeNull();
  });
});
