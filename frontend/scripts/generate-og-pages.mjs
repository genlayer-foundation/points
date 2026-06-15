import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  DEFAULT_META,
  ROUTE_META_ALIASES,
  SITE_NAME,
  STATIC_OG_ROUTES,
  TWITTER_SITE,
  resolveRouteMeta,
  routeStructuredData,
} from '../src/lib/routeMeta.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');
const distRoot = path.join(frontendRoot, 'dist');
const indexPath = path.join(distRoot, 'index.html');

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function escapeRegExp(value = '') {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function setTitle(html, title) {
  const safe = escapeHtml(title);
  return html.replace(/<title>.*?<\/title>/s, () => `<title>${safe}</title>`);
}

function setMetaContent(html, attrName, attrValue, content) {
  const safe = escapeHtml(content);
  const attr = escapeRegExp(attrName);
  const value = escapeRegExp(attrValue);
  const pattern = new RegExp(`<meta\\b(?=[^>]*\\b${attr}="${value}")[^>]*>`, 'i');

  return html.replace(pattern, (tag) => {
    if (/\bcontent="/i.test(tag)) {
      return tag.replace(/\bcontent="[^"]*"/i, () => `content="${safe}"`);
    }

    return tag.replace(/\/?>$/, (end) => ` content="${safe}"${end}`);
  });
}

function setNamedMeta(html, name, content) {
  return setMetaContent(html, 'name', name, content);
}

function setPropertyMeta(html, property, content) {
  return setMetaContent(html, 'property', property, content);
}

function setCanonicalLink(html, href) {
  const safe = escapeHtml(href);
  const pattern = /<link\b(?=[^>]*\brel="canonical")[^>]*>/i;

  if (pattern.test(html)) {
    return html.replace(pattern, (tag) => {
      if (/\bhref="/i.test(tag)) {
        return tag.replace(/\bhref="[^"]*"/i, () => `href="${safe}"`);
      }

      return tag.replace(/\/?>$/, (end) => ` href="${safe}"${end}`);
    });
  }

  return html.replace(/<head>/i, (tag) => `${tag}\n  <link rel="canonical" href="${safe}" />`);
}

function upsertJsonLd(html, id, data) {
  const safeJson = JSON.stringify(data)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026');
  const script = `<script type="application/ld+json" data-seo="${escapeHtml(id)}">${safeJson}</script>`;
  const pattern = new RegExp(
    `<script\\b(?=[^>]*\\btype="application/ld\\+json")(?=[^>]*\\bdata-seo="${escapeRegExp(id)}")[^>]*>.*?<\\/script>`,
    'is'
  );

  if (pattern.test(html)) {
    return html.replace(pattern, script);
  }

  return html.replace(/<\/head>/i, `  ${script}\n</head>`);
}

function applyMeta(html, meta) {
  let next = setTitle(html, meta.title);
  next = setCanonicalLink(next, meta.url);
  next = setNamedMeta(next, 'robots', meta.robots || DEFAULT_META.robots);
  next = setNamedMeta(next, 'title', meta.title);
  next = setNamedMeta(next, 'description', meta.description);
  next = setPropertyMeta(next, 'og:type', meta.type || 'website');
  next = setPropertyMeta(next, 'og:url', meta.url);
  next = setPropertyMeta(next, 'og:title', meta.title);
  next = setPropertyMeta(next, 'og:description', meta.description);
  next = setPropertyMeta(next, 'og:image', meta.image);
  next = setPropertyMeta(next, 'og:image:width', meta.imageWidth || DEFAULT_META.imageWidth);
  next = setPropertyMeta(next, 'og:image:height', meta.imageHeight || DEFAULT_META.imageHeight);
  next = setPropertyMeta(next, 'og:site_name', SITE_NAME);
  next = setNamedMeta(next, 'twitter:card', 'summary_large_image');
  next = setNamedMeta(next, 'twitter:url', meta.url);
  next = setNamedMeta(next, 'twitter:title', meta.title);
  next = setNamedMeta(next, 'twitter:description', meta.description);
  next = setNamedMeta(next, 'twitter:image', meta.image);
  next = setNamedMeta(next, 'twitter:site', TWITTER_SITE);
  next = upsertJsonLd(next, 'page', routeStructuredData(meta));
  return next;
}

function routeOutputPath(route) {
  const clean = route.replace(/^\/+/, '').replace(/\/+$/, '');
  return path.join(distRoot, clean, 'index.html');
}

const template = await readFile(indexPath, 'utf8');

for (const route of STATIC_OG_ROUTES) {
  const meta = resolveRouteMeta(route);
  const outputPath = routeOutputPath(route);
  await mkdir(path.dirname(outputPath), { recursive: true });
  await writeFile(outputPath, applyMeta(template, meta));
}

const aliasCount = Object.keys(ROUTE_META_ALIASES).length;
console.log(`Generated ${STATIC_OG_ROUTES.length} route OG pages (${aliasCount} aliases included).`);
