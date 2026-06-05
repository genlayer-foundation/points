import { describe, expect, it } from 'vitest';

import { parseMarkdown } from '../lib/markdownLoader.js';

describe('parseMarkdown', () => {
  it('preserves normal markdown links and formatting', () => {
    const html = parseMarkdown('Read **the docs** at [GenLayer](https://genlayer.com).');

    expect(html).toContain('<strong>the docs</strong>');
    expect(html).toContain('<a href="https://genlayer.com">GenLayer</a>');
  });

  it('strips scripts, event handlers, inline styles, and unsafe URLs', () => {
    const html = parseMarkdown(`
<script>alert('xss')</script>
<img src="x" onerror="alert('xss')" style="width: 100px">
<a href="javascript:alert('xss')" onclick="alert('xss')">bad link</a>
<iframe src="https://example.com"></iframe>
`);

    expect(html).not.toContain('<script');
    expect(html).not.toContain('onerror');
    expect(html).not.toContain('onclick');
    expect(html).not.toContain('style=');
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('<iframe');
  });
});
