import { get, writable } from 'svelte/store';
import { authState } from './auth.js';
import { userStore } from './userStore.js';
import { hasEarnedRole, hasStartedJourney, roleFunnelState } from './roleState.js';

const ANALYTICS_SCRIPT_ID = 'google-analytics-gtag';
const ANALYTICS_CONSENT_KEY = 'ga_analytics_consent';
const TIMER_PREFIX = 'ga_funnel_timer:';
const LIFECYCLE_TIME_PREFIX = 'ga_lifecycle_time:';
const LIFECYCLE_FLAG_PREFIX = 'ga_lifecycle_flag:';
const CONNECT_WALLET_INTENT_KEY = 'ga_connect_wallet_intent';
const MAX_STRING_LENGTH = 100;
const MAX_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

const ROUTE_PARAM_KEYS = new Set([
  'route',
  'source_route',
  'target_route',
  'guarded_route',
  'redirect_target',
  'page_path',
]);

const SAFE_ID_KEYS = new Set(['cta_id', 'step_id']);
const FORBIDDEN_KEYS = new Set([
  'id',
  'slug',
  'token',
  'user',
  'address',
  'wallet_address',
  'email',
  'username',
  'handle',
  'discord_handle',
  'x_handle',
  'github_handle',
  'post_url',
  'tweet_id',
  'tweet_text',
  'verification_code',
  'message',
  'siwe_message',
  'signature',
  'nonce',
  'raw_error',
]);

const ADDRESS_RE = /\b0x[a-fA-F0-9]{40}\b/;
const EMAIL_RE = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i;
const URL_RE = /^https?:\/\//i;
const URL_VALUE_RE = /https?:\/\/\S+/i;

let initialized = false;
let scriptRequested = false;

function trackingId() {
  return import.meta.env.VITE_GOOGLE_ANALYTICS_ID || '';
}

export function isAnalyticsConfigured() {
  return Boolean(trackingId());
}

function canUseBrowser() {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
}

function isDoNotTrackEnabled() {
  if (!canUseBrowser()) return false;
  return (
    window.navigator?.doNotTrack === '1' ||
    window.navigator?.doNotTrack === 'yes' ||
    window.navigator?.globalPrivacyControl === true
  );
}

function storedAnalyticsConsent() {
  try {
    if (!canUseBrowser()) return 'unknown';
    if (isDoNotTrackEnabled()) return 'denied';
    const value = localStorage.getItem(ANALYTICS_CONSENT_KEY);
    return value === 'granted' || value === 'denied' ? value : 'unknown';
  } catch {
    return 'unknown';
  }
}

export const analyticsConsent = writable(storedAnalyticsConsent());

function hasAnalyticsConsent() {
  return get(analyticsConsent) === 'granted' && !isDoNotTrackEnabled();
}

function safeNow() {
  return Date.now ? Date.now() : new Date().getTime();
}

function safeStorageKey(key) {
  return String(key || '').replace(/[^a-zA-Z0-9:_-]/g, '_').slice(0, 80);
}

function normalizePath(path) {
  if (!path || typeof path !== 'string') return '/';
  let value = path;
  try {
    if (URL_RE.test(value)) {
      value = new URL(value).pathname;
    }
  } catch {
    value = '/';
  }
  value = value.split('?')[0].split('#')[0] || '/';
  value = value.replace(/\/+$/, '') || '/';
  return value.startsWith('/') ? value : `/${value}`;
}

export function templateRoute(path) {
  const route = normalizePath(path);
  const replacements = [
    [/^\/participant\/[^/]+$/, '/participant/:address'],
    [/^\/community\/poaps\/recover$/, '/community/poaps/recover'],
    [/^\/community\/poaps\/[^/]+$/, '/community/poaps/:slug'],
    [/^\/claim\/poap\/[^/]+$/, '/claim/poap/:token'],
    [/^\/community\/contribution\/[^/]+$/, '/community/contribution/:id'],
    [/^\/builders\/contribution\/[^/]+$/, '/builders/contribution/:id'],
    [/^\/validators\/contribution\/[^/]+$/, '/validators/contribution/:id'],
    [/^\/contribution\/[^/]+$/, '/contribution/:id'],
    [/^\/contributions\/[^/]+$/, '/contributions/:id'],
    [/^\/contribution-type\/[^/]+$/, '/contribution-type/:id'],
    [/^\/mission\/[^/]+$/, '/mission/:id'],
    [/^\/badge\/[^/]+$/, '/contribution/:id'],
    [/^\/builders\/projects\/[^/]+\/edit$/, '/builders/projects/:slug/edit'],
    [/^\/builders\/projects\/[^/]+$/, '/builders/projects/:slug'],
    [/^\/builders\/startup-requests\/[^/]+$/, '/builders/startup-requests/:id'],
  ];
  const match = replacements.find(([pattern]) => pattern.test(route));
  return match ? match[1] : route;
}

function roleContextFromRoute(path) {
  const route = normalizePath(path);
  if (route.startsWith('/builders')) return 'builder';
  if (route.startsWith('/validators')) return 'validator';
  if (route.startsWith('/community')) return 'community';
  if (route.startsWith('/stewards')) return 'steward';
  if (
    route.startsWith('/ecosystem-partners') ||
    route.startsWith('/gen-news') ||
    route.startsWith('/gen-tv') ||
    route.startsWith('/genesis') ||
    route.startsWith('/foundations') ||
    route === '/manifesto' ||
    route === '/how-it-works'
  ) {
    return 'ecosystem';
  }
  if (
    route === '/' ||
    route === '/testnets' ||
    route === '/metrics' ||
    route === '/participants'
  ) {
    return 'overview';
  }
  return 'unknown';
}

function userRoleState(user) {
  if (!user) return 'none';
  const roles = [];
  if (user.builder) roles.push('builder');
  if (user.validator) roles.push('validator');
  if (user.creator) roles.push('community');
  if (user.steward) roles.push('steward');
  if (roles.length > 1) return 'multiple';
  return roles[0] || 'none';
}

function journeyState(isAuthenticated, user, role) {
  if (!['builder', 'validator', 'community'].includes(role)) return undefined;
  if (!isAuthenticated) return 'not_started';
  if (hasEarnedRole(user, role)) return 'earned';
  if (role === 'validator' && user?.has_validator_waitlist) return 'waitlisted';
  if (hasStartedJourney(user, role)) return 'started';
  return 'not_started';
}

function funnelState(isAuthenticated, user, role) {
  if (!['builder', 'validator', 'community'].includes(role)) return undefined;
  if (role === 'validator' && isAuthenticated && !user?.validator && user?.has_validator_waitlist) {
    return 'waitlisted';
  }
  return roleFunnelState(isAuthenticated, user, role);
}

function deviceType() {
  if (!canUseBrowser() || !window.matchMedia) return 'desktop';
  return window.matchMedia('(max-width: 767px)').matches ? 'mobile' : 'desktop';
}

function shouldDropKey(key) {
  const lowerKey = String(key || '').toLowerCase();
  if (FORBIDDEN_KEYS.has(lowerKey)) return true;
  if (lowerKey.endsWith('_id') && !SAFE_ID_KEYS.has(lowerKey)) return true;
  if (lowerKey.includes('error_message')) return true;
  if (lowerKey.includes('raw')) return true;
  return false;
}

function sanitizeString(key, value) {
  if (key === 'page_location') {
    const route = templateRoute(value);
    if (canUseBrowser()) return `${window.location.origin}${route}`;
    return route;
  }
  if (ROUTE_PARAM_KEYS.has(key)) return templateRoute(value);
  if (ADDRESS_RE.test(value) || EMAIL_RE.test(value)) return undefined;
  if (URL_VALUE_RE.test(value)) return undefined;
  return value.slice(0, MAX_STRING_LENGTH);
}

export function sanitizeAnalyticsParams(params = {}) {
  const sanitized = {};
  if (!params || typeof params !== 'object' || Array.isArray(params)) return sanitized;

  for (const [rawKey, rawValue] of Object.entries(params)) {
    const key = String(rawKey || '').trim();
    if (!key || shouldDropKey(key)) continue;
    if (rawValue === undefined || rawValue === null) continue;

    if (typeof rawValue === 'string') {
      const value = sanitizeString(key, rawValue);
      if (value !== undefined && value !== '') sanitized[key] = value;
      continue;
    }

    if (typeof rawValue === 'number') {
      if (!Number.isFinite(rawValue)) continue;
      sanitized[key] = Math.max(0, Math.min(Math.round(rawValue), MAX_DURATION_MS));
      continue;
    }

    if (typeof rawValue === 'boolean') {
      sanitized[key] = rawValue;
    }
  }

  return sanitized;
}

export function initializeAnalytics() {
  try {
    const id = trackingId();
    if (!id || !canUseBrowser() || !hasAnalyticsConsent()) return false;

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag() {
      window.dataLayer.push(arguments);
    };

    if (!scriptRequested && !document.getElementById(ANALYTICS_SCRIPT_ID)) {
      scriptRequested = true;
      const script = document.createElement('script');
      script.id = ANALYTICS_SCRIPT_ID;
      script.async = true;
      script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
      document.head.appendChild(script);
    }

    if (!initialized) {
      initialized = true;
      window.gtag('js', new Date());
      window.gtag('config', id, { send_page_view: false });
    }

    return true;
  } catch {
    return false;
  }
}

export function trackEvent(name, params = {}) {
  try {
    if (!name || typeof name !== 'string') return false;
    if (!hasAnalyticsConsent()) return false;
    if (!initializeAnalytics() || !window.gtag) return false;
    const safeName = name.replace(/[^a-zA-Z0-9_]/g, '_').slice(0, 40);
    window.gtag('event', safeName, sanitizeAnalyticsParams(params));
    return true;
  } catch {
    return false;
  }
}

export function trackPageView(route, params = {}) {
  try {
    const safeRoute = templateRoute(route);
    const pageParams = {
      ...params,
      route: safeRoute,
      page_path: safeRoute,
      page_location: canUseBrowser() ? `${window.location.origin}${safeRoute}` : safeRoute,
    };
    return trackEvent('page_view', pageParams);
  } catch {
    return false;
  }
}

export function markFunnelTime(key) {
  try {
    if (!canUseBrowser() || !key) return;
    sessionStorage.setItem(`${TIMER_PREFIX}${key}`, String(safeNow()));
  } catch {
    // Analytics timing is best-effort only.
  }
}

export function getFunnelDurationMs(key) {
  try {
    if (!canUseBrowser() || !key) return undefined;
    const startedAt = Number(sessionStorage.getItem(`${TIMER_PREFIX}${key}`));
    if (!Number.isFinite(startedAt) || startedAt <= 0) return undefined;
    const duration = safeNow() - startedAt;
    if (!Number.isFinite(duration) || duration < 0) return undefined;
    return Math.min(Math.round(duration), MAX_DURATION_MS);
  } catch {
    return undefined;
  }
}

export function markLifecycleTime(key, { overwrite = false } = {}) {
  try {
    if (!canUseBrowser() || !key) return false;
    const storageKey = `${LIFECYCLE_TIME_PREFIX}${safeStorageKey(key)}`;
    if (!overwrite && localStorage.getItem(storageKey)) return false;
    localStorage.setItem(storageKey, String(safeNow()));
    return true;
  } catch {
    return false;
  }
}

export function getLifecycleDurationMs(key) {
  try {
    if (!canUseBrowser() || !key) return undefined;
    const startedAt = Number(localStorage.getItem(`${LIFECYCLE_TIME_PREFIX}${safeStorageKey(key)}`));
    if (!Number.isFinite(startedAt) || startedAt <= 0) return undefined;
    const duration = safeNow() - startedAt;
    if (!Number.isFinite(duration) || duration < 0) return undefined;
    return Math.min(Math.round(duration), MAX_DURATION_MS);
  } catch {
    return undefined;
  }
}

export function markLifecycleFlag(key) {
  try {
    if (!canUseBrowser() || !key) return false;
    const storageKey = `${LIFECYCLE_FLAG_PREFIX}${safeStorageKey(key)}`;
    if (localStorage.getItem(storageKey)) return false;
    localStorage.setItem(storageKey, '1');
    return true;
  } catch {
    return false;
  }
}

export function hasLifecycleFlag(key) {
  try {
    if (!canUseBrowser() || !key) return false;
    return localStorage.getItem(`${LIFECYCLE_FLAG_PREFIX}${safeStorageKey(key)}`) === '1';
  } catch {
    return false;
  }
}

export function trackEventOnce(key, name, params = {}) {
  try {
    if (!key || hasLifecycleFlag(`event:${key}`)) return false;
    const tracked = trackEvent(name, params);
    if (tracked) markLifecycleFlag(`event:${key}`);
    return tracked;
  } catch {
    return false;
  }
}

export function getLifecycleDurations(role) {
  const safeRole = ['builder', 'validator', 'community'].includes(role) ? role : '';
  const params = {
    lifecycle_scope: 'browser',
    time_from_first_wallet_auth_success_ms: getLifecycleDurationMs('first_wallet_auth_success'),
    time_from_first_profile_completion_ms: getLifecycleDurationMs('first_profile_completion'),
    time_from_first_dashboard_ms: getLifecycleDurationMs('first_dashboard'),
  };
  if (safeRole) {
    params.time_from_role_unlock_ms = getLifecycleDurationMs(`role_unlocked:${safeRole}`);
    params.time_from_role_dashboard_ms = getLifecycleDurationMs(`first_dashboard:${safeRole}`);
    params.time_from_journey_start_ms = getFunnelDurationMs(`journey_start:${safeRole}`);
    params.time_from_first_journey_start_ms = getLifecycleDurationMs(`first_journey_start:${safeRole}`);
  }
  return sanitizeAnalyticsParams(params);
}

export function setConnectWalletIntent(intent = {}) {
  try {
    if (!canUseBrowser()) return;
    sessionStorage.setItem(
      CONNECT_WALLET_INTENT_KEY,
      JSON.stringify(sanitizeAnalyticsParams(intent)),
    );
  } catch {
    // Best-effort only.
  }
}

export function consumeConnectWalletIntent() {
  try {
    if (!canUseBrowser()) return {};
    const raw = sessionStorage.getItem(CONNECT_WALLET_INTENT_KEY);
    sessionStorage.removeItem(CONNECT_WALLET_INTENT_KEY);
    if (!raw) return {};
    return sanitizeAnalyticsParams(JSON.parse(raw));
  } catch {
    return {};
  }
}

export function getAnalyticsContext(extra = {}) {
  try {
    const route = templateRoute(extra.route || (canUseBrowser() ? window.location.pathname : '/'));
    const role = extra.role_context || roleContextFromRoute(route);
    const auth = get(authState) || {};
    const storeState = get(userStore) || {};
    const user = extra.user || storeState.user || null;
    const isAuthenticated = Boolean(auth.isAuthenticated);
    const context = {
      route,
      auth_state: isAuthenticated ? 'authenticated' : 'unauthenticated',
      role_context: role,
      user_role_state: userRoleState(user),
      role_funnel_state: extra.role_funnel_state ?? funnelState(isAuthenticated, user, role),
      journey_state: extra.journey_state ?? journeyState(isAuthenticated, user, role),
      device_type: deviceType(),
      ...extra,
    };
    return sanitizeAnalyticsParams(context);
  } catch {
    return sanitizeAnalyticsParams(extra);
  }
}

export function setAnalyticsConsent(granted) {
  try {
    const status = granted && !isDoNotTrackEnabled() ? 'granted' : 'denied';
    if (canUseBrowser()) {
      localStorage.setItem(ANALYTICS_CONSENT_KEY, status);
      if (window.gtag) {
        window.gtag('consent', 'update', {
          analytics_storage: status === 'granted' ? 'granted' : 'denied',
        });
      }
    }
    analyticsConsent.set(status);
    if (status === 'granted') initializeAnalytics();
    return status === 'granted';
  } catch {
    analyticsConsent.set(granted ? 'granted' : 'denied');
    if (granted) initializeAnalytics();
    return Boolean(granted);
  }
}
