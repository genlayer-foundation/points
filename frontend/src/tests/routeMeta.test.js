import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import path from 'node:path';

import { OG_IMAGES, resolveRouteMeta } from '../lib/routeMeta.js';

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
    expect(resolveRouteMeta('/participants').image).toContain('/assets/og/participants.png');
    expect(resolveRouteMeta('/ecosystem-partners').image).toContain('/assets/og/ecosystem-partners.png');
    expect(resolveRouteMeta('/builders/resources').image).toContain('/assets/og/builders-resources.png');
    expect(resolveRouteMeta('/validators/waitlist/join').image).toContain('/assets/og/validators-waitlist.png');
  });

  it('keeps alias URLs while reusing Genesis route metadata', () => {
    const meta = resolveRouteMeta('/foundations/manifesto');

    expect(meta.title).toBe('GenLayer Manifesto');
    expect(meta.image).toContain('/assets/og/genesis-manifesto.png');
    expect(meta.url).toBe('https://portal.genlayer.foundation/foundations/manifesto');
  });

  it('uses the generic builder project image for project detail slugs', () => {
    const meta = resolveRouteMeta('/builders/projects/test-project');

    expect(meta.title).toBe('GenLayer Builder Project');
    expect(meta.image).toContain('/assets/og/builder-project.png');
    expect(meta.url).toBe('https://portal.genlayer.foundation/builders/projects/test-project');
  });
});
