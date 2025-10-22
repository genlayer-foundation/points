<script>
  import { notificationsAPI } from '../lib/api';
  import { push } from 'svelte-spa-router';
  import { showSuccess } from '../lib/toastStore';
  import { format } from 'date-fns';

  let notifications = $state([]);
  let loading = $state(true);
  let filter = $state('all'); // 'all' or 'unread'

  // Derived state for unread count
  let unreadCount = $derived(
    notifications.filter(n => n.unread).length
  );

  async function loadNotifications() {
    loading = true;
    try {
      const { data } = await notificationsAPI.getAll();
      notifications = data.results || data;
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      loading = false;
    }
  }

  async function markAllRead() {
    try {
      await notificationsAPI.markAllRead();
      showSuccess('All notifications marked as read');
      loadNotifications(); // Reload
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  }

  async function markAsRead(id) {
    try {
      await notificationsAPI.markRead(id);
      loadNotifications();
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  }

  async function handleNotificationClick(notification) {
    // Mark as read and navigate
    if (notification.unread) {
      try {
        await notificationsAPI.markRead(notification.id);
      } catch (err) {
        console.error('Failed to mark as read:', err);
      }
    }

    // Navigate based on notification type
    if (notification.notification_type === 'accepted' || notification.notification_type === 'rejected') {
      push('/my-submissions');
    } else if (notification.notification_type === 'more_info') {
      if (notification.submission_id) {
        push(`/contributions/${notification.submission_id}`);
      }
    }
  }

  async function handleMarkAsReadOnly(notification, event) {
    event.stopPropagation(); // Prevent navigation
    if (notification.unread) {
      await markAsRead(notification.id);
    }
  }

  function getNotificationIcon(type) {
    switch (type) {
      case 'accepted':
        return '✓';
      case 'rejected':
        return '✕';
      case 'more_info':
        return '?';
      default:
        return '•';
    }
  }

  function getNotificationBorderClass(type) {
    switch (type) {
      case 'accepted':
        return 'border-l-green-400';
      case 'rejected':
        return 'border-l-red-400';
      case 'more_info':
        return 'border-l-blue-400';
      default:
        return 'border-l-gray-400';
    }
  }

  function getNotificationBgClass(type) {
    switch (type) {
      case 'accepted':
        return 'bg-green-50';
      case 'rejected':
        return 'bg-red-50';
      case 'more_info':
        return 'bg-blue-50';
      default:
        return 'bg-gray-50';
    }
  }

  function getNotificationBadgeClass(type) {
    switch (type) {
      case 'accepted':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'more_info':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
      return format(new Date(dateString), 'MMM d, yyyy HH:mm');
    } catch {
      return dateString;
    }
  }

  $effect(() => {
    loadNotifications();
  });

  let filteredNotifications = $derived(
    filter === 'unread'
      ? notifications.filter(n => n.unread)
      : notifications
  );
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Notifications</h1>
      <p class="mt-1 text-sm text-gray-600">
        {#if unreadCount > 0}
          {unreadCount} unread notification{unreadCount > 1 ? 's' : ''}
        {:else}
          You're all caught up!
        {/if}
      </p>
    </div>
    {#if unreadCount > 0}
      <button
        onclick={markAllRead}
        class="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 transition-colors"
      >
        Mark all as read
      </button>
    {/if}
  </div>

  <!-- Filters -->
  <div class="flex gap-2">
    <button
      onclick={() => filter = 'all'}
      class="px-4 py-2 text-sm font-medium rounded-md transition-colors {filter === 'all' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'}"
    >
      All
    </button>
    <button
      onclick={() => filter = 'unread'}
      class="px-4 py-2 text-sm font-medium rounded-md transition-colors {filter === 'unread' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'}"
    >
      Unread
    </button>
  </div>

  <!-- Notifications list -->
  {#if loading}
    <div class="flex justify-center items-center p-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  {:else if filteredNotifications.length === 0}
    <div class="bg-white shadow-lg rounded-lg p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
      <h3 class="mt-4 text-lg font-medium text-gray-900">No {filter === 'unread' ? 'unread ' : ''}notifications</h3>
      <p class="mt-2 text-sm text-gray-600">
        {filter === 'unread' ? 'You\'re all caught up!' : 'Notifications will appear here when stewards review your submissions.'}
      </p>
    </div>
  {:else}
    <div class="space-y-4">
      {#each filteredNotifications as notification}
        <div
          class="bg-white shadow-lg rounded-lg border-l-4 {getNotificationBorderClass(notification.notification_type)} hover:shadow-xl transition-all cursor-pointer relative {!notification.unread ? 'opacity-65' : ''}"
          onclick={() => handleNotificationClick(notification)}
        >
          <!-- Header -->
          <div class="px-6 py-4 border-b {getNotificationBgClass(notification.notification_type)}">
            <div class="flex justify-between items-start">
              <div class="flex items-center gap-3 flex-1">
                {#if notification.unread}
                  <div class="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0"></div>
                {/if}
                <div class="flex-1">
                  <h3 class="text-lg {notification.unread ? 'font-semibold' : 'font-normal'} text-gray-900">
                    {notification.message}
                  </h3>
                  <p class="text-sm text-gray-600 mt-1">
                    {formatDate(notification.created_at)}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-3 py-1 rounded-full text-sm font-medium {getNotificationBadgeClass(notification.notification_type)}">
                  {notification.notification_type === 'accepted' ? 'Accepted' :
                   notification.notification_type === 'rejected' ? 'Rejected' :
                   notification.notification_type === 'more_info' ? 'More Info' : 'Notification'}
                </span>

                <!-- Mark as read button (always visible on unread) -->
                {#if notification.unread}
                  <button
                    onclick={(e) => handleMarkAsReadOnly(notification, e)}
                    class="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors flex-shrink-0"
                    title="Mark as read"
                  >
                    <!-- Eye icon (mark as seen) -->
                    <svg class="w-5 h-5 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                    </svg>
                  </button>
                {/if}
              </div>
            </div>
          </div>

          <!-- Content -->
          {#if notification.data?.staff_reply || notification.data?.points || notification.data?.contribution_type}
            <div class="px-6 py-4 space-y-3">
              {#if notification.data?.points}
                <div>
                  <h4 class="text-sm font-medium text-gray-700">Points Awarded</h4>
                  <p class="mt-1 text-sm text-gray-900 font-semibold">{notification.data.points} points</p>
                </div>
              {/if}

              {#if notification.data?.contribution_type}
                <div>
                  <h4 class="text-sm font-medium text-gray-700">Contribution Type</h4>
                  <p class="mt-1 text-sm text-gray-900">{notification.data.contribution_type}</p>
                </div>
              {/if}

              {#if notification.data?.staff_reply}
                <div>
                  <h4 class="text-sm font-medium text-gray-700">Steward Message</h4>
                  <p class="mt-1 text-sm text-gray-600 italic">"{notification.data.staff_reply}"</p>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
