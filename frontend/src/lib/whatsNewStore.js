import { writable } from 'svelte/store';
import { whatsNewAPI } from './api.js';
import { asList } from './notificationUtils.js';

function createWhatsNewStore() {
  const { subscribe, set, update } = writable({
    visible: false,
    unseenCount: 0,
  });

  async function loadUnseen() {
    const response = await whatsNewAPI.list();
    const items = asList(response.data);
    update((state) => ({ ...state, unseenCount: response.data?.count ?? items.length }));
    return items;
  }

  async function loadPreviews() {
    const response = await whatsNewAPI.list({ preview: true });
    return asList(response.data);
  }

  async function refresh() {
    const response = await whatsNewAPI.unseenCount();
    const count = response.data?.count || 0;
    update((state) => ({ ...state, unseenCount: count }));
    return count;
  }

  async function markSeen(ids, action = 'seen') {
    const nextIds = Array.from(new Set((ids || []).filter(Boolean)));
    if (nextIds.length === 0) return { updated: 0 };

    const response = await whatsNewAPI.markSeen(nextIds, action);
    update((state) => ({
      ...state,
      unseenCount: response.data?.count ?? Math.max(0, state.unseenCount - nextIds.length),
    }));
    return response.data;
  }

  function open() {
    update((state) => ({ ...state, visible: true }));
  }

  function close() {
    update((state) => ({ ...state, visible: false }));
  }

  function reset() {
    set({ visible: false, unseenCount: 0 });
  }

  return {
    subscribe,
    loadUnseen,
    loadPreviews,
    refresh,
    markSeen,
    open,
    close,
    reset,
  };
}

export const whatsNewStore = createWhatsNewStore();
export const openWhatsNew = () => whatsNewStore.open();
