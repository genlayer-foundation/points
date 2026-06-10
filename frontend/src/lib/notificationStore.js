import { writable } from 'svelte/store';
import { notificationsAPI } from './api.js';

function asList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/**
 * Single source of truth for notification state shared by the navbar
 * dropdown and the /notifications page: latest items, unread count, and
 * mark-read mutations. The page keeps its own paginated list but routes all
 * mutations through this store so both surfaces stay in sync.
 */
function createNotificationStore() {
  const { subscribe, set, update } = writable({
    items: [],
    unreadCount: 0,
    loading: false,
    error: null
  });

  async function loadLatest() {
    update((state) => ({ ...state, loading: true, error: null }));

    try {
      const [listResponse, countResponse] = await Promise.all([
        notificationsAPI.list({ page_size: 7 }),
        notificationsAPI.unreadCount()
      ]);

      update((state) => ({
        ...state,
        items: asList(listResponse.data),
        unreadCount: countResponse.data?.count || 0,
        loading: false
      }));
    } catch (error) {
      update((state) => ({ ...state, error, loading: false }));
    }
  }

  async function loadUnreadCount() {
    try {
      const response = await notificationsAPI.unreadCount();
      update((state) => ({ ...state, unreadCount: response.data?.count || 0 }));
    } catch (error) {
      update((state) => ({ ...state, error }));
    }
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
    set({ items: [], unreadCount: 0, loading: false, error: null });
  }

  return {
    subscribe,
    loadLatest,
    loadUnreadCount,
    markRead,
    markAllRead,
    reset
  };
}

export const notificationStore = createNotificationStore();
