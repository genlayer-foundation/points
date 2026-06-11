<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { notificationStore } from '../lib/notificationStore.js';
  import { followNotificationLink } from '../lib/notificationUtils.js';
  import { relativeTime } from '../lib/relativeTime.js';

  let open = $state(false);
  let container = $state(null);
  let pollId;

  let notifications = $derived(($notificationStore.items || []).slice(0, 7));
  let unreadCount = $derived($notificationStore.unreadCount || 0);
  let loading = $derived($notificationStore.loading);

  function toggleOpen() {
    open = !open;
    if (open) {
      notificationStore.loadLatest();
    }
  }

  function closePanel() {
    open = false;
  }

  function openNotification(notification) {
    if (!notification.is_read) {
      // Don't block navigation on the mark-read call.
      notificationStore.markRead(notification.id).catch(() => {});
    }

    closePanel();
    followNotificationLink(notification);
  }

  async function markAllRead(event) {
    event.stopPropagation();
    await notificationStore.markAllRead();
  }

  function viewAll() {
    closePanel();
    push('/notifications');
  }

  function handleDocumentClick(event) {
    if (!open || !container || container.contains(event.target)) return;
    closePanel();
  }

  $effect(() => {
    if ($authState.isAuthenticated) {
      notificationStore.loadLatest();
    } else {
      notificationStore.reset();
      closePanel();
    }
  });

  onMount(() => {
    document.addEventListener('click', handleDocumentClick);
    pollId = window.setInterval(() => {
      if ($authState.isAuthenticated) {
        notificationStore.loadUnreadCount();
      }
    }, 60000);

    return () => {
      document.removeEventListener('click', handleDocumentClick);
      if (pollId) window.clearInterval(pollId);
    };
  });
</script>

{#if $authState.isAuthenticated}
  <div class="relative inline-flex items-center" bind:this={container}>
    <button
      type="button"
      class="relative flex items-center justify-center w-10 h-10 rounded-full text-gray-700 hover:bg-gray-100 transition-colors"
      aria-label="Notifications{unreadCount > 0 ? ` (${unreadCount} unread)` : ''}"
      aria-expanded={open}
      onclick={toggleOpen}
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
      </svg>
      {#if unreadCount > 0}
        <span class="absolute top-0.5 right-0.5 flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 border-2 border-white text-white text-[10px] font-semibold leading-none">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      {/if}
    </button>

    {#if open}
      <div class="notification-panel absolute right-0 top-full mt-2 w-96 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden z-50">
        <div class="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 class="text-sm font-semibold text-gray-900">Notifications</h3>
          <button
            type="button"
            class="text-xs font-medium text-gray-500 hover:text-gray-900 disabled:opacity-40 disabled:cursor-not-allowed"
            disabled={unreadCount === 0}
            onclick={markAllRead}
          >
            Mark all read
          </button>
        </div>

        <div class="max-h-96 overflow-y-auto">
          {#if loading && notifications.length === 0}
            <div class="p-3 space-y-2">
              {#each Array(3) as _}
                <div class="h-14 rounded-md bg-gray-100 animate-pulse"></div>
              {/each}
            </div>
          {:else if notifications.length === 0}
            <div class="p-8 text-center text-sm text-gray-500">
              No notifications yet
            </div>
          {:else}
            {#each notifications as notification (notification.id)}
              <button
                type="button"
                class="w-full flex gap-3 px-4 py-3 text-left transition-colors {notification.is_read ? 'hover:bg-gray-50' : 'bg-primary-50/60 hover:bg-primary-50'}"
                onclick={() => openNotification(notification)}
              >
                <span class="mt-1.5 w-2 h-2 rounded-full shrink-0 {notification.is_read ? 'bg-transparent' : notification.priority >= 3 ? 'bg-red-500' : 'bg-primary-500'}"></span>
                <span class="min-w-0 flex-1">
                  <span class="block text-sm font-medium text-gray-900 leading-snug">{notification.title}</span>
                  {#if notification.body}
                    <span class="block text-xs text-gray-500 leading-snug mt-0.5 line-clamp-2">{notification.body}</span>
                  {/if}
                  <span class="block text-xs text-gray-400 mt-1">
                    {notification.category_label || notification.category} &middot; {relativeTime(notification.created_at)}
                  </span>
                </span>
              </button>
            {/each}
          {/if}
        </div>

        <button
          type="button"
          class="w-full py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 border-t border-gray-100 text-center"
          onclick={viewAll}
        >
          View all notifications
        </button>
      </div>
    {/if}
  </div>
{/if}

<style>
  @media (max-width: 767px) {
    .notification-panel {
      position: fixed;
      top: 3.5rem;
      right: 0.5rem;
      left: 0.5rem;
      width: auto;
      max-height: calc(100vh - 5rem);
    }
  }
</style>
