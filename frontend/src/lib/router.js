/**
 * History-based router core — drop-in replacement for `svelte-spa-router`'s
 * navigation API, but reading `window.location.pathname` instead of the hash.
 *
 * Why: hash URLs (`/#/hackathon`) drop their fragment before reaching the
 * server, so crawlers and copied links never resolve to the right prerendered
 * page. History URLs (`/hackathon`) do. `svelte-spa-router` is hash-only, so we
 * own a thin equivalent that keeps the same public API (push/replace/pop,
 * `location`/`querystring`/`params` stores, the `link` action). Route matching
 * is delegated to `regexparam` — the very library `svelte-spa-router` uses — so
 * `:param`/`*` behaviour is identical. The matching component lives in
 * `Router.svelte`; `wrap()` lives in `wrap.js`.
 */
import { readable, derived, writable } from 'svelte/store';
import { tick } from 'svelte';
import { parse } from 'regexparam';

// Fired by push/replace so the loc store recomputes (History API mutations
// don't emit popstate on their own).
const NAV_EVENT = 'spa-router:navigate';

function getLocation() {
  if (typeof window === 'undefined') return { location: '/', querystring: '' };
  const location = window.location.pathname || '/';
  const search = window.location.search || '';
  return { location, querystring: search ? search.substr(1) : '' };
}

/** Current `{ location, querystring }`, updated on nav + back/forward. */
export const loc = readable(getLocation(), (set) => {
  const update = () => set(getLocation());
  window.addEventListener('popstate', update);
  window.addEventListener(NAV_EVENT, update);
  return () => {
    window.removeEventListener('popstate', update);
    window.removeEventListener(NAV_EVENT, update);
  };
});

export const location = derived(loc, (l) => l.location);
export const querystring = derived(loc, (l) => l.querystring);

// Writable per svelte-spa-router parity; the Router sets it, consumers read it.
export const params = writable(undefined);

// ponytail: tolerate legacy '#/...' callers (old code / shared links) by
// stripping a leading '#'. New code passes plain '/path'.
function normalize(path) {
  if (!path || path.length < 1) throw Error('Invalid parameter location');
  return path.charAt(0) === '#' ? path.slice(1) : path;
}

export async function push(path) {
  const dest = normalize(path);
  await tick();
  window.history.pushState({}, '', dest);
  window.dispatchEvent(new Event(NAV_EVENT));
}

export async function replace(path) {
  const dest = normalize(path);
  await tick();
  window.history.replaceState({}, '', dest);
  window.dispatchEvent(new Event(NAV_EVENT));
}

export async function pop() {
  await tick();
  window.history.back();
}

// Prefixes the server/static layer owns — never SPA-navigate these.
const RESERVED_PREFIXES = ['/api', '/oauth', '/static', '/assets', '/media'];

/**
 * Decide the in-app path to navigate to for an anchor href, or null to leave it
 * to the browser. Returns null for in-page (`#...`) anchors, external origins,
 * reserved prefixes, and file-looking paths. Legacy `/#/route` links resolve to
 * the route in their hash fragment (otherwise the router would read only the
 * pathname `/` and land on home).
 */
export function linkNavTarget(href, baseHref) {
  if (!href || href.charAt(0) === '#') return null; // inert / in-page anchors
  let url;
  try { url = new URL(href, baseHref); } catch { return null; }
  if (url.origin !== new URL(baseHref).origin) return null; // external
  const target = url.hash.startsWith('#/')
    ? url.hash.slice(1)                       // legacy "/#/route" -> "/route"
    : url.pathname + url.search + url.hash;
  if (RESERVED_PREFIXES.some((p) => target.startsWith(p))) return null;
  const last = target.split('?')[0].split('/').pop() || '';
  if (last.includes('.')) return null; // looks like a static file
  return target;
}

/**
 * One delegated click handler so every same-origin `<a href="/path">` navigates
 * via the SPA without a full reload — no need for `use:link` on each anchor.
 * Bails when another handler already called preventDefault (components that
 * push() themselves), on modified/new-tab/download clicks, and anything
 * linkNavTarget() rejects, which fall through to normal browser handling.
 */
export function installLinkInterceptor() {
  function onClick(e) {
    if (e.defaultPrevented || e.button !== 0 ||
        e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const anchor = e.target.closest?.('a');
    if (!anchor || anchor.target === '_blank' || anchor.hasAttribute('download')) return;
    const target = linkNavTarget(anchor.getAttribute('href'), window.location.href);
    if (target === null) return;
    e.preventDefault();
    push(target);
  }
  document.addEventListener('click', onClick);
  return () => document.removeEventListener('click', onClick);
}

// ---- Route matching (delegated to regexparam, like svelte-spa-router) ----

/**
 * Compile a `{ '/path': component }` map into a matchable list, preserving
 * insertion order so literal routes beat :param ones and '*' (last) catches all.
 * Components wrapped by wrap() carry conditions/props/userData.
 */
export function buildRoutes(routes) {
  return Object.keys(routes).map((path) => {
    const def = routes[path];
    const wrapped = def && typeof def === 'object' && def._sveltesparouter === true;
    const { pattern, keys } = parse(path);
    return {
      path, pattern, keys,
      component: wrapped ? def.component : def,
      conditions: wrapped ? def.conditions : [],
      props: wrapped ? def.props : {},
      userData: wrapped ? def.userData : undefined,
    };
  });
}

/** First matching route for `pathname` (no querystring), with decoded params. */
export function matchRoute(routesList, pathname) {
  for (const route of routesList) {
    const m = route.pattern.exec(pathname);
    if (m === null) continue;
    const params = {};
    route.keys.forEach((k, i) => {
      try { params[k] = decodeURIComponent(m[i + 1] || '') || null; }
      catch { params[k] = null; }
    });
    return { route, params };
  }
  return null;
}

function linkOpts(val) {
  return val && typeof val === 'string' ? { href: val } : val || {};
}

/**
 * `use:link` action — intercept left-clicks on an `<a>` and navigate via the
 * History API instead of a full page load. Modified clicks (new tab, etc.) and
 * `target=_blank` fall through to the browser.
 */
export function link(node, opts) {
  let current = linkOpts(opts);
  function onClick(event) {
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey || event.ctrlKey || event.shiftKey || event.altKey ||
      node.target === '_blank' ||
      current.disabled
    ) {
      return;
    }
    // Same normalization/guards as the global interceptor (legacy '#/' links,
    // external/file/reserved fall through to the browser).
    const target = linkNavTarget(current.href || node.getAttribute('href'), window.location.href);
    if (target === null) return;
    event.preventDefault();
    push(target);
  }
  node.addEventListener('click', onClick);
  return {
    update(updated) { current = linkOpts(updated); },
    destroy() { node.removeEventListener('click', onClick); },
  };
}
