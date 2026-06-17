const X_POST_HOSTS = new Set([
  'x.com',
  'twitter.com',
  'mobile.twitter.com',
]);

/** @param {string} hostname */
function normalizeHost(hostname) {
  return hostname.toLowerCase().replace(/^www\./, '');
}

/**
 * @param {unknown} value
 * @returns {{ id: string, username: string, url: string } | null}
 */
export function getXPostUrl(value) {
  if (!value || typeof value !== 'string') return null;

  try {
    const parsed = new URL(value.trim());
    const host = normalizeHost(parsed.hostname);
    if (!X_POST_HOSTS.has(host)) return null;

    const parts = parsed.pathname.split('/').filter(Boolean);
    let username = parts[0];
    let postId = null;

    if (parts[0] === 'i' && parts[1] === 'web' && parts[2] === 'status') {
      username = 'i';
      postId = parts[3];
    } else if (parts[1] === 'status' || parts[1] === 'statuses') {
      postId = parts[2];
    }

    if (!postId || !/^\d+$/.test(postId)) return null;

    return {
      id: postId,
      username,
      url: username === 'i'
        ? `https://twitter.com/i/web/status/${postId}`
        : `https://twitter.com/${username}/status/${postId}`,
    };
  } catch {
    return null;
  }
}
