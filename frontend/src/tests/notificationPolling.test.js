import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

const mocks = vi.hoisted(() => ({
  authenticated: true,
  unreadCount: vi.fn(),
  list: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}));

vi.mock('../lib/api.js', () => ({
  notificationsAPI: {
    unreadCount: mocks.unreadCount,
    list: mocks.list,
    markRead: mocks.markRead,
    markAllRead: mocks.markAllRead,
  },
}));

vi.mock('../lib/auth.js', () => ({
  authState: {
    get: () => ({ isAuthenticated: mocks.authenticated }),
  },
}));

const originalHiddenDescriptor = Object.getOwnPropertyDescriptor(document, 'hidden');
let hidden = false;

async function flushPromises() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

describe('notification polling visibility lifecycle', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.useFakeTimers();
    hidden = false;
    mocks.authenticated = true;
    mocks.unreadCount.mockReset();
    mocks.list.mockReset();
    mocks.markRead.mockReset();
    mocks.markAllRead.mockReset();
    mocks.unreadCount.mockResolvedValue({ data: { count: 3 } });
    mocks.list.mockResolvedValue({ data: { results: [] } });
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => hidden,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    if (originalHiddenDescriptor) {
      Object.defineProperty(document, 'hidden', originalHiddenDescriptor);
    } else {
      delete document.hidden;
    }
  });

  it('shares one timer, skips hidden intervals, and refreshes when visible', async () => {
    const setIntervalSpy = vi.spyOn(window, 'setInterval');
    const { notificationStore } = await import('../lib/notificationStore.js');
    const stopDesktop = notificationStore.startPolling();
    const stopMobile = notificationStore.startPolling();

    expect(setIntervalSpy).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(60000);
    await flushPromises();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(1);

    hidden = true;
    vi.advanceTimersByTime(60000);
    document.dispatchEvent(new Event('visibilitychange'));
    await flushPromises();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(1);

    hidden = false;
    document.dispatchEvent(new Event('visibilitychange'));
    await flushPromises();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(2);

    mocks.authenticated = false;
    vi.advanceTimersByTime(60000);
    document.dispatchEvent(new Event('visibilitychange'));
    await flushPromises();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(2);

    stopDesktop();
    stopMobile();
  });

  it('removes shared polling resources only after the final idempotent cleanup', async () => {
    const clearIntervalSpy = vi.spyOn(window, 'clearInterval');
    const removeListenerSpy = vi.spyOn(document, 'removeEventListener');
    const { notificationStore } = await import('../lib/notificationStore.js');
    const stopDesktop = notificationStore.startPolling();
    const stopMobile = notificationStore.startPolling();

    stopDesktop();
    stopDesktop();
    expect(clearIntervalSpy).not.toHaveBeenCalled();
    expect(removeListenerSpy).not.toHaveBeenCalledWith('visibilitychange', expect.any(Function));

    stopMobile();
    expect(clearIntervalSpy).toHaveBeenCalledTimes(1);
    expect(removeListenerSpy).toHaveBeenCalledWith('visibilitychange', expect.any(Function));
  });

  it('forces one visible refresh past a pending pre-hide count and ignores its stale result', async () => {
    const preHide = deferred();
    const visible = deferred();
    mocks.unreadCount
      .mockImplementationOnce(() => preHide.promise)
      .mockImplementationOnce(() => visible.promise);
    const { notificationStore } = await import('../lib/notificationStore.js');
    const stopDesktop = notificationStore.startPolling();
    const stopMobile = notificationStore.startPolling();

    const preHideRequest = notificationStore.loadUnreadCount();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(60000);
    expect(mocks.unreadCount).toHaveBeenCalledTimes(1);

    hidden = true;
    document.dispatchEvent(new Event('visibilitychange'));
    expect(mocks.unreadCount).toHaveBeenCalledTimes(1);

    hidden = false;
    document.dispatchEvent(new Event('visibilitychange'));
    expect(mocks.unreadCount).toHaveBeenCalledTimes(2);

    visible.resolve({ data: { count: 8 } });
    await flushPromises();
    expect(get(notificationStore).unreadCount).toBe(8);

    preHide.resolve({ data: { count: 1 } });
    await preHideRequest;
    expect(get(notificationStore).unreadCount).toBe(8);

    stopDesktop();
    stopMobile();
  });

  it('keeps a visible refresh when an older loadLatest count resolves afterward', async () => {
    const latestCount = deferred();
    const visible = deferred();
    mocks.unreadCount
      .mockImplementationOnce(() => latestCount.promise)
      .mockImplementationOnce(() => visible.promise);
    mocks.list.mockResolvedValue({
      data: { results: [{ id: 7, title: 'A notification', is_read: false }] },
    });
    const { notificationStore } = await import('../lib/notificationStore.js');
    const stopPolling = notificationStore.startPolling();

    const latestRequest = notificationStore.loadLatest();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(1);

    hidden = true;
    document.dispatchEvent(new Event('visibilitychange'));
    hidden = false;
    document.dispatchEvent(new Event('visibilitychange'));
    expect(mocks.unreadCount).toHaveBeenCalledTimes(2);

    visible.resolve({ data: { count: 9 } });
    await flushPromises();
    expect(get(notificationStore).unreadCount).toBe(9);

    latestCount.resolve({ data: { count: 2 } });
    await latestRequest;
    expect(get(notificationStore).unreadCount).toBe(9);
    expect(get(notificationStore).items).toEqual([
      { id: 7, title: 'A notification', is_read: false },
    ]);

    stopPolling();
  });

  it('does not double-decrement when a count observes mark-read before its POST resolves', async () => {
    const markReadResponse = deferred();
    const authoritativeCount = deferred();
    mocks.markRead.mockImplementationOnce(() => markReadResponse.promise);
    mocks.unreadCount
      .mockResolvedValueOnce({ data: { count: 4 } })
      .mockResolvedValueOnce({ data: { count: 3 } })
      .mockImplementationOnce(() => authoritativeCount.promise);
    const { notificationStore } = await import('../lib/notificationStore.js');

    await notificationStore.loadUnreadCount();
    expect(get(notificationStore).unreadCount).toBe(4);

    const markReadRequest = notificationStore.markRead(7);
    await notificationStore.loadUnreadCount({ force: true });
    expect(get(notificationStore).unreadCount).toBe(3);

    markReadResponse.resolve({ data: { id: 7, is_read: true } });
    await flushPromises();
    expect(mocks.unreadCount).toHaveBeenCalledTimes(3);
    expect(get(notificationStore).unreadCount).toBe(3);

    authoritativeCount.resolve({ data: { count: 3 } });
    await markReadRequest;
    expect(get(notificationStore).unreadCount).toBe(3);
  });

  it('keeps a mark-read item update when an older loadLatest resolves afterward', async () => {
    const staleList = deferred();
    mocks.list
      .mockResolvedValueOnce({ data: { results: [{ id: 7, is_read: false }] } })
      .mockImplementationOnce(() => staleList.promise);
    mocks.unreadCount
      .mockResolvedValueOnce({ data: { count: 1 } })
      .mockResolvedValueOnce({ data: { count: 1 } })
      .mockResolvedValueOnce({ data: { count: 0 } });
    mocks.markRead.mockResolvedValueOnce({ data: { id: 7, is_read: true } });
    const { notificationStore } = await import('../lib/notificationStore.js');

    await notificationStore.loadLatest();
    const staleRequest = notificationStore.loadLatest();
    await notificationStore.markRead(7);
    expect(get(notificationStore).items).toEqual([{ id: 7, is_read: true }]);

    staleList.resolve({ data: { results: [{ id: 7, is_read: false }] } });
    await staleRequest;
    expect(get(notificationStore).items).toEqual([{ id: 7, is_read: true }]);
  });

  it('keeps mark-all-read item updates when an older loadLatest resolves afterward', async () => {
    const staleList = deferred();
    mocks.list
      .mockResolvedValueOnce({ data: { results: [{ id: 7, is_read: false }] } })
      .mockImplementationOnce(() => staleList.promise);
    mocks.unreadCount
      .mockResolvedValueOnce({ data: { count: 1 } })
      .mockResolvedValueOnce({ data: { count: 1 } });
    mocks.markAllRead.mockResolvedValueOnce({});
    const { notificationStore } = await import('../lib/notificationStore.js');

    await notificationStore.loadLatest();
    const staleRequest = notificationStore.loadLatest();
    await notificationStore.markAllRead();
    expect(get(notificationStore).items).toEqual([{ id: 7, is_read: true }]);

    staleList.resolve({ data: { results: [{ id: 7, is_read: false }] } });
    await staleRequest;
    expect(get(notificationStore).items).toEqual([{ id: 7, is_read: true }]);
  });

  it('discards mark-all-read completion after the notification session resets', async () => {
    const oldSessionMutation = deferred();
    mocks.markAllRead.mockImplementationOnce(() => oldSessionMutation.promise);
    mocks.list.mockResolvedValueOnce({ data: { results: [{ id: 9, is_read: false }] } });
    mocks.unreadCount.mockResolvedValueOnce({ data: { count: 1 } });
    const { notificationStore } = await import('../lib/notificationStore.js');

    const oldSessionRequest = notificationStore.markAllRead();
    notificationStore.reset();
    await notificationStore.loadLatest();

    oldSessionMutation.resolve({});
    await oldSessionRequest;

    expect(get(notificationStore).items).toEqual([{ id: 9, is_read: false }]);
    expect(get(notificationStore).unreadCount).toBe(1);
  });
});
