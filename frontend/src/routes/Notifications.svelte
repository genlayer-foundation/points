<script>
  import { onMount, tick } from 'svelte';
  import { push, querystring } from 'svelte-spa-router';
  import AuthButton from '../components/AuthButton.svelte';
  import WhatsNewAnnouncementSurface from '../components/WhatsNewAnnouncementSurface.svelte';
  import { authState } from '../lib/auth.js';
  import { notificationsAPI, whatsNewAPI } from '../lib/api.js';
  import { notificationStore } from '../lib/notificationStore.js';
  import { asList, followNotificationLink } from '../lib/notificationUtils.js';
  import { parseUserMarkdown } from '../lib/markdownLoader.js';
  import { relativeTime } from '../lib/relativeTime.js';
  import { normalizeWhatsNewItem } from '../lib/whatsNewPresentation.js';

  let notifications = $state([]);
  let loading = $state(false);
  let error = $state('');
  let unreadOnly = $state(false);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let hasNext = $state(false);
  let announcements = $state([]);
  let announcementsLoading = $state(false);
  let announcementsError = $state('');
  let previewAnnouncement = $state(null);
  let previewDialogEl = $state(null);
  let lastLoadKey = '';
  // Guards against out-of-order responses on fast filter toggles, same as
  // latestPoapsRequestId in CommunityPoaps.
  let latestRequestId = 0;
  let latestAnnouncementsRequestId = 0;

  let activeTab = $derived(
    new URLSearchParams($querystring).get('tab') === 'announcements'
      ? 'announcements'
      : 'notifications'
  );
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

  async function loadAnnouncements() {
    if (!$authState.isAuthenticated) {
      announcements = [];
      previewAnnouncement = null;
      return;
    }

    const requestId = ++latestAnnouncementsRequestId;
    announcementsLoading = true;
    announcementsError = '';

    try {
      const response = await whatsNewAPI.list({ preview: true });
      if (requestId !== latestAnnouncementsRequestId) return;

      announcements = asList(response.data).map(normalizeWhatsNewItem);
    } catch (err) {
      if (requestId !== latestAnnouncementsRequestId) return;
      announcementsError = 'Failed to load announcements';
    } finally {
      if (requestId === latestAnnouncementsRequestId) {
        announcementsLoading = false;
      }
    }
  }

  function openNotification(notification, event) {
    if (!notification.is_read) {
      // Don't block navigation on the mark-read call.
      notificationStore
        .markRead(notification.id)
        .then((updated) => {
          notifications = notifications.map((item) => (item.id === updated.id ? updated : item));
        })
        .catch(() => {});
    }
    // A click on an inline body link should follow only that link, not also
    // trigger the row's own redirect.
    if (event?.target?.closest('a')) return;
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
  }

  function setTab(nextTab) {
    push(nextTab === 'announcements' ? '/notifications?tab=announcements' : '/notifications');
  }

  function openAnnouncementLink(announcement) {
    if (!announcement?.linkUrl) return;
    previewAnnouncement = null;
    followNotificationLink({ link_url: announcement.linkUrl });
  }

  async function openAnnouncementPreview(announcement) {
    previewAnnouncement = announcement;
    await tick();
    previewDialogEl?.focus();
  }

  function closeAnnouncementPreview() {
    previewAnnouncement = null;
  }

  function handlePreviewKeydown(event) {
    if (event.key !== 'Escape' || !previewAnnouncement) return;
    event.preventDefault();
    closeAnnouncementPreview();
  }

  // Covers both initial mount and later auth changes; no separate onMount load.
  $effect(() => {
    const isAuthenticated = $authState.isAuthenticated;
    const loadKey = `${isAuthenticated}:${activeTab}:${unreadOnly}`;
    if (loadKey === lastLoadKey) return;

    lastLoadKey = loadKey;
    if (isAuthenticated) {
      if (activeTab === 'announcements') {
        loadAnnouncements();
      } else {
        loadNotifications(true);
      }
    } else {
      notifications = [];
      totalCount = 0;
      hasNext = false;
      announcements = [];
      previewAnnouncement = null;
    }
  });

  $effect(() => {
    if (activeTab !== 'announcements') {
      previewAnnouncement = null;
    }
  });

  $effect(() => {
    if (!previewAnnouncement || typeof document === 'undefined') return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  });

  onMount(() => {
    document.addEventListener('keydown', handlePreviewKeydown);
    return () => document.removeEventListener('keydown', handlePreviewKeydown);
  });
</script>

<div class="container mx-auto px-4 py-8">
  <div class="max-w-5xl mx-auto">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Notifications</h1>
      {#if $authState.isAuthenticated && activeTab === 'notifications' && totalCount > 0}
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
      <div class="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div class="inline-flex w-fit p-1 bg-white border border-gray-200 rounded-full" role="tablist" aria-label="Notification views">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'notifications'}
            class="px-4 py-1.5 text-sm font-medium rounded-full transition-colors {activeTab === 'notifications' ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'}"
            onclick={() => setTab('notifications')}
          >
            Notifications
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'announcements'}
            class="px-4 py-1.5 text-sm font-medium rounded-full transition-colors {activeTab === 'announcements' ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'}"
            onclick={() => setTab('announcements')}
          >
            Announcements
          </button>
        </div>

        {#if activeTab === 'notifications'}
          <div class="flex items-center gap-3">
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
        {:else}
          <span class="text-sm text-gray-500">{announcements.length} viewed</span>
        {/if}
      </div>

      {#if activeTab === 'notifications' && error}
        <div class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      {/if}

      {#if activeTab === 'announcements'}
        {#if announcementsError}
          <div class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{announcementsError}</div>
        {/if}

        {#if announcementsLoading && announcements.length === 0}
          <div class="announcement-grid">
            {#each Array(6) as _}
              <div class="h-32 bg-white shadow rounded-lg animate-pulse"></div>
            {/each}
          </div>
        {:else if announcements.length === 0}
          <div class="bg-white shadow rounded-lg p-8 text-center">
            <svg class="w-10 h-10 mx-auto text-gray-300" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-7.5A2.25 2.25 0 0017.25 4.5H6.75A2.25 2.25 0 004.5 6.75v10.5A2.25 2.25 0 006.75 19.5h6.75M8.25 8.25h7.5M8.25 12h4.5m3 5.25l1.5 1.5 3-3"></path>
            </svg>
            <h2 class="mt-3 text-lg font-semibold text-gray-900">No viewed announcements yet</h2>
            <p class="mt-1 text-sm text-gray-500">
              Announcements you finish from What's New will appear here.
            </p>
          </div>
        {:else}
          <div class="announcement-grid">
            {#each announcements as announcement (announcement.id)}
              <button
                type="button"
                class="announcement-list-item"
                onclick={() => openAnnouncementPreview(announcement)}
              >
                <span class="flex items-center justify-between gap-2">
                  <span class="text-[11px] font-bold uppercase tracking-wide text-gray-400">{announcement.eyebrow}</span>
                  {#if announcement.showCommunityBadge}
                    <span class="rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-[11px] font-semibold text-green-700">{announcement.audienceLabel}</span>
                  {/if}
                </span>
                <span class="mt-2 block text-sm font-semibold leading-snug text-gray-900">{announcement.title}</span>
                {#if announcement.summary}
                  <span class="announcement-summary">{announcement.summary}</span>
                {/if}
              </button>
            {/each}
          </div>
        {/if}
      {:else if loading && notifications.length === 0}
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
            <!-- div[role=button] instead of <button>: markdown bodies can
                 contain links, and nested <a> inside <button> is invalid. -->
            <div
              role="button"
              tabindex="0"
              class="w-full flex gap-3 px-4 py-4 text-left transition-colors {notification.link_url ? 'cursor-pointer' : 'cursor-default'} {notification.is_read ? 'hover:bg-gray-50' : 'bg-primary-50/60 hover:bg-primary-50'}"
              onclick={(event) => openNotification(notification, event)}
              onkeydown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  openNotification(notification);
                }
              }}
            >
              <span class="mt-1.5 w-2 h-2 rounded-full shrink-0 {notification.is_read ? 'bg-transparent' : notification.priority >= 3 ? 'bg-red-500' : 'bg-primary-500'}"></span>
              <span class="min-w-0 flex-1">
                <span class="flex items-start justify-between gap-4">
                  <span class="text-sm font-medium text-gray-900 leading-snug">{notification.title}</span>
                  <span class="text-xs text-gray-400 whitespace-nowrap shrink-0">{relativeTime(notification.created_at, { verbose: true })}</span>
                </span>
                {#if notification.body}
                  <span class="notification-body block text-sm text-gray-500 leading-snug mt-1">{@html parseUserMarkdown(notification.body)}</span>
                {/if}
                <span class="block text-xs text-gray-400 mt-1.5">
                  {notification.category_label || notification.category}{#if notification.link_url}&nbsp;&middot; {notification.link_label || 'Open'}{/if}
                </span>
              </span>
            </div>
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

{#if previewAnnouncement}
  <div class="announcement-preview-layer">
    <button
      type="button"
      class="announcement-preview-backdrop"
      aria-label="Close announcement preview"
      onclick={closeAnnouncementPreview}
    ></button>
    <div class="announcement-preview-wrap">
      <WhatsNewAnnouncementSurface
        slide={previewAnnouncement}
        bind:dialogEl={previewDialogEl}
        labelledby="announcement-preview-title"
        showClose={true}
        closeLabel="Close announcement preview"
        onClose={closeAnnouncementPreview}
        totalSlides={1}
        currentIndex={0}
        primaryLabel="Done"
        onPrimary={closeAnnouncementPreview}
        onOpenLink={() => openAnnouncementLink(previewAnnouncement)}
      />
    </div>
  </div>
{/if}

<style>
  /* Tailwind preflight zeroes default element styles; restore the few the
     sanitized markdown bodies need. */
  .notification-body :global(p + p) {
    margin-top: 0.375rem;
  }
  .notification-body :global(a) {
    color: #0284c7;
    text-decoration: underline;
  }
  .notification-body :global(ul) {
    list-style: disc;
    padding-left: 1.25rem;
  }
  .notification-body :global(ol) {
    list-style: decimal;
    padding-left: 1.25rem;
  }
  .notification-body :global(code) {
    font-size: 0.8125rem;
    background: #f3f4f6;
    padding: 0 0.25rem;
    border-radius: 0.25rem;
  }

  .announcement-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(18rem, 100%), 1fr));
    gap: 0.75rem;
  }

  .announcement-list-item {
    min-height: 8rem;
    width: 100%;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fff;
    padding: 0.875rem;
    text-align: left;
    box-shadow: 0 6px 16px rgba(31, 42, 68, 0.05);
    transition: border-color 150ms ease, background 150ms ease, box-shadow 150ms ease, transform 150ms ease;
  }

  .announcement-list-item:hover {
    transform: translateY(-1px);
    border-color: #cdd5e3;
    background: #fbfcfe;
    box-shadow: 0 10px 24px rgba(31, 42, 68, 0.08);
  }

  .announcement-list-item:focus-visible {
    outline: 2px solid #0284c7;
    outline-offset: 2px;
  }

  .announcement-summary {
    display: -webkit-box;
    margin-top: 0.45rem;
    overflow: hidden;
    color: #6b7280;
    font-size: 0.78rem;
    line-height: 1.45;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .announcement-preview-layer {
    position: fixed;
    inset: 0;
    z-index: 9000;
    pointer-events: none;
  }

  .announcement-preview-backdrop {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    background: rgba(17, 24, 39, 0.38);
    backdrop-filter: blur(4px) saturate(0.96);
    pointer-events: auto;
    animation: previewBackdropIn 180ms ease-out both;
  }

  .announcement-preview-wrap {
    position: absolute;
    inset: 0;
    z-index: 3;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.25rem;
    pointer-events: none;
  }

  @keyframes previewBackdropIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @media (max-width: 760px) {
    .announcement-preview-wrap {
      align-items: flex-end;
      padding: 0.75rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .announcement-list-item,
    .announcement-preview-backdrop {
      animation: none;
      transition: none;
    }

    .announcement-list-item:hover {
      transform: none;
    }
  }
</style>
