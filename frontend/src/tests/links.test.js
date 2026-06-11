import { describe, expect, it } from 'vitest';

import { resolvePortalLink } from '../lib/links.js';

const ORIGIN = 'https://portal.genlayer.foundation';

describe('resolvePortalLink', () => {
  it('rewrites absolute same-origin hash URLs into in-app hash routes', () => {
    expect(resolvePortalLink('https://portal.genlayer.foundation/#/mission/7', ORIGIN))
      .toEqual({ href: '#/mission/7', external: false });
    expect(resolvePortalLink('https://portal.genlayer.foundation/#/hackathon', ORIGIN))
      .toEqual({ href: '#/hackathon', external: false });
  });

  it('rewrites absolute same-origin path URLs into hash routes', () => {
    expect(resolvePortalLink('https://portal.genlayer.foundation/referral-program', ORIGIN))
      .toEqual({ href: '#/referral-program', external: false });
    expect(resolvePortalLink('https://portal.genlayer.foundation/metrics?range=30d', ORIGIN))
      .toEqual({ href: '#/metrics?range=30d', external: false });
  });

  it('maps a bare same-origin root URL to the home route', () => {
    expect(resolvePortalLink('https://portal.genlayer.foundation/', ORIGIN))
      .toEqual({ href: '#/', external: false });
  });

  it('keeps cross-origin URLs external', () => {
    expect(resolvePortalLink('https://argue.fun', ORIGIN))
      .toEqual({ href: 'https://argue.fun', external: true });
    expect(resolvePortalLink('https://x.com/GenLayer/status/1', ORIGIN))
      .toEqual({ href: 'https://x.com/GenLayer/status/1', external: true });
  });

  it('converts relative paths into hash routes', () => {
    expect(resolvePortalLink('/badge/42', ORIGIN))
      .toEqual({ href: '#/badge/42', external: false });
  });

  it('passes through hash routes unchanged', () => {
    expect(resolvePortalLink('#/gen-tv', ORIGIN))
      .toEqual({ href: '#/gen-tv', external: false });
  });

  it('falls back to an inert anchor when there is no link', () => {
    expect(resolvePortalLink(null, ORIGIN)).toEqual({ href: '#', external: false });
    expect(resolvePortalLink('', ORIGIN)).toEqual({ href: '#', external: false });
    expect(resolvePortalLink('#', ORIGIN)).toEqual({ href: '#', external: false });
  });
});
