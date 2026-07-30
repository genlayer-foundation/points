import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte/svelte5';

/**
 * The navbar bell used to call loadLatest() on every route change even while
 * closed, which cost a list request plus a redundant unread-count. Nothing
 * rendered the component in tests, so the bug shipped unnoticed. These tests
 * render it.
 */

const mocks = vi.hoisted(() => {
  // A minimal writable: vi.hoisted runs before imports, so svelte/store is not
  // available here.
  function store(initial) {
    let value = initial;
    const subscribers = new Set();
    return {
      subscribe(run) {
        subscribers.add(run);
        run(value);
        return () => subscribers.delete(run);
      },
      set(next) {
        value = next;
        subscribers.forEach((run) => run(value));
      },
    };
  }

  return {
    store,
    loadLatest: vi.fn(),
    loadUnreadCount: vi.fn(),
    startPolling: vi.fn(() => () => {}),
    reset: vi.fn(),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
    location: store('/'),
    authState: store({ isAuthenticated: true }),
    notifications: store({
      items: [],
      unreadCount: 0,
      loading: false,
      error: null,
    }),
  };
});

vi.mock('svelte-spa-router', () => ({
  push: vi.fn(),
  location: mocks.location,
}));

vi.mock('../lib/auth.js', () => ({
  authState: mocks.authState,
}));

vi.mock('../lib/notificationStore.js', () => ({
  notificationStore: {
    subscribe: mocks.notifications.subscribe,
    loadLatest: mocks.loadLatest,
    loadUnreadCount: mocks.loadUnreadCount,
    startPolling: mocks.startPolling,
    reset: mocks.reset,
    markRead: mocks.markRead,
    markAllRead: mocks.markAllRead,
  },
}));

async function flush() {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('NotificationCenter request volume', () => {
  beforeEach(() => {
    mocks.loadLatest.mockReset();
    mocks.loadUnreadCount.mockReset();
    mocks.location.set('/');
    mocks.authState.set({ isAuthenticated: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('only refreshes the unread count on route changes while closed', async () => {
    const NotificationCenter = (await import('../components/NotificationCenter.svelte')).default;
    render(NotificationCenter);
    await flush();

    mocks.loadLatest.mockClear();
    mocks.loadUnreadCount.mockClear();

    for (const path of ['/builders', '/validators', '/community/poaps', '/profile']) {
      mocks.location.set(path);
      await flush();
    }

    expect(mocks.loadLatest).not.toHaveBeenCalled();
    expect(mocks.loadUnreadCount).toHaveBeenCalledTimes(4);
  });

  it('loads the list when the panel is opened', async () => {
    const NotificationCenter = (await import('../components/NotificationCenter.svelte')).default;
    const { getByRole } = render(NotificationCenter);
    await flush();
    mocks.loadLatest.mockClear();

    getByRole('button', { name: /notification/i }).click();
    await flush();

    expect(mocks.loadLatest).toHaveBeenCalledTimes(1);
  });

  it('does not load the list on the notifications route', async () => {
    const NotificationCenter = (await import('../components/NotificationCenter.svelte')).default;
    render(NotificationCenter);
    await flush();
    mocks.loadLatest.mockClear();
    mocks.loadUnreadCount.mockClear();

    mocks.location.set('/notifications');
    await flush();

    expect(mocks.loadLatest).not.toHaveBeenCalled();
    expect(mocks.loadUnreadCount).toHaveBeenCalledTimes(1);
  });

  it('resets instead of fetching when unauthenticated', async () => {
    const NotificationCenter = (await import('../components/NotificationCenter.svelte')).default;
    render(NotificationCenter);
    await flush();
    mocks.loadUnreadCount.mockClear();
    mocks.reset.mockClear();

    mocks.authState.set({ isAuthenticated: false });
    await flush();

    expect(mocks.loadUnreadCount).not.toHaveBeenCalled();
    expect(mocks.reset).toHaveBeenCalled();
  });
});
