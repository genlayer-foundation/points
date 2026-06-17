import { describe, expect, it } from 'vitest';
import { getXPostUrl } from '../lib/xPost.js';

describe('xPost utilities', () => {
  it('detects X and Twitter status URLs', () => {
    expect(getXPostUrl('https://x.com/example/status/1234567890')).toEqual({
      id: '1234567890',
      username: 'example',
      url: 'https://twitter.com/example/status/1234567890',
    });
    expect(getXPostUrl('https://twitter.com/example/statuses/1234567890')).toEqual({
      id: '1234567890',
      username: 'example',
      url: 'https://twitter.com/example/status/1234567890',
    });
  });

  it('ignores X profile and broadcast URLs', () => {
    expect(getXPostUrl('https://x.com/example')).toBeNull();
    expect(getXPostUrl('https://x.com/i/broadcasts/1abc')).toBeNull();
    expect(getXPostUrl('https://x.com/genlayer/articles/123')).toBeNull();
  });
});
