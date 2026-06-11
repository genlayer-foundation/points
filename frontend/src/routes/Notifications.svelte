<script>
  import AuthButton from '../components/AuthButton.svelte';
  import { authState } from '../lib/auth.js';
  import { notificationsAPI } from '../lib/api.js';
  import { notificationStore } from '../lib/notificationStore.js';
  import { asList, followNotificationLink } from '../lib/notificationUtils.js';
  import { relativeTime } from '../lib/relativeTime.js';

  let notifications = $state([]);
  let loading = $state(false);
  let error = $state('');
  let unreadOnly = $state(false);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let hasNext = $state(false);
  let lastAuthState = null;
  // Guards against out-of-order responses on fast filter toggles, same as
  // latestPoapsRequestId in CommunityPoaps.
  let latestRequestId = 0;

  async function loadNotifications(reset = true) {
    if (!$authState.isAuthenticated) {
      notifications = [];
      totalCount = 0;
      hasNext = false;
      return;
    }

    const requestId = ++latestRequestId;
    loading = true;
    error = '';

    try {
      const page = reset ? 1 : currentPage + 1;
      const response = await notificationsAPI.list({
        page,
        page_size: 30,
        unread: unreadOnly ? 'true' : undefined
      });
      if (requestId !== latestRequestId) return;

      const items = asList(response.data);
      notifications = reset ? items : [...notifications, ...items];
      totalCount = response.data?.count ?? notifications.length;
      hasNext = Boolean(response.data?.next);
      currentPage = page;
    } catch (err) {
      if (requestId !== latestRequestId) return;
      error = 'Failed to load notifications';
    } finally {
      if (requestId === latestRequestId) {
        loading = false;
      }
    }
  }

  function openNotification(notification) {
    if (!notification.is_read) {
      // Don't block navigation on the mark-read call.
      notificationStore
        .markRead(notification.id)
        .then((updated) => {
          notifications = notifications.map((item) => (item.id === updated.id ? updated : item));
        })
        .catch(() => {});
    }
    followNotificationLink(notification);
  }

  async function markAllRead() {
    await notificationStore.markAllRead();
    if (unreadOnly) {
      // Everything just stopped matching the active Unread filter.
      notifications = [];
      totalCount = 0;
      hasNext = false;
      currentPage = 1;
      return;
    }
    notifications = notifications.map((item) => ({ ...item, is_read: true }));
  }

  function setFilter(nextUnreadOnly) {
    if (unreadOnly === nextUnreadOnly) return;
    unreadOnly = nextUnreadOnly;
    loadNotifications(true);
  }

  // Covers both initial mount and later auth changes; no separate onMount load.
  $effect(() => {
    const isAuthenticated = $authState.isAuthenticated;
    if (isAuthenticated === lastAuthState) return;

    lastAuthState = isAuthenticated;
    if (isAuthenticated) {
      loadNotifications(true);
    } else {
      notifications = [];
      totalCount = 0;
      hasNext = false;
    }
  });
</script>

<div class="container mx-auto px-4 py-8">
  <div class="max-w-3xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Notifications</h1>
      {#if $authState.isAuthenticated && totalCount > 0}
        <button
          type="button"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={$notificationStore.unreadCount === 0}
          onclick={markAllRead}
        >
          Mark all read
        </button>
      {/if}
    </div>

    {#if !$authState.isAuthenticated}
      <div class="bg-white shadow rounded-lg p-8 text-center">
        <h2 class="text-lg font-semibold text-gray-900">Sign in to view notifications</h2>
        <p class="mt-2 mb-6 text-sm text-gray-500">
          Submission decisions and portal updates appear here once you are signed in.
        </p>
        <div class="flex justify-center">
          <AuthButton />
        </div>
      </div>
    {:else}
      <div class="flex items-center justify-between mb-4">
        <div class="inline-flex p-1 bg-white border border-gray-200 rounded-full" role="group" aria-label="Notification filters">
          <button
            type="button"
            class="px-4 py-1.5 text-sm font-medium rounded-full transition-colors {!unreadOnly ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'}"
            onclick={() => setFilter(false)}
          >
            All
          </button>
          <button
            type="button"
            class="px-4 py-1.5 text-sm font-medium rounded-full transition-colors {unreadOnly ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'}"
            onclick={() => setFilter(true)}
          >
            Unread
          </button>
        </div>
        <span class="text-sm text-gray-500">{totalCount} total</span>
      </div>

      {#if error}
        <div class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      {/if}

      {#if loading && notifications.length === 0}
        <div class="space-y-3">
          {#each Array(6) as _}
            <div class="h-20 bg-white shadow rounded-lg animate-pulse"></div>
          {/each}
        </div>
      {:else if notifications.length === 0}
        <div class="bg-white shadow rounded-lg p-8 text-center">
          <svg class="w-10 h-10 mx-auto text-gray-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
          </svg>
          <h2 class="mt-3 text-lg font-semibold text-gray-900">No notifications</h2>
          <p class="mt-1 text-sm text-gray-500">
            {unreadOnly ? 'You have no unread notifications.' : 'Portal updates and submission decisions will appear here.'}
          </p>
        </div>
      {:else}
        <div class="bg-white shadow rounded-lg overflow-hidden divide-y divide-gray-100">
          {#each notifications as notification (notification.id)}
            <button
              type="button"
              class="w-full flex gap-3 px-4 py-4 text-left transition-colors {notification.is_read ? 'hover:bg-gray-50' : 'bg-primary-50/60 hover:bg-primary-50'}"
              onclick={() => openNotification(notification)}
            >
              <span class="mt-1.5 w-2 h-2 rounded-full shrink-0 {notification.is_read ? 'bg-transparent' : notification.priority >= 3 ? 'bg-red-500' : 'bg-primary-500'}"></span>
              <span class="min-w-0 flex-1">
                <span class="flex items-start justify-between gap-4">
                  <span class="text-sm font-medium text-gray-900 leading-snug">{notification.title}</span>
                  <span class="text-xs text-gray-400 whitespace-nowrap shrink-0">{relativeTime(notification.created_at, { verbose: true })}</span>
                </span>
                {#if notification.body}
                  <span class="block text-sm text-gray-500 leading-snug mt-1">{notification.body}</span>
                {/if}
                <span class="block text-xs text-gray-400 mt-1.5">
                  {notification.category_label || notification.category}{#if notification.link_url}&nbsp;&middot; {notification.link_label || 'Open'}{/if}
                </span>
              </span>
            </button>
          {/each}
        </div>

        {#if hasNext}
          <div class="flex justify-center mt-6">
            <button
              type="button"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              disabled={loading}
              onclick={() => loadNotifications(false)}
            >
              {loading ? 'Loading...' : 'Load more'}
            </button>
          </div>
        {/if}
      {/if}
    {/if}
  </div>
</div>
