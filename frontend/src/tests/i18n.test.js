import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { setLocale } from '../lib/paraglide/runtime.js';
import { m } from '../lib/paraglide/messages.js';
import { formatCompactNumber, ogLocale, SUPPORTED_LOCALES, getLocale } from '../lib/i18n.js';
import { relativeTime } from '../lib/relativeTime.js';
import { setRouteMeta } from '../lib/meta.js';

// reload: false — jsdom cannot navigate; production setLocale reloads by design.
const switchTo = (locale) => setLocale(locale, { reload: false });

describe('i18n foundation', () => {
  beforeEach(() => switchTo('en'));
  afterEach(() => switchTo('en'));

  it('defaults to English and resolves messages', () => {
    expect(getLocale()).toBe('en');
    expect(m.nav_overview()).toBe('Overview');
  });

  it('switches locale, persists it, and resolves translated messages', () => {
    switchTo('es');
    expect(m.nav_overview()).toBe('Resumen');
    expect(localStorage.getItem('PARAGLIDE_LOCALE')).toBe('es');
    switchTo('zh-Hans');
    expect(m.nav_leaderboard()).toBe('排行榜');
  });

  it('has a message catalog entry for every supported locale', () => {
    for (const { code } of SUPPORTED_LOCALES) {
      switchTo(code);
      expect(m.language_label().length).toBeGreaterThan(0);
    }
  });

  it('formats compact numbers per locale and rejects non-numbers', () => {
    expect(formatCompactNumber(1234)).toBe('1.2K');
    expect(formatCompactNumber(2500000)).toBe('2.5M');
    expect(formatCompactNumber(null)).toBeNull();
    expect(formatCompactNumber('not-a-number')).toBeNull();
  });

  it('formats relative time compactly and verbosely', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000);
    expect(relativeTime(fiveMinAgo)).toBe('5m');
    expect(relativeTime(fiveMinAgo, { verbose: true })).toBe('5 minutes ago');
    expect(relativeTime(new Date(Date.now() - 10 * 1000))).toBe('now');
    expect(relativeTime('garbage')).toBe('');
    switchTo('es');
    expect(relativeTime(fiveMinAgo, { verbose: true })).toBe('hace 5 minutos');
  });

  it('localizes route metadata at runtime (og:locale + overlay)', () => {
    switchTo('es');
    setRouteMeta('/');
    expect(document.querySelector('meta[property="og:locale"]').getAttribute('content')).toBe('es_ES');
    expect(document.querySelector('meta[name="description"]').getAttribute('content')).toBe(
      m.meta_home_description()
    );
    switchTo('en');
    setRouteMeta('/');
    expect(document.querySelector('meta[property="og:locale"]').getAttribute('content')).toBe('en_US');
  });
});
