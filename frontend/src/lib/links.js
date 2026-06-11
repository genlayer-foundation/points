/**
 * Content-link resolution for the hash-based portal router.
 *
 * Links managed through the admin (hero banners, GenNews announcements) are
 * stored in a URLField, so links that point back into the portal itself
 * arrive as absolute URLs (e.g. `https://portal.genlayer.foundation/#/mission/7`).
 * Treating those as external opens the portal in a new tab, where the browser
 * back button has no history to return to. This helper classifies a raw link
 * and rewrites same-origin URLs into in-app hash routes so they navigate
 * within the SPA and keep browser history intact.
 */

/**
 * @param {string | null | undefined} raw - Link as stored in the content item.
 * @param {string} [origin] - Origin the portal is served from (injectable for tests).
 * @returns {{ href: string, external: boolean }} `href` ready for an anchor;
 *   `external` is true only for links that leave the portal (open in a new tab).
 */
export function resolvePortalLink(
  raw,
  origin = typeof window !== 'undefined' ? window.location.origin : ''
) {
  if (!raw || raw === '#') return { href: '#', external: false };
  if (raw.startsWith('#')) return { href: raw, external: false };
  if (raw.startsWith('/')) return { href: `#${raw}`, external: false };

  let url;
  try {
    url = new URL(raw);
  } catch {
    // Not absolute and not a path — leave untouched, navigate in place.
    return { href: raw, external: false };
  }

  if (origin && url.origin === origin) {
    if (url.hash.startsWith('#/')) return { href: url.hash, external: false };
    if (url.pathname && url.pathname !== '/') {
      return { href: `#${url.pathname}${url.search}`, external: false };
    }
    return { href: '#/', external: false };
  }

  return { href: raw, external: true };
}
