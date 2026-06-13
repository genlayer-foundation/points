import axios from 'axios';
import { API_BASE_URL } from './config.js';

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

let csrfCookieName = 'csrftoken';
let csrfTokenRequest = null;

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
  const existingToken = getCookieToken();
  if (existingToken) {
    return existingToken;
  }

  if (!csrfTokenRequest) {
    csrfTokenRequest = axios
      .get(`${API_BASE_URL}/api/csrf/`, { withCredentials: true })
      .then((response) => {
        csrfCookieName = response.data?.csrfCookieName || csrfCookieName;
        return response.data?.csrfToken || getCookieToken();
      })
      .finally(() => {
        csrfTokenRequest = null;
      });
  }

  return csrfTokenRequest;
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
