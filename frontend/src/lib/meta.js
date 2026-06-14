import { DEFAULT_META, resolveRouteMeta } from './routeMeta.js';

function updateTag(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.setAttribute('content', value);
}

export function setPageMeta({ title, description, image, imageWidth, imageHeight, url }) {
  const t = title || DEFAULT_META.title;
  const d = description || DEFAULT_META.description;
  const img = image || DEFAULT_META.image;
  const w = imageWidth || DEFAULT_META.imageWidth;
  const h = imageHeight || DEFAULT_META.imageHeight;
  const u = url || DEFAULT_META.url;

  document.title = t;
  updateTag('meta[name="title"]', t);
  updateTag('meta[name="description"]', d);
  updateTag('meta[property="og:title"]', t);
  updateTag('meta[property="og:description"]', d);
  updateTag('meta[property="og:image"]', img);
  updateTag('meta[property="og:image:width"]', w);
  updateTag('meta[property="og:image:height"]', h);
  updateTag('meta[property="og:url"]', u);
  updateTag('meta[name="twitter:title"]', t);
  updateTag('meta[name="twitter:description"]', d);
  updateTag('meta[name="twitter:image"]', img);
  updateTag('meta[name="twitter:url"]', u);
}

export function resetPageMeta() {
  setPageMeta(DEFAULT_META);
}

export function setRouteMeta(path) {
  setPageMeta(resolveRouteMeta(path));
}
