import { getLocale } from './paraglide/runtime.js';

/**
 * Compact relative time for notification timestamps ("now", "5m", "3h", "2d",
 * then a short date), localized to the active portal locale via Intl.
 * Pass `verbose: true` for "5 minutes ago" style.
 */
export function relativeTime(value, { verbose = false } = {}) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const locale = getLocale();
  const seconds = Math.max(1, Math.floor((Date.now() - date.getTime()) / 1000));

  if (seconds < 60) {
    return new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(0, 'second');
  }

  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const [amount, unit] = /** @type {[number, 'minute' | 'hour' | 'day']} */ (
    minutes < 60 ? [minutes, 'minute'] : hours < 24 ? [hours, 'hour'] : [days, 'day']
  );

  if (days >= 7) {
    return date.toLocaleDateString(locale, { month: 'short', day: 'numeric' });
  }

  if (verbose) {
    return new Intl.RelativeTimeFormat(locale, { numeric: 'always' }).format(-amount, unit);
  }

  // Narrow unit display gives the compact "5m" / "3h" / "2d" per locale.
  return new Intl.NumberFormat(locale, {
    style: 'unit',
    unit,
    unitDisplay: 'narrow',
  }).format(amount);
}
