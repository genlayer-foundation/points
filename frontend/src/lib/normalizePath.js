/**
 * Path-to-hash route normalization for the hash-based portal router.
 *
 * The portal uses `svelte-spa-router`, which resolves routes from the URL hash
 * (e.g. `/#/testnets`). Several entry points still produce plain path URLs
 * (e.g. `/testnets`, `/metrics`): sidebar `href` attributes, links opened in a
 * new tab, refreshes of a path-based route, and shared/indexed links. When such
 * a URL is opened directly, the hash is empty, the router has nothing to match,
 * and the user lands on a 404 / NotFound view.
 *
 * This module decides whether a plain path URL should be rewritten into its
 * hash equivalent so the router can resolve it. It is deliberately
 * route-agnostic: any unknown path is forwarded to the router, which renders
 * its own NotFound for genuinely missing routes. Static assets and known
 * server-handled prefixes (OAuth, API) are left untouched.
 */

const RESERVED_PREFIXES = ['/api', '/oauth', '/static', '/assets', '/media'];

function normalizeRoutePath(pathname) {
  if (!pathname || pathname === '/') return '/';
  return pathname.replace(/\/+$/, '') || '/';
}

function looksLikeStaticFile(pathname) {
  const lastSegment = pathname.split('/').pop() || '';
  return lastSegment.includes('.');
}

export function computeNormalizedUrl(location) {
  const pathname = normalizeRoutePath(location.pathname || '/');
  const hash = location.hash || '';
  const search = location.search || '';

  if (hash) return null;
  if (pathname === '/' || pathname === '') return null;
  if (RESERVED_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return null;
  if (looksLikeStaticFile(pathname)) return null;

  return `/#${pathname}${search}`;
}

export function normalizeLocation(
  win = typeof window !== 'undefined' ? window : undefined
) {
  if (!win || !win.location || !win.history) return false;

  const target = computeNormalizedUrl(win.location);
  if (!target) return false;

  win.history.replaceState({}, '', target);
  return true;
}
