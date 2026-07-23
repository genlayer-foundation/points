import { describe, expect, it } from 'vitest';

import {
  NOTIFICATION_BODY_PREVIEW_LENGTH,
  notificationBodyPreview
} from '../lib/notificationUtils.js';

describe('notificationBodyPreview', () => {
  it('preserves sanitized markdown formatting and links', () => {
    const html = notificationBodyPreview(
      'A **bold** update with [details](/notifications).\n\nRead it now.'
    );

    expect(html).toContain('<strong>bold</strong>');
    expect(html).toContain('<a href="/notifications">details</a>');

    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    expect(wrapper.textContent).toBe('A bold update with details. Read it now.');
  });

  it('trims long bodies to the dropdown limit with an ellipsis', () => {
    const wrapper = document.createElement('div');
    wrapper.innerHTML = notificationBodyPreview('Update '.repeat(40));
    const preview = wrapper.textContent || '';

    expect(preview.length).toBeLessThanOrEqual(NOTIFICATION_BODY_PREVIEW_LENGTH);
    expect(preview.length).toBeGreaterThan(1);
    expect(preview.endsWith('…')).toBe(true);
  });

  it('supports short limits and empty values', () => {
    expect(notificationBodyPreview('Hello', 1)).toBe('…');
    expect(notificationBodyPreview('Hello', 0)).toBe('');
    expect(notificationBodyPreview(null)).toBe('');
  });
});
