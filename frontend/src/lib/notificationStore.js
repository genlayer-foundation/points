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

  function loadLatest() {
    if (inflightLatest) return inflightLatest;

    const requestEpoch = epoch;
    update((state) => ({ ...state, loading: true, error: null }));

    const request = Promise.all([
      notificationsAPI.list({ page_size: 7 }),
      notificationsAPI.unreadCount()
    ])
      .then(([listResponse, countResponse]) => {
        if (requestEpoch !== epoch) return;
        update((state) => ({
          ...state,
          items: asList(listResponse.data),
          unreadCount: countResponse.data?.count || 0,
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

  function loadUnreadCount() {
    if (inflightCount) return inflightCount;

    const requestEpoch = epoch;
    const request = notificationsAPI
      .unreadCount()
      .then((response) => {
        if (requestEpoch !== epoch) return;
        update((state) => ({ ...state, unreadCount: response.data?.count || 0 }));
      })
      .catch((error) => {
        if (requestEpoch !== epoch) return;
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
    if (!pollHandle) {
      pollHandle = window.setInterval(() => {
        if (authState.get().isAuthenticated) {
          loadUnreadCount();
        }
      }, intervalMs);
    }

    return function stopPolling() {
      pollSubscribers = Math.max(0, pollSubscribers - 1);
      if (pollSubscribers === 0 && pollHandle) {
        window.clearInterval(pollHandle);
        pollHandle = null;
      }
    };
  }

  async function markRead(id) {
    const response = await notificationsAPI.markRead(id);
    const updated = response.data;

    update((state) => ({
      ...state,
      items: state.items.map((item) => (item.id === id ? updated : item)),
      unreadCount: Math.max(0, state.unreadCount - 1)
    }));

    return updated;
  }

  async function markAllRead() {
    await notificationsAPI.markAllRead();
    update((state) => ({
      ...state,
      items: state.items.map((item) => ({ ...item, is_read: true })),
      unreadCount: 0
    }));
  }

  function reset() {
    epoch += 1;
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
