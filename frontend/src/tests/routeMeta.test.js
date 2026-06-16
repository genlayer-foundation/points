import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

import { OG_IMAGES, SITE_URL, STATIC_OG_ROUTES, resolveRouteMeta } from '../lib/routeMeta.js';

const expectedRouteImages = {
  '/': '/assets/og/portal.png',
  '/how-it-works': '/assets/og/how-it-works.png',
  '/referral-program': '/assets/og/referral-program.png',
  '/hackathon': '/assets/og/hackathon.png',
  '/hackathon-winners': '/assets/og/hackathon-winners.png',
  '/genesis': '/assets/og/genesis.png',
  '/genesis/manifesto': '/assets/og/genesis-manifesto.png',
  '/genesis/whitepaper': '/assets/og/genesis-whitepaper.png',
  '/genesis/compass': '/assets/og/genesis-compass.png',
  '/gen-tv': '/assets/og/gen-tv.png',
  '/gen-news': '/assets/og/gen-news.png',
  '/ecosystem-partners': '/assets/og/ecosystem-partners.png',
  '/builders/resources': '/assets/og/builders-resources.png',
  '/community/poaps': '/assets/og/community-poaps.png',
  '/participants': '/assets/og/participants.png',
  '/validators/participants': '/assets/og/validators-participants.png',
  '/validators/waitlist/join': '/assets/og/validators-waitlist.png',
  '/validators/wall-of-shame': '/assets/og/validators-wall-of-shame.png',
  '/terms-of-use': '/assets/og/terms-of-use.png',
  '/privacy-policy': '/assets/og/privacy-policy.png',
};

describe('route metadata', () => {
  it('uses final 1200x630 OG images instead of raw backdrops', () => {
    for (const image of Object.values(OG_IMAGES)) {
      expect(image.src).toMatch('/assets/og/');
      expect(image.src).not.toContain('/assets/og/backdrops/');
      expect(image.width).toBe('1200');
      expect(image.height).toBe('630');
    }
  });

  it('points every configured image to an existing public asset', () => {
    for (const image of Object.values(OG_IMAGES)) {
      const { pathname } = new URL(image.src);
      const assetPath = path.join(process.cwd(), 'public', pathname.replace(/^\//, ''));

      expect(existsSync(assetPath)).toBe(true);
    }
  });

  it('resolves route-specific images for key portal routes', () => {
    for (const [route, imagePath] of Object.entries(expectedRouteImages)) {
      expect(resolveRouteMeta(route).image).toContain(imagePath);
    }
  });

  it('uses non-hash canonical URLs for every public OG route', () => {
    for (const route of ['/', ...STATIC_OG_ROUTES]) {
      const meta = resolveRouteMeta(route);
      const expectedUrl = `${SITE_URL}${route === '/' ? '/' : route}`;

      expect(meta.url).toBe(expectedUrl);
      expect(meta.url).not.toContain('#');
    }

    expect(resolveRouteMeta('#/hackathon?ref=abc').url)
      .toBe('https://portal.genlayer.foundation/hackathon');
    expect(resolveRouteMeta('https://portal.genlayer.foundation/#/builders/resources').url)
      .toBe('https://portal.genlayer.foundation/builders/resources');
  });

  it('only generates static OG pages for canonical route paths', () => {
    expect(STATIC_OG_ROUTES).toEqual([
      '/how-it-works',
      '/referral-program',
      '/hackathon',
      '/hackathon-winners',
      '/genesis',
      '/genesis/manifesto',
      '/genesis/whitepaper',
      '/genesis/compass',
      '/gen-tv',
      '/gen-news',
      '/ecosystem-partners',
      '/builders/resources',
      '/community/poaps',
      '/participants',
      '/validators/participants',
      '/validators/waitlist/join',
      '/validators/wall-of-shame',
      '/terms-of-use',
      '/privacy-policy',
    ]);
  });

  it('canonicalizes legacy Foundations aliases to Genesis URLs', () => {
    expect(resolveRouteMeta('/foundations').url).toBe('https://portal.genlayer.foundation/genesis');
    expect(resolveRouteMeta('/foundations/manifesto').url).toBe('https://portal.genlayer.foundation/genesis/manifesto');
    expect(resolveRouteMeta('/foundations/whitepaper').url).toBe('https://portal.genlayer.foundation/genesis/whitepaper');
    expect(resolveRouteMeta('/foundations/compass').url).toBe('https://portal.genlayer.foundation/genesis/compass');
    expect(resolveRouteMeta('/manifesto').url).toBe('https://portal.genlayer.foundation/genesis/manifesto');

    const meta = resolveRouteMeta('/foundations/manifesto');
    expect(meta.title).toBe('GenLayer Manifesto');
    expect(meta.image).toContain('/assets/og/genesis-manifesto.png');
  });

  it('uses the generic builder project image for project detail slugs', () => {
    const meta = resolveRouteMeta('/builders/projects/test-project');

    expect(meta.title).toBe('GenLayer Builder Project');
    expect(meta.image).toContain('/assets/og/builder-project.png');
    expect(meta.url).toBe('https://portal.genlayer.foundation/builders/projects/test-project');
  });

  it('keeps supported dynamic public routes hashless and protected lookalikes noindex', () => {
    expect(resolveRouteMeta('/builders/startup-requests/42').url)
      .toBe('https://portal.genlayer.foundation/builders/startup-requests/42');
    expect(resolveRouteMeta('/community/poaps/community-drop').url)
      .toBe('https://portal.genlayer.foundation/community/poaps/community-drop');
    expect(resolveRouteMeta('/badge/7').url)
      .toBe('https://portal.genlayer.foundation/badge/7');

    expect(resolveRouteMeta('/builders/projects/test-project/edit').robots).toBe('noindex,nofollow');
    expect(resolveRouteMeta('/community/poaps/recover').robots).toBe('noindex,nofollow');
    expect(resolveRouteMeta('/stewards/submissions').robots).toBe('noindex,nofollow');
  });

  it('keeps noindex recovery routes blocked in robots.txt', () => {
    const robots = readFileSync(path.join(process.cwd(), 'public', 'robots.txt'), 'utf8');

    expect(robots).toContain('Allow: /community/poaps/');
    expect(robots).toContain('Disallow: /community/poaps/recover');
  });
});
