import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  computeNormalizedUrl,
  normalizeLocation,
} from '../lib/normalizePath.js';

describe('computeNormalizedUrl', () => {
  it('rewrites a plain path route into its hash equivalent', () => {
    expect(computeNormalizedUrl({ pathname: '/testnets', hash: '', search: '' }))
      .toBe('/#/testnets');
    expect(computeNormalizedUrl({ pathname: '/metrics', hash: '', search: '' }))
      .toBe('/#/metrics');
  });

  it('preserves the query string when rewriting', () => {
    expect(computeNormalizedUrl({ pathname: '/metrics', hash: '', search: '?range=30d' }))
      .toBe('/#/metrics?range=30d');
  });

  it('rewrites nested path routes', () => {
    expect(computeNormalizedUrl({ pathname: '/builders/leaderboard', hash: '', search: '' }))
      .toBe('/#/builders/leaderboard');
  });

  it('removes trailing slashes when rewriting', () => {
    expect(computeNormalizedUrl({ pathname: '/referral-program/', hash: '', search: '' }))
      .toBe('/#/referral-program');
    expect(computeNormalizedUrl({ pathname: '/validators/waitlist/join/', hash: '', search: '?ref=abc' }))
      .toBe('/#/validators/waitlist/join?ref=abc');
  });

  it('returns null when a hash is already present', () => {
    expect(computeNormalizedUrl({ pathname: '/testnets', hash: '#/testnets', search: '' }))
      .toBeNull();
    expect(computeNormalizedUrl({ pathname: '/', hash: '#/metrics', search: '' }))
      .toBeNull();
  });

  it('returns null for the root path', () => {
    expect(computeNormalizedUrl({ pathname: '/', hash: '', search: '' })).toBeNull();
    expect(computeNormalizedUrl({ pathname: '', hash: '', search: '' })).toBeNull();
  });

  it('leaves reserved or server-handled prefixes untouched', () => {
    expect(computeNormalizedUrl({ pathname: '/api/users', hash: '', search: '' })).toBeNull();
    expect(computeNormalizedUrl({ pathname: '/oauth/callback', hash: '', search: '?code=x' })).toBeNull();
    expect(computeNormalizedUrl({ pathname: '/assets/app.js', hash: '', search: '' })).toBeNull();
  });

  it('leaves static file requests untouched', () => {
    expect(computeNormalizedUrl({ pathname: '/favicon.ico', hash: '', search: '' })).toBeNull();
    expect(computeNormalizedUrl({ pathname: '/robots.txt', hash: '', search: '' })).toBeNull();
    expect(computeNormalizedUrl({ pathname: '/sitemap.xml', hash: '', search: '' })).toBeNull();
  });

  it('tolerates missing hash and search fields', () => {
    expect(computeNormalizedUrl({ pathname: '/leaderboard' })).toBe('/#/leaderboard');
  });
});

describe('normalizeLocation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('rewrites the URL via history.replaceState when normalization is needed', () => {
    const replaceState = vi.fn();
    const win = {
      location: { pathname: '/testnets', hash: '', search: '' },
      history: { replaceState },
    };

    const changed = normalizeLocation(win);

    expect(changed).toBe(true);
    expect(replaceState).toHaveBeenCalledWith({}, '', '/#/testnets');
  });

  it('does nothing when a hash route is already present', () => {
    const replaceState = vi.fn();
    const win = {
      location: { pathname: '/', hash: '#/testnets', search: '' },
      history: { replaceState },
    };

    const changed = normalizeLocation(win);

    expect(changed).toBe(false);
    expect(replaceState).not.toHaveBeenCalled();
  });

  it('returns false safely when window or history is unavailable', () => {
    expect(normalizeLocation(undefined)).toBe(false);
    expect(normalizeLocation({})).toBe(false);
    expect(normalizeLocation({ location: { pathname: '/testnets' } })).toBe(false);
  });
});
