import { push } from 'svelte-spa-router';
import { resolvePortalLink } from './links.js';

/** Normalize paginated or plain-array API payloads into a list. */
export function asList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/**
 * Follow a notification's link. Same-origin links (including legacy `#/...` and
 * absolute portal URLs) route in-app; genuinely external links open in a new
 * tab. resolvePortalLink does the classification and normalization.
 */
export function followNotificationLink(notification) {
  const url = notification.link_url || '';
  if (!url) return;

  const { href, external } = resolvePortalLink(url);
  if (external) {
    window.open(href, '_blank', 'noopener,noreferrer');
    return;
  }
  if (!href || href.startsWith('#')) return; // inert / in-page anchor
  push(href);
}
