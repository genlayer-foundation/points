import { parseUserMarkdown } from './markdownLoader.js';

export const FALLBACK_IMAGE = '/assets/portal_og_image.png';
export const CAUGHT_UP_GRADIENT =
  'linear-gradient(135deg, rgba(127, 82, 225, 0.08), rgba(25, 166, 99, 0.08))';

export const AUDIENCE_META = {
  all: {
    label: 'All portal users',
    accent: '#0284c7',
    gradient:
      'linear-gradient(135deg, rgba(127, 82, 225, 0.08), rgba(2, 132, 199, 0.08), rgba(25, 166, 99, 0.08))',
  },
  builders: {
    label: 'Builders',
    accent: '#db6917',
    gradient: 'linear-gradient(135deg, rgba(219, 105, 23, 0.16), rgba(255, 209, 163, 0.12))',
  },
  validators: {
    label: 'Validators',
    accent: '#2563eb',
    gradient: 'linear-gradient(135deg, rgba(31, 86, 242, 0.14), rgba(184, 199, 255, 0.14))',
  },
  stewards: {
    label: 'Stewards',
    accent: '#111827',
    gradient: 'linear-gradient(135deg, rgba(17, 24, 39, 0.12), rgba(80, 96, 120, 0.08))',
  },
  community: {
    label: 'Community',
    accent: '#19A663',
    gradient: 'linear-gradient(135deg, rgba(25, 166, 99, 0.14), rgba(127, 82, 225, 0.10))',
  },
};

export function audienceMeta(audience) {
  return AUDIENCE_META[audience] || AUDIENCE_META.all;
}

export function normalizeEyebrow(eyebrow) {
  if (!eyebrow || eyebrow.trim().toLowerCase() === 'what is new') return "What's new";
  return eyebrow;
}

export function cleanAnnouncementSummary(body) {
  return (body || '')
    .replace(/[#*_`[\]()]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

export function normalizeWhatsNewItem(item) {
  const audience = item.audience || 'all';
  const meta = audienceMeta(audience);
  const body = item.body || 'A new portal update is available.';

  return {
    id: item.id,
    audience,
    audienceLabel: item.audience_label || meta.label,
    eyebrow: normalizeEyebrow(item.eyebrow),
    title: item.title || 'Portal update',
    body,
    bodyHtml: parseUserMarkdown(body),
    summary: cleanAnnouncementSummary(body),
    linkUrl: item.link_url || '',
    linkLabel: item.link_label || 'Open update',
    accent: meta.accent,
    gradient: meta.gradient,
    image: item.image_url || FALLBACK_IMAGE,
    showCommunityBadge: audience === 'community',
  };
}
