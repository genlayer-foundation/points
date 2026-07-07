import {
  DEFAULT_META,
  DEFAULT_ROBOTS,
  ROUTE_META_ALIASES,
  SITE_NAME,
  SITE_URL,
  TWITTER_SITE,
  routeStructuredData,
  resolveRouteMeta,
} from './routeMeta.js';
import { m } from './paraglide/messages.js';
import { getLocale, ogLocale } from './i18n.js';

// Runtime locale overlay for route metadata. routeMeta.js itself stays plain
// English strings because scripts/generate-og-pages.mjs imports it in Node at
// build time; static OG pages are prerendered in English by design. Keyed by
// canonical route path; add entries here as pages get translated.
const LOCALIZED_ROUTE_META = {
  '/': () => ({ description: m.meta_home_description() }),
};

function localizeRouteMeta(path, meta) {
  const canonicalPath = canonicalUrl(path).slice(SITE_URL.length) || '/';
  const overlay = LOCALIZED_ROUTE_META[canonicalPath];
  return overlay ? { ...meta, ...overlay() } : meta;
}

function localizeStructuredData(data) {
  if (!data || !Array.isArray(data['@graph'])) return data;
  return {
    ...data,
    '@graph': data['@graph'].map((node) =>
      'inLanguage' in node ? { ...node, inLanguage: getLocale() } : node
    ),
  };
}

function ensureMeta(selector, attrs) {
  let el = document.querySelector(selector);
  if (!el) {
    el = document.createElement('meta');
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    document.head.appendChild(el);
  }
  return el;
}

function updateTag(selector, value, attrs) {
  const el = ensureMeta(selector, attrs);
  el.setAttribute('content', value);
}

function updateLink(selector, attrs) {
  let el = document.querySelector(selector);
  if (!el) {
    el = document.createElement('link');
    document.head.appendChild(el);
  }
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
}

function upsertJsonLd(id, data) {
  const selector = `script[type="application/ld+json"][data-seo="${id}"]`;
  let el = document.querySelector(selector);
  if (!el) {
    el = document.createElement('script');
    el.type = 'application/ld+json';
    el.dataset.seo = id;
    document.head.appendChild(el);
  }
  el.textContent = JSON.stringify(data);
}

function stripTrailingSlash(path) {
  if (!path || path === '/') return '/';
  return path.replace(/\/+$/, '');
}

export function canonicalUrl(value = '/') {
  try {
    const parsed = new URL(String(value || '/'), `${SITE_URL}/`);
    const path = parsed.hash.startsWith('#/')
      ? parsed.hash.slice(1)
      : parsed.pathname;
    const normalizedPath = stripTrailingSlash(path.split('?')[0].split('#')[0] || '/');
    const canonicalPath = ROUTE_META_ALIASES[normalizedPath] || normalizedPath;
    return `${SITE_URL}${canonicalPath === '/' ? '/' : canonicalPath}`;
  } catch {
    const raw = String(value || '/');
    const hashIndex = raw.indexOf('#/');
    const routePath = hashIndex >= 0 ? raw.slice(hashIndex + 1) : raw;
    const path = stripTrailingSlash(routePath.split('?')[0].split('#')[0] || '/');
    const normalizedPath = path === '/' ? '/' : path.startsWith('/') ? path : `/${path}`;
    const canonicalPath = ROUTE_META_ALIASES[normalizedPath] || normalizedPath;
    return `${SITE_URL}${canonicalPath === '/' ? '/' : canonicalPath}`;
  }
}

export function getRouteMeta(path = '/') {
  return resolveRouteMeta(path);
}

export function setPageMeta({
  title,
  description,
  image,
  imageWidth,
  imageHeight,
  url,
  path,
  robots,
  structuredData,
} = {}) {
  const t = title || DEFAULT_META.title;
  const d = description || DEFAULT_META.description;
  const img = image || DEFAULT_META.image;
  const w = imageWidth || DEFAULT_META.imageWidth;
  const h = imageHeight || DEFAULT_META.imageHeight;
  const u = canonicalUrl(path || url || DEFAULT_META.url);
  const robotValue = robots || DEFAULT_ROBOTS;

  document.title = t;
  updateLink('link[rel="canonical"]', { rel: 'canonical', href: u });
  updateTag('meta[name="robots"]', robotValue, { name: 'robots' });
  updateTag('meta[name="title"]', t, { name: 'title' });
  updateTag('meta[name="description"]', d, { name: 'description' });
  updateTag('meta[property="og:type"]', 'website', { property: 'og:type' });
  updateTag('meta[property="og:title"]', t, { property: 'og:title' });
  updateTag('meta[property="og:description"]', d, { property: 'og:description' });
  updateTag('meta[property="og:image"]', img, { property: 'og:image' });
  updateTag('meta[property="og:image:width"]', w, { property: 'og:image:width' });
  updateTag('meta[property="og:image:height"]', h, { property: 'og:image:height' });
  updateTag('meta[property="og:url"]', u, { property: 'og:url' });
  updateTag('meta[property="og:site_name"]', SITE_NAME, { property: 'og:site_name' });
  updateTag('meta[property="og:locale"]', ogLocale(), { property: 'og:locale' });
  updateTag('meta[name="twitter:card"]', 'summary_large_image', { name: 'twitter:card' });
  updateTag('meta[name="twitter:title"]', t, { name: 'twitter:title' });
  updateTag('meta[name="twitter:description"]', d, { name: 'twitter:description' });
  updateTag('meta[name="twitter:image"]', img, { name: 'twitter:image' });
  updateTag('meta[name="twitter:url"]', u, { name: 'twitter:url' });
  updateTag('meta[name="twitter:site"]', TWITTER_SITE, { name: 'twitter:site' });

  upsertJsonLd(
    'page',
    localizeStructuredData(
      structuredData || routeStructuredData({ title: t, description: d, url: u, image: img })
    )
  );
}

export function setRouteMeta(path) {
  setPageMeta(localizeRouteMeta(path, resolveRouteMeta(path)));
}

export function resetPageMeta() {
  setPageMeta(DEFAULT_META);
}
