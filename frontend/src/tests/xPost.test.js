import { describe, expect, it } from 'vitest';
import { getSingleXPostEvidence, getXPostUrl, isXPostUrl } from '../lib/xPost.js';

describe('xPost utilities', () => {
  it('detects X and Twitter status URLs', () => {
    expect(getXPostUrl('https://x.com/example/status/1234567890')).toEqual({
      id: '1234567890',
      username: 'example',
      url: 'https://twitter.com/example/status/1234567890',
    });
    expect(isXPostUrl('https://twitter.com/example/statuses/1234567890')).toBe(true);
  });

  it('ignores X profile and broadcast URLs', () => {
    expect(getXPostUrl('https://x.com/example')).toBeNull();
    expect(getXPostUrl('https://x.com/i/broadcasts/1abc')).toBeNull();
  });

  it('returns evidence only when there is exactly one evidence URL and it is an X post', () => {
    const evidence = { description: 'Launch post', url: 'https://x.com/genlayer/status/123' };

    expect(getSingleXPostEvidence([evidence])).toMatchObject({
      id: '123',
      evidence,
    });
    expect(getSingleXPostEvidence([evidence, { url: 'https://example.com' }])).toBeNull();
    expect(getSingleXPostEvidence([{ description: 'No URL' }, evidence])).toMatchObject({
      id: '123',
      evidence,
    });
    expect(getSingleXPostEvidence(null)).toBeNull();
  });
});
