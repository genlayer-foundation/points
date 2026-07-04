// ponytail: replaces date-fns `format` with Intl — only the patterns this app
// actually uses. Add a pattern here if a new call site needs one.
const PATTERNS = {
  'MMM d, yyyy': { month: 'short', day: 'numeric', year: 'numeric' },
  'MMMM d, yyyy': { month: 'long', day: 'numeric', year: 'numeric' },
  'MMM yyyy': { month: 'short', year: 'numeric' },
  'MMMM yyyy': { month: 'long', year: 'numeric' },
};

function hhmm(d) {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/**
 * Drop-in replacement for date-fns `format(date, pattern)` for the patterns
 * listed above. Like date-fns, throws RangeError on invalid dates (call sites
 * rely on this for their try/catch fallbacks).
 */
export function format(date, pattern = 'MMM d, yyyy') {
  const d = date instanceof Date ? date : new Date(date);
  if (Number.isNaN(d.getTime())) throw new RangeError('Invalid time value');
  if (pattern === 'yyyy-MM') return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  if (pattern === 'MMM d, yyyy HH:mm') return `${format(d)} ${hhmm(d)}`;
  if (pattern === 'EEE, MMM d · HH:mm') {
    return `${d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · ${hhmm(d)}`;
  }
  const options = PATTERNS[pattern];
  if (!options) throw new RangeError(`Unsupported date pattern: ${pattern}`);
  return d.toLocaleDateString('en-US', options);
}
