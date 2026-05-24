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

// Prefixes that are handled outside the SPA router and must never be
// rewritten into hash routes.
const RESERVED_PREFIXES = ['/api', '/oauth', '/static', '/assets', '/media'];

/**
 * Returns true when `pathname` looks like a request for a static file, e.g.
 * `/favicon.ico`, `/robots.txt`, `/assets/app.123.js`. Such requests must not
 * be turned into hash routes. We treat a final path segment that contains a
 * dot as a file request.
 *
 * @param {string} pathname
 * @returns {boolean}
 */
function looksLikeStaticFile(pathname) {
  const lastSegment = pathname.split('/').pop() || '';
  return lastSegment.includes('.');
}

/**
 * Given a `window.location`-like object, compute the normalized URL the app
 * should switch to, or `null` when no normalization is needed.
 *
 * Normalization applies when ALL of the following hold:
 *   - there is no existing hash (a hash route is already resolvable), and
 *   - the path is not the root `/` (root maps to `#/` implicitly), and
 *   - the path is not a reserved/server-handled prefix, and
 *   - the path does not look like a static file request.
 *
 * The returned URL preserves the original query string and moves the path into
 * the hash, e.g. `/testnets?foo=1` -> `/#/testnets?foo=1`.
 *
 * @param {{ pathname: string, hash?: string, search?: string }} location
 * @returns {string | null} the URL to replace, or null if no change is needed
 */
export function computeNormalizedUrl(location) {
  const pathname = location.pathname || '/';
  const hash = location.hash || '';
  const search = location.search || '';

  if (hash) return null;
  if (pathname === '/' || pathname === '') return null;
  if (RESERVED_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return null;
  if (looksLikeStaticFile(pathname)) return null;

  return `/#${pathname}${search}`;
}

/**
 * Side-effecting helper for use at app startup. Rewrites the current URL via
 * `history.replaceState` when normalization is needed, so the hash router can
 * resolve direct/path-based links without a full navigation or 404.
 *
 * Safe to call when `window`/`history` are unavailable (e.g. SSR/tests): it
 * simply does nothing and returns false.
 *
 * @param {Window} [win=window]
 * @returns {boolean} true if the URL was rewritten
 */
export function normalizeLocation(win = typeof window !== 'undefined' ? window : undefined) {
  if (!win || !win.location || !win.history) return false;

  const target = computeNormalizedUrl(win.location);
  if (!target) return false;

  win.history.replaceState({}, '', target);
  return true;
}
