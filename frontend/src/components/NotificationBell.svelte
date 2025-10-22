<script>
  import { push } from 'svelte-spa-router';
  import { notificationsAPI } from '../lib/api';

  let unreadCount = $state(0);
  let pollInterval;

  // Load unread count
  async function loadUnreadCount() {
    try {
      const { data } = await notificationsAPI.getUnreadCount();
      unreadCount = data.count;
    } catch (err) {
      console.error('Failed to load unread count:', err);
    }
  }

  // Start polling every 30 seconds
  $effect(() => {
    loadUnreadCount();
    pollInterval = setInterval(loadUnreadCount, 30000);

    return () => clearInterval(pollInterval);
  });

  function goToNotifications() {
    push('/notifications');
  }
</script>

<button
  onclick={goToNotifications}
  class="relative p-2 text-gray-700 hover:text-gray-900 transition-colors rounded-md hover:bg-gray-100"
  aria-label="Notifications"
  title="Notifications"
>
  <!-- Bell icon (heroicons bell) -->
  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
  </svg>

  {#if unreadCount > 0}
    <span class="absolute top-1 right-1 bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
      {unreadCount > 9 ? '9+' : unreadCount}
    </span>
  {/if}
</button>
