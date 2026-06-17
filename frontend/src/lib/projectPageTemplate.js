import { isSafeHttpUrl } from './urlSafety.js';

const ATTR_PATTERN = /([a-z_]+)=(?:"([^"]*)"|'([^']*)'|([^\s]+))/gi;
const MEDIA_TAG_PATTERN = /^<(Image|Video)\s+([^>]*)\/>\s*$/i;
const MEDIA_TAG_PATTERN_GLOBAL = /^<(Image|Video)\s+([^>]*)\/>\s*$/gim;
const JSX_LIKE_PATTERN = /<\/?[A-Z][A-Za-z0-9]*(?:\s|>|\/>)/;

/** @param {string} markdown */
export function renderProjectMarkdown(markdown) {
  const source = String(markdown || '').trim();
  if (!source) return '';

  return source
    .split(/\n{2,}/)
    .map((chunk) => renderMarkdownChunk(chunk.trim()))
    .filter(Boolean)
    .join('');
}

/** @param {string} value */
export function getMarkdownTextLength(value) {
  return String(value || '')
    .replace(MEDIA_TAG_PATTERN_GLOBAL, '')
    .replace(/\s+/g, ' ')
    .trim()
    .length;
}

/**
 * @param {string} markdown
 * @param {string} sectionName
 */
export function validateProjectMarkdownMedia(markdown, sectionName = 'About') {
  const issues = [];
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || !JSX_LIKE_PATTERN.test(trimmed)) continue;

    const mediaMatch = trimmed.match(MEDIA_TAG_PATTERN);
    if (!mediaMatch) {
      issues.push(`${sectionName} only supports standalone <Image ... /> and <Video ... /> tags.`);
      continue;
    }

    const tagName = mediaMatch[1].toLowerCase();
    const attrs = parseAttrs(mediaMatch[2]);
    const allowedAttrs = tagName === 'image'
      ? new Set(['src', 'caption', 'alt'])
      : new Set(['url', 'title', 'caption']);
    for (const attrName of Object.keys(attrs)) {
      if (!allowedAttrs.has(attrName)) {
        issues.push(`${sectionName} ${mediaMatch[1]} tag has unsupported "${attrName}" attribute.`);
      }
    }

    const url = tagName === 'image' ? attrs.src : attrs.url;
    if (!url) {
      issues.push(`${sectionName} ${mediaMatch[1]} tag requires ${tagName === 'image' ? 'src' : 'url'}.`);
    } else if (!isSafeHttpUrl(url)) {
      issues.push(`${sectionName} ${mediaMatch[1]} URL must be a full http(s) URL.`);
    }
  }
  return issues;
}

/** @param {string} chunk */
function renderMarkdownChunk(chunk) {
  const lines = chunk.split('\n').map((line) => line.trimEnd()).filter(Boolean);
  if (!lines.length) return '';

  if (lines.length === 1) {
    const mediaHtml = renderMediaTag(lines[0]);
    if (mediaHtml) return mediaHtml;
  }

  if (lines.every((line) => /^[-*]\s+/.test(line))) {
    return `<ul>${lines.map((line) => `<li>${renderInline(line.replace(/^[-*]\s+/, ''))}</li>`).join('')}</ul>`;
  }

  if (lines.every((line) => /^\d+\.\s+/.test(line))) {
    return `<ol>${lines.map((line) => `<li>${renderInline(line.replace(/^\d+\.\s+/, ''))}</li>`).join('')}</ol>`;
  }

  const headingMatch = lines[0].match(/^###\s+(.+)$/);
  if (headingMatch) {
    const rest = lines.slice(1).map(renderInline).join('<br>');
    return `<h3>${renderInline(headingMatch[1])}</h3>${rest ? `<p>${rest}</p>` : ''}`;
  }

  return `<p>${lines.map(renderInline).join('<br>')}</p>`;
}

/** @param {string} line */
function renderMediaTag(line) {
  const match = line.trim().match(MEDIA_TAG_PATTERN);
  if (!match) return '';
  const tagName = match[1].toLowerCase();
  const attrs = parseAttrs(match[2]);
  const url = tagName === 'image' ? attrs.src : attrs.url;
  if (!isSafeHttpUrl(url)) return '';

  if (tagName === 'image') {
    const caption = attrs.caption ? `<figcaption>${renderInline(attrs.caption)}</figcaption>` : '';
    const alt = escapeHtml(attrs.alt || attrs.caption || 'Project image');
    return [
      '<figure class="project-mdx-media project-mdx-image">',
      `<img src="${escapeHtml(url)}" alt="${alt}" loading="lazy" />`,
      caption,
      '</figure>',
    ].join('');
  }

  const media = getVideoEmbed(url);
  const title = escapeHtml(attrs.title || 'Project video');
  const caption = attrs.caption ? `<figcaption>${renderInline(attrs.caption)}</figcaption>` : '';
  const content = media.type === 'iframe'
    ? `<iframe title="${title}" src="${escapeHtml(media.src)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`
    : media.type === 'video'
      ? `<video src="${escapeHtml(media.src)}" controls playsinline></video>`
      : `<a class="project-mdx-video-link" href="${escapeHtml(media.src)}" target="_blank" rel="noopener noreferrer">${title}</a>`;
  return [
    '<figure class="project-mdx-media project-mdx-video">',
    `<div class="project-mdx-video-frame">${content}</div>`,
    caption,
    '</figure>',
  ].join('');
}

/** @param {string} value */
function getVideoEmbed(value) {
  const url = new URL(value);
  const host = url.hostname.replace(/^www\./, '');
  const pathParts = url.pathname.split('/').filter(Boolean);

  if (host.includes('youtube.com') || host.includes('youtu.be')) {
    let id = '';
    if (host.includes('youtu.be')) {
      id = pathParts[0] || '';
    } else {
      id = url.searchParams.get('v') || '';
      if (!id && pathParts[0] === 'embed') id = pathParts[1] || '';
      if (!id && pathParts[0] === 'shorts') id = pathParts[1] || '';
    }
    if (id) return { type: 'iframe', src: `https://www.youtube.com/embed/${id}` };
  }

  if (host.includes('vimeo.com')) {
    const id = pathParts.find((part) => /^\d+$/.test(part));
    if (id) return { type: 'iframe', src: `https://player.vimeo.com/video/${id}` };
  }

  if (host.includes('loom.com')) {
    const shareIndex = pathParts.indexOf('share');
    const id = shareIndex >= 0 ? pathParts[shareIndex + 1] : '';
    if (id) return { type: 'iframe', src: `https://www.loom.com/embed/${id}` };
  }

  if (/\.(mp4|webm|ogg)$/i.test(url.pathname)) {
    return { type: 'video', src: url.toString() };
  }

  return { type: 'link', src: url.toString() };
}

/** @param {string | undefined} attrText */
function parseAttrs(attrText) {
  /** @type {Record<string, string>} */
  const attrs = {};
  ATTR_PATTERN.lastIndex = 0;
  let match = ATTR_PATTERN.exec(attrText || '');
  while (match) {
    attrs[match[1].toLowerCase()] = (match[2] || match[3] || match[4] || '').trim();
    match = ATTR_PATTERN.exec(attrText || '');
  }
  return attrs;
}

/** @param {string | undefined} text */
function renderInline(text) {
  return escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}

/** @param {string | undefined} value */
function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
