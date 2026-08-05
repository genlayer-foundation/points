import axios from 'axios';
import { API_BASE_URL } from './config.js';

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

let csrfCookieName = 'csrftoken';
let csrfTokenRequest = null;
// In production the API lives on a different host than the SPA, so the CSRF
// cookie is never readable from document.cookie and every unsafe request would
// otherwise refetch /api/csrf/. Held in memory only, never localStorage or any
// persistent browser storage, and cleared by clearCsrfToken() on every path
// that rotates the server-side token.
let cachedCsrfToken = null;

function getCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) {
    return '';
  }

  const cookie = document.cookie
    .split('; ')
    .find((row) => row.startsWith(`${encodeURIComponent(name)}=`));

  if (!cookie) {
    return '';
  }

  return decodeURIComponent(cookie.split('=').slice(1).join('='));
}

function getCookieToken() {
  return getCookie(csrfCookieName) || getCookie('csrftoken');
}

function isUnsafeMethod(method = 'get') {
  return UNSAFE_METHODS.has(method.toLowerCase());
}

async function getCsrfToken() {
  // Same-origin dev keeps working off the cookie, which Django rotates for us.
  const existingToken = getCookieToken();
  if (existingToken) {
    return existingToken;
  }

  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }

  if (!csrfTokenRequest) {
    csrfTokenRequest = axios
      .get(`${API_BASE_URL}/api/csrf/`, { withCredentials: true })
      .then((response) => {
        csrfCookieName = response.data?.csrfCookieName || csrfCookieName;
        cachedCsrfToken = response.data?.csrfToken || getCookieToken() || null;
        return cachedCsrfToken;
      })
      .finally(() => {
        csrfTokenRequest = null;
      });
  }

  return csrfTokenRequest;
}

/**
 * Drop the cached token. Call from every path that rotates the server-side
 * token: login, logout, wallet switch, and email confirmation, plus a genuine
 * CSRF rejection. Session refresh does not rotate it.
 */
export function clearCsrfToken() {
  cachedCsrfToken = null;
  csrfTokenRequest = null;
}

/**
 * Distinguish a real CSRF rejection from an authorization 403. DRF raises
 * PermissionDenied('CSRF Failed: ...') from enforce_csrf, so the detail string
 * is the only reliable signal; both cases are 403.
 */
export function isCsrfFailure(error) {
  if (error?.response?.status !== 403) return false;
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' && detail.startsWith('CSRF Failed');
}

/**
 * Retry one explicitly idempotent request after a genuine CSRF rejection.
 *
 * The shared Axios interceptor cannot safely replay every mutation because
 * many endpoints are not idempotent. Callers opt in here only when the server
 * guarantees that repeating the operation is safe (for example, role grants
 * implemented with get_or_create).
 *
 * @template T
 * @param {() => Promise<T>} request
 * @returns {Promise<T>}
 */
export async function retryOnceAfterCsrfFailure(request) {
  try {
    return await request();
  } catch (error) {
    if (!isCsrfFailure(error)) throw error;
    clearCsrfToken();
    return request();
  }
}

export async function attachCsrfToken(config) {
  if (!isUnsafeMethod(config.method)) {
    return config;
  }

  const token = await getCsrfToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers['X-CSRFToken'] = token;
  }

  return config;
}
