import { writable } from 'svelte/store';
import { notificationsAPI } from './api.js';
import { authState } from './auth.js';
import { asList } from './notificationUtils.js';

/**
 * Single source of truth for notification state shared by the navbar
 * dropdown and the /notifications page: latest items, unread count, and
 * mark-read mutations. The page keeps its own paginated list but routes all
 * mutations through this store so both surfaces stay in sync.
 *
 * The bell component mounts twice (desktop and mobile navbar rows), so the
 * unread polling timer is a refcounted singleton and loads coalesce while a
 * request is in flight; network traffic stays single no matter how many
 * instances mount.
 */
function createNotificationStore() {
  const { subscribe, set, update } = writable({
    items: [],
    unreadCount: 0,
    loading: false,
    error: null
  });

  let pollHandle = null;
  let pollSubscribers = 0;
  let inflightLatest = null;
  let inflightCount = null;
  // Bumped on reset() so responses that were in flight when the session
  // changed (logout, wallet switch) are discarded instead of leaking the
  // previous account's feed into the new session.
  let epoch = 0;
  // Every request that can write unreadCount claims a monotonically increasing
  // version. This lets an immediate visibility refresh supersede count data
  // already in flight through either loadUnreadCount() or loadLatest().
  let unreadWriteVersion = 0;
  // Local read mutations supersede item lists that started loading before
  // those mutations completed.
  let itemWriteVersion = 0;

  function pollUnreadCountIfVisible() {
    if (document.hidden || !authState.get().isAuthenticated) return;
    loadUnreadCount();
  }

  function refreshUnreadCountOnVisibility() {
    if (document.hidden || !authState.get().isAuthenticated) return;
    loadUnreadCount({ force: true });
  }

  function loadLatest() {
    if (inflightLatest) return inflightLatest;

    const requestEpoch = epoch;
    const requestUnreadVersion = ++unreadWriteVersion;
    const requestItemVersion = itemWriteVersion;
    update((state) => ({ ...state, loading: true, error: null }));

    const request = Promise.all([
      notificationsAPI.list({ page_size: 7 }),
      notificationsAPI.unreadCount()
    ])
      .then(([listResponse, countResponse]) => {
        if (requestEpoch !== epoch) return;
        update((state) => ({
          ...state,
          ...(requestItemVersion === itemWriteVersion
            ? { items: asList(listResponse.data) }
            : {}),
          ...(requestUnreadVersion === unreadWriteVersion
            ? { unreadCount: countResponse.data?.count || 0 }
            : {}),
          loading: false
        }));
      })
      .catch((error) => {
        if (requestEpoch !== epoch) return;
        update((state) => ({ ...state, error, loading: false }));
      })
      .finally(() => {
        if (inflightLatest === request) inflightLatest = null;
      });

    inflightLatest = request;
    return request;
  }

  function loadUnreadCount({ force = false } = {}) {
    if (!force && inflightCount) return inflightCount;

    const requestEpoch = epoch;
    const requestUnreadVersion = ++unreadWriteVersion;
    const request = notificationsAPI
      .unreadCount()
      .then((response) => {
        if (requestEpoch !== epoch || requestUnreadVersion !== unreadWriteVersion) return;
        update((state) => ({ ...state, unreadCount: response.data?.count || 0 }));
      })
      .catch((error) => {
        if (requestEpoch !== epoch || requestUnreadVersion !== unreadWriteVersion) return;
        update((state) => ({ ...state, error }));
      })
      .finally(() => {
        if (inflightCount === request) inflightCount = null;
      });

    inflightCount = request;
    return request;
  }

  function startPolling(intervalMs = 60000) {
    pollSubscribers += 1;
    if (pollSubscribers === 1) {
      pollHandle = window.setInterval(pollUnreadCountIfVisible, intervalMs);
      document.addEventListener('visibilitychange', refreshUnreadCountOnVisibility);
    }

    let stopped = false;
    return function stopPolling() {
      if (stopped) return;
      stopped = true;
      pollSubscribers = Math.max(0, pollSubscribers - 1);
      if (pollSubscribers === 0) {
        if (pollHandle !== null) window.clearInterval(pollHandle);
        pollHandle = null;
        document.removeEventListener('visibilitychange', refreshUnreadCountOnVisibility);
      }
    };
  }

  async function markRead(id) {
    const requestEpoch = epoch;
    const response = await notificationsAPI.markRead(id);
    const updated = response.data;
    if (requestEpoch !== epoch) return updated;

    itemWriteVersion += 1;
    update((state) => ({
      ...state,
      items: state.items.map((item) => (item.id === id ? updated : item))
    }));
    await loadUnreadCount({ force: true });

    return updated;
  }

  async function markAllRead() {
    const requestEpoch = epoch;
    await notificationsAPI.markAllRead();
    if (requestEpoch !== epoch) return;

    unreadWriteVersion += 1;
    itemWriteVersion += 1;
    update((state) => ({
      ...state,
      items: state.items.map((item) => ({ ...item, is_read: true })),
      unreadCount: 0
    }));
  }

  function reset() {
    epoch += 1;
    unreadWriteVersion += 1;
    inflightLatest = null;
    inflightCount = null;
    set({ items: [], unreadCount: 0, loading: false, error: null });
  }

  return {
    subscribe,
    loadLatest,
    loadUnreadCount,
    startPolling,
    markRead,
    markAllRead,
    reset
  };
}

export const notificationStore = createNotificationStore();
