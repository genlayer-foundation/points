const BASE_URL = 'https://portal.genlayer.foundation/';
const DEFAULT_IMAGE = BASE_URL + 'assets/portal_og_image.png';
const DEFAULT_TITLE = "GenLayer's Incentivized Builder Program";
const DEFAULT_DESCRIPTION =
  "GenLayer's Incentivized Builder Program rewards early contributors who help build the foundation of the GenLayer ecosystem across code, infrastructure, and community growth. Participation is open to everyone.";

function updateTag(selector, value) {
  const el = document.querySelector(selector);
  if (el) el.setAttribute('content', value);
}

export function setPageMeta({ title, description, image, imageWidth, imageHeight, url }) {
  const t = title || DEFAULT_TITLE;
  const d = description || DEFAULT_DESCRIPTION;
  const img = image || DEFAULT_IMAGE;
  const w = imageWidth || '1200';
  const h = imageHeight || '630';
  const u = url || BASE_URL;

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
  setPageMeta({
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
    image: DEFAULT_IMAGE,
    imageWidth: '1200',
    imageHeight: '630',
    url: BASE_URL,
  });
}
