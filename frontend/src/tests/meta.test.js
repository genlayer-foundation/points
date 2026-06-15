import { beforeEach, describe, expect, it } from 'vitest';

import {
  canonicalUrl,
  getRouteMeta,
  setPageMeta,
} from '../lib/meta.js';
import { truncateMetaDescription } from '../lib/metaHelpers.js';

describe('SEO metadata helpers', () => {
  beforeEach(() => {
    document.head.innerHTML = '';
    document.title = '';
  });

  it('normalizes hash routes to canonical path URLs', () => {
    expect(canonicalUrl('https://portal.genlayer.foundation/#/hackathon'))
      .toBe('https://portal.genlayer.foundation/hackathon');
    expect(canonicalUrl('#/builders/resources'))
      .toBe('https://portal.genlayer.foundation/builders/resources');
    expect(canonicalUrl('https://portal.genlayer.foundation/#/hackathon?ref=abc'))
      .toBe('https://portal.genlayer.foundation/hackathon');
  });

  it('canonicalizes legacy route aliases', () => {
    expect(canonicalUrl('/foundations/whitepaper'))
      .toBe('https://portal.genlayer.foundation/genesis/whitepaper');
    expect(canonicalUrl('/participants'))
      .toBe('https://portal.genlayer.foundation/participants');
  });

  it('keeps public routes indexable and protected routes noindex', () => {
    expect(getRouteMeta('/builders/resources').robots).toContain('index,follow');
    expect(getRouteMeta('/builders').robots).toBe('noindex,nofollow');
    expect(getRouteMeta('/stewards/submissions').robots).toBe('noindex,nofollow');
  });

  it('updates title, canonical, robots, social tags, and JSON-LD', () => {
    setPageMeta({
      title: 'Builder Resources for AI-Native Apps | GenLayer Portal',
      description: 'Find GenLayer builder resources and starter projects.',
      path: '/builders/resources',
    });

    expect(document.title).toBe('Builder Resources for AI-Native Apps | GenLayer Portal');
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href'))
      .toBe('https://portal.genlayer.foundation/builders/resources');
    expect(document.querySelector('meta[name="robots"]')?.getAttribute('content'))
      .toContain('max-image-preview:large');
    expect(document.querySelector('meta[property="og:url"]')?.getAttribute('content'))
      .toBe('https://portal.genlayer.foundation/builders/resources');
    expect(document.querySelector('meta[name="twitter:card"]')?.getAttribute('content'))
      .toBe('summary_large_image');

    const jsonLd = document.querySelector('script[type="application/ld+json"][data-seo="page"]');
    expect(jsonLd).toBeTruthy();
    const graph = JSON.parse(jsonLd.textContent)['@graph'];
    expect(
      graph.some((node) => node?.url === 'https://portal.genlayer.foundation/builders/resources')
    ).toBe(true);
  });

  it('preserves non-null falsy values when truncating meta descriptions', () => {
    expect(truncateMetaDescription(0)).toBe('0');
    expect(truncateMetaDescription(false)).toBe('false');
    expect(truncateMetaDescription(null)).toBe('');
    expect(truncateMetaDescription(undefined)).toBe('');
  });
});
