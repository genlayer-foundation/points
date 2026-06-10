/**
 * Compact relative time for notification timestamps ("now", "5m", "3h", "2d",
 * then a short date). Pass `verbose: true` for "5m ago" style.
 */
export function relativeTime(value, { verbose = false } = {}) {
  const date = new Date(value);
  const seconds = Math.max(1, Math.floor((Date.now() - date.getTime()) / 1000));
  const suffix = verbose ? ' ago' : '';

  if (seconds < 60) return 'now';

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m${suffix}`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h${suffix}`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d${suffix}`;

  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
