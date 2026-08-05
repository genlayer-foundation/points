import { push } from 'svelte-spa-router';
import { resolvePortalLink } from './links.js';
import { parseUserMarkdown } from './markdownLoader.js';

export const NOTIFICATION_BODY_PREVIEW_LENGTH = 120;

/** Normalize paginated or plain-array API payloads into a list. */
export function asList(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

/**
 * Convert markdown to compact, sanitized HTML for the navbar dropdown.
 * @param {unknown} body
 * @param {number} maxLength
 * @returns {string}
 */
export function notificationBodyPreview(
  body,
  maxLength = NOTIFICATION_BODY_PREVIEW_LENGTH
) {
  if (typeof body !== 'string' || maxLength <= 0) return '';

  const wrapper = document.createElement('div');
  wrapper.innerHTML = parseUserMarkdown(body);
  wrapper.querySelectorAll('br').forEach((breakElement) => {
    breakElement.replaceWith(document.createTextNode(' '));
  });

  const text = (wrapper.textContent || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  if (maxLength === 1) return '…';

  const truncated = text.length > maxLength;
  let previewText = truncated ? text.slice(0, maxLength - 1).trimEnd() : text;
  const lastWordBreak = previewText.lastIndexOf(' ');
  if (truncated && lastWordBreak >= Math.floor(maxLength * 0.6)) {
    previewText = previewText.slice(0, lastWordBreak);
  }

  let remaining = previewText.length;
  let previousEndsWithSpace = true;
  let ellipsisAdded = !truncated;
  const walker = document.createTreeWalker(wrapper, NodeFilter.SHOW_TEXT);

  while (walker.nextNode()) {
    const node = walker.currentNode;
    let normalized = (node.textContent || '').replace(/\s+/g, ' ');
    if (previousEndsWithSpace) normalized = normalized.trimStart();

    if (remaining === 0) {
      node.textContent = '';
      continue;
    }

    const kept = normalized.slice(0, remaining);
    node.textContent = kept;
    remaining -= kept.length;
    previousEndsWithSpace = kept.endsWith(' ');

    if (remaining === 0 && !ellipsisAdded) {
      node.textContent = `${kept.trimEnd()}…`;
      ellipsisAdded = true;
    }
  }

  return wrapper.innerHTML;
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
