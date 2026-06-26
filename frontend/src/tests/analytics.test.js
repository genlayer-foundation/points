import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

const stores = vi.hoisted(() => {
  let authValue = {
    isAuthenticated: false,
    address: null,
    provider: null,
    loading: false,
    error: null,
    hasVerified: true,
  };
  let userValue = { user: null, loading: false, error: null };
  return {
    authState: {
      subscribe(fn) {
        fn(authValue);
        return () => {};
      },
      set(value) {
        authValue = value;
      },
    },
    userStore: {
      subscribe(fn) {
        fn(userValue);
        return () => {};
      },
      set(value) {
        userValue = value;
      },
    },
    reset() {
      authValue = {
        isAuthenticated: false,
        address: null,
        provider: null,
        loading: false,
        error: null,
        hasVerified: true,
      };
      userValue = { user: null, loading: false, error: null };
    },
  };
});

vi.mock('../lib/auth.js', () => ({
  authState: stores.authState,
}));

vi.mock('../lib/userStore.js', () => ({
  userStore: stores.userStore,
}));

async function loadAnalytics() {
  vi.resetModules();
  return import('../lib/analytics.js');
}

function dataLayerCalls() {
  return (window.dataLayer || []).map((entry) => Array.from(entry));
}

describe('analytics helper', () => {
  beforeEach(() => {
    stores.reset();
    vi.unstubAllEnvs();
    document.head.innerHTML = '';
    document.body.innerHTML = '';
    window.dataLayer = undefined;
    window.gtag = undefined;
    window.history.pushState({}, '', '/');
    sessionStorage.clear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  it('no-ops when GA is not configured', async () => {
    const analytics = await loadAnalytics();

    expect(analytics.initializeAnalytics()).toBe(false);
    expect(analytics.trackEvent('role_landing_view')).toBe(false);
    expect(document.querySelectorAll('script[src*="googletagmanager"]').length).toBe(0);
  });

  it('initializes once and disables automatic config page views', async () => {
    vi.stubEnv('VITE_GOOGLE_ANALYTICS_ID', 'G-TEST123');
    const analytics = await loadAnalytics();

    expect(analytics.initializeAnalytics()).toBe(true);
    expect(analytics.initializeAnalytics()).toBe(true);

    expect(document.querySelectorAll('#google-analytics-gtag').length).toBe(1);
    const configCalls = dataLayerCalls().filter((call) => call[0] === 'config');
    expect(configCalls).toHaveLength(1);
    expect(configCalls[0][1]).toBe('G-TEST123');
    expect(configCalls[0][2]).toEqual({ send_page_view: false });
  });

  it('sends explicit templated page views', async () => {
    vi.stubEnv('VITE_GOOGLE_ANALYTICS_ID', 'G-TEST123');
    const analytics = await loadAnalytics();

    analytics.trackPageView('/participant/0x1234567890abcdef1234567890abcdef12345678?ref=ABC');

    const eventCall = dataLayerCalls().find((call) => call[0] === 'event' && call[1] === 'page_view');
    expect(eventCall[2].route).toBe('/participant/:address');
    expect(eventCall[2].page_path).toBe('/participant/:address');
    expect(eventCall[2].page_location).toBe(`${window.location.origin}/participant/:address`);
  });

  it('sanitizes unsafe params and templates dynamic route params', async () => {
    const analytics = await loadAnalytics();
    const sanitized = analytics.sanitizeAnalyticsParams({
      route: '/community/poaps/founders-drop',
      address: '0x1234567890abcdef1234567890abcdef12345678',
      email: 'person@example.com',
      username: 'raw-user',
      post_url: 'https://x.com/user/status/123',
      error_message: 'backend included raw details',
      cta_id: 'builder_start',
      step_id: 'x_post',
      long_value: 'x'.repeat(160),
      completed_step_count: 2.4,
      ignored_object: { nested: true },
      ignored_array: ['x'],
      empty: null,
    });

    expect(sanitized).toEqual({
      route: '/community/poaps/:slug',
      cta_id: 'builder_start',
      step_id: 'x_post',
      long_value: 'x'.repeat(100),
      completed_step_count: 2,
    });
  });

  it('persists funnel timers in session storage', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(1_000);
    const analytics = await loadAnalytics();

    analytics.markFunnelTime('journey_start:builder');
    vi.setSystemTime(2_750);

    expect(analytics.getFunnelDurationMs('journey_start:builder')).toBe(1750);
  });

  it('persists lifecycle timers and one-shot events in local storage', async () => {
    vi.stubEnv('VITE_GOOGLE_ANALYTICS_ID', 'G-TEST123');
    vi.useFakeTimers();
    vi.setSystemTime(10_000);
    const analytics = await loadAnalytics();

    expect(analytics.markLifecycleTime('first_wallet_auth_success')).toBe(true);
    expect(analytics.markLifecycleTime('first_wallet_auth_success')).toBe(false);
    vi.setSystemTime(11_000);
    expect(analytics.markLifecycleTime('first_journey_start:builder')).toBe(true);

    vi.setSystemTime(13_250);
    expect(analytics.getLifecycleDurationMs('first_wallet_auth_success')).toBe(3250);
    expect(analytics.getLifecycleDurations('builder')).toMatchObject({
      time_from_first_wallet_auth_success_ms: 3250,
      time_from_first_journey_start_ms: 2250,
    });

    expect(analytics.trackEventOnce('first_dashboard_view', 'first_dashboard_view', {
      route: '/builders',
    })).toBe(true);
    expect(analytics.trackEventOnce('first_dashboard_view', 'first_dashboard_view', {
      route: '/builders',
    })).toBe(false);

    const firstDashboardEvents = dataLayerCalls().filter(
      (call) => call[0] === 'event' && call[1] === 'first_dashboard_view'
    );
    expect(firstDashboardEvents).toHaveLength(1);
  });

  it('builds shared context without sending user identifiers', async () => {
    stores.authState.set({
      isAuthenticated: true,
      address: '0x1234567890abcdef1234567890abcdef12345678',
      hasVerified: true,
    });
    stores.userStore.set({
      user: { builder: {}, creator: {}, email: 'person@example.com' },
      loading: false,
      error: null,
    });
    window.history.pushState({}, '', '/builders/journey');
    const analytics = await loadAnalytics();

    expect(analytics.getAnalyticsContext()).toMatchObject({
      route: '/builders/journey',
      auth_state: 'authenticated',
      role_context: 'builder',
      user_role_state: 'multiple',
      role_funnel_state: 'earned',
      journey_state: 'earned',
    });
  });
});
