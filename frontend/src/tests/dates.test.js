import { describe, it, expect } from 'vitest';
import { format } from '../lib/dates.js';

describe('dates.js format (date-fns replacement)', () => {
  const d = new Date(2026, 6, 5, 9, 7); // Jul 5 2026 09:07

  it('formats every pattern the app uses', () => {
    expect(format(d)).toBe('Jul 5, 2026');
    expect(format(d, 'MMM d, yyyy')).toBe('Jul 5, 2026');
    expect(format(d, 'MMMM d, yyyy')).toBe('July 5, 2026');
    expect(format(d, 'MMM yyyy')).toBe('Jul 2026');
    expect(format(d, 'MMMM yyyy')).toBe('July 2026');
    expect(format(d, 'yyyy-MM')).toBe('2026-07');
    expect(format(d, 'MMM d, yyyy HH:mm')).toBe('Jul 5, 2026 09:07');
    expect(format(d, 'EEE, MMM d · HH:mm')).toBe('Sun, Jul 5 · 09:07');
  });

  it('accepts date strings', () => {
    expect(format('2026-07-05T09:07:00')).toBe('Jul 5, 2026');
  });

  it('throws RangeError on invalid dates and unknown patterns (date-fns parity)', () => {
    expect(() => format('garbage')).toThrow(RangeError);
    expect(() => format(d, 'qqq')).toThrow(RangeError);
  });
});
