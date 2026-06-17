import { describe, expect, it } from 'vitest';

import { buildRoutes, matchRoute, linkNavTarget } from '../lib/router.js';

// Mirror of the real route table's hard cases (params, literal-vs-:param
// precedence, catch-all). Components are stand-in markers.
const routes = buildRoutes({
  '/': 'home',
  '/community/poaps/recover': 'recover',
  '/community/poaps/:slug': 'poapDetail',
  '/claim/poap/:token': 'claim',
  '/participant/:address': 'profile',
  '/builders/projects/:slug/edit': 'projectEdit',
  '/builders/projects/:slug': 'projectDetail',
  '/genesis/compass': 'compass',
  '/genesis': 'genesis',
  '*': 'notFound',
});

const hit = (path) => {
  const m = matchRoute(routes, path);
  return m && { route: m.route.path, params: m.params };
};

describe('history router matching', () => {
  it('extracts named params', () => {
    expect(hit('/community/poaps/genesis-poap'))
      .toEqual({ route: '/community/poaps/:slug', params: { slug: 'genesis-poap' } });
    expect(hit('/claim/poap/abc123'))
      .toEqual({ route: '/claim/poap/:token', params: { token: 'abc123' } });
    expect(hit('/participant/0xAbC'))
      .toEqual({ route: '/participant/:address', params: { address: '0xAbC' } });
  });

  it('decodes percent-encoded params', () => {
    expect(hit('/participant/0x%41%42').params).toEqual({ address: '0xAB' });
  });

  it('respects route order (literal and longer routes before :param)', () => {
    expect(hit('/community/poaps/recover').route).toBe('/community/poaps/recover');
    expect(hit('/builders/projects/foo/edit').route).toBe('/builders/projects/:slug/edit');
    expect(hit('/builders/projects/foo').route).toBe('/builders/projects/:slug');
    expect(hit('/genesis/compass').route).toBe('/genesis/compass');
    expect(hit('/genesis').route).toBe('/genesis');
  });

  it('falls through to the catch-all for unknown paths', () => {
    expect(hit('/does/not/exist').route).toBe('*');
  });

  it('matches the root and has no params on static routes', () => {
    expect(hit('/')).toEqual({ route: '/', params: {} });
    expect(hit('/genesis').params).toEqual({});
  });
});

describe('link navigation targets', () => {
  const base = 'https://portal.genlayer.foundation/hackathon';

  it('navigates same-origin path links in-app', () => {
    expect(linkNavTarget('/submit-contribution', base)).toBe('/submit-contribution');
    expect(linkNavTarget('/all-contributions?category=builder', base))
      .toBe('/all-contributions?category=builder');
    expect(linkNavTarget('/metrics?range=30d#top', base)).toBe('/metrics?range=30d#top');
  });

  it('resolves legacy /#/route links to the clean path (regression)', () => {
    // Without this, the router reads pathname '/' and lands on home.
    expect(linkNavTarget('/#/submit-contribution', base)).toBe('/submit-contribution');
    expect(linkNavTarget('/#/mission/7?x=1', base)).toBe('/mission/7?x=1');
    expect(linkNavTarget('https://portal.genlayer.foundation/#/hackathon', base))
      .toBe('/hackathon');
  });

  it('leaves in-page, external, reserved, and file links to the browser', () => {
    expect(linkNavTarget('#section', base)).toBeNull();
    expect(linkNavTarget('https://x.com/GenLayer', base)).toBeNull();
    expect(linkNavTarget('/api/v1/export', base)).toBeNull();
    expect(linkNavTarget('/assets/whitepaper.pdf', base)).toBeNull();
    expect(linkNavTarget('', base)).toBeNull();
  });
});
