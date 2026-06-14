import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import path from 'node:path';

import { OG_IMAGES, STATIC_OG_ROUTES, resolveRouteMeta } from '../lib/routeMeta.js';

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
});
