/**
 * Shared guards for rendering and validating user-provided URLs.
 *
 * Evidence URLs (and other user-controlled links) must only ever be rendered
 * as http(s) hrefs — anything else (javascript:, data:, file:, etc.) is
 * dropped so a malicious submission can't turn a "View URL" link into a
 * script gadget for whoever reviews or browses it.
 */

/**
 * @param {string | undefined | null} value
 * @returns {boolean} true when the value parses as an absolute http(s) URL
 */
export function isSafeHttpUrl(value) {
  if (!value || typeof value !== 'string' || /\s/.test(value.trim())) return false;
  try {
    const url = new URL(value.trim());
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
}
