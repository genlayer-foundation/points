import { beforeEach, describe, expect, it } from 'vitest';

import { clearPoapClaimRedirect } from '../lib/poapRedirect.js';

describe('clearPoapClaimRedirect', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('removes the matching raw POAP claim redirect', () => {
    sessionStorage.setItem('redirectAfterLogin', '/claim/poap/raw-token');

    clearPoapClaimRedirect('raw-token');

    expect(sessionStorage.getItem('redirectAfterLogin')).toBeNull();
  });

  it('removes the matching encoded POAP claim redirect', () => {
    sessionStorage.setItem('redirectAfterLogin', '/claim/poap/token%20with%20spaces');

    clearPoapClaimRedirect('token with spaces');

    expect(sessionStorage.getItem('redirectAfterLogin')).toBeNull();
  });

  it('leaves unrelated redirects intact', () => {
    sessionStorage.setItem('redirectAfterLogin', '/submit-contribution');

    clearPoapClaimRedirect('raw-token');

    expect(sessionStorage.getItem('redirectAfterLogin')).toBe('/submit-contribution');
  });
});
