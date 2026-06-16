import { push } from 'svelte-spa-router';

/** Normalize paginated or plain-array API payloads into a list. */
export function asList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/** Follow a notification's link: external URLs in a new tab, internal routes in-app. */
export function followNotificationLink(notification) {
  const url = notification.link_url || '';
  if (!url) return;

  if (url.startsWith('http://') || url.startsWith('https://')) {
    window.open(url, '_blank', 'noopener,noreferrer');
    return;
  }

  push(url.startsWith('#/') ? url.slice(1) : url);
}
