import { describe, expect, it } from 'vitest';

import { parseMarkdown } from '../lib/markdownLoader.js';

describe('parseMarkdown', () => {
  it('preserves normal markdown links and formatting', () => {
    const html = parseMarkdown('Read **the docs** at [GenLayer](https://genlayer.com).');

    expect(html).toContain('<strong>the docs</strong>');
    expect(html).toContain('<a href="https://genlayer.com" target="_blank" rel="noopener noreferrer">GenLayer</a>');
  });

  it('rewrites same-origin absolute links to in-app hash routes', () => {
    const html = parseMarkdown(`See [the mission](${window.location.origin}/#/mission/7).`);

    expect(html).toContain('<a href="#/mission/7">the mission</a>');
    expect(html).not.toContain('target="_blank"');
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

  it('strips additional dangerous tags, handlers, and data URLs', () => {
    const html = parseMarkdown(`
<img src="data:text/html,<script>alert('xss')</script>" onload="alert('xss')">
<p onmouseover="alert('xss')">hover</p>
<object data="https://example.com/payload"></object>
<embed src="https://example.com/payload">
<form action="https://example.com"><input name="token"></form>
<svg onload="alert('xss')"><circle></circle></svg>
`);

    expect(html).not.toContain('data:text/html');
    expect(html).not.toContain('onload');
    expect(html).not.toContain('onmouseover');
    expect(html).not.toContain('<object');
    expect(html).not.toContain('<embed');
    expect(html).not.toContain('<form');
    expect(html).not.toContain('<input');
    expect(html).not.toContain('<svg');
  });
});
