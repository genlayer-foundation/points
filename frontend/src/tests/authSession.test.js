import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  requestUse: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mocks.get,
      post: mocks.post,
      interceptors: {
        request: { use: mocks.requestUse },
      },
    })),
  },
}));

vi.mock('../lib/config.js', () => ({
  API_BASE_URL: 'https://api.example.test',
}));

vi.mock('../lib/csrf.js', () => ({
  attachCsrfToken: vi.fn((config) => config),
}));

vi.mock('../lib/userStore.js', () => ({
  userStore: {
    clearUser: vi.fn(),
    loadUser: vi.fn().mockResolvedValue({ id: 1 }),
  },
}));

vi.mock('../stores/category.js', () => ({
  detectCategoryFromRoute: vi.fn(() => 'global'),
}));

vi.mock('../lib/roleState.js', () => ({
  roleForCategory: vi.fn(() => 'validator'),
}));

function setDocumentHidden(hidden) {
  Object.defineProperty(document, 'hidden', {
    configurable: true,
    value: hidden,
  });
}

async function importAuth() {
  mocks.get.mockResolvedValue({ data: { authenticated: false } });
  const auth = await import('../lib/auth.js');
  await Promise.resolve();
  vi.clearAllMocks();
  return auth;
}

describe('auth session refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    vi.resetModules();
    localStorage.clear();
    setDocumentHidden(false);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('shares one refresh request across concurrent callers', async () => {
    const { refreshSession } = await importAuth();
    let resolveRefresh;
    mocks.post.mockImplementation(() => new Promise(resolve => {
      resolveRefresh = resolve;
    }));

    const firstRefresh = refreshSession();
    const secondRefresh = refreshSession();

    expect(mocks.post).toHaveBeenCalledTimes(1);

    resolveRefresh({ data: {} });
    await expect(Promise.all([firstRefresh, secondRefresh])).resolves.toEqual([true, true]);
  });

  it('shares forced verification with concurrent cached callers', async () => {
    const { verifyAuth } = await importAuth();
    let resolveVerification;
    mocks.get.mockImplementation(() => new Promise(resolve => {
      resolveVerification = resolve;
    }));

    const forcedVerification = verifyAuth({ force: true });
    const cachedVerification = verifyAuth();

    expect(mocks.get).toHaveBeenCalledTimes(1);

    resolveVerification({ data: { authenticated: true, address: '0x123' } });
    await expect(Promise.all([forcedVerification, cachedVerification])).resolves.toEqual([true, true]);
  });

  it('does not run the interval refresh while the document is hidden', async () => {
    const { authState } = await importAuth();
    mocks.post.mockResolvedValue({ data: {} });
    authState.setAuthenticated(true, '0x123');

    setDocumentHidden(true);
    await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    expect(mocks.post).not.toHaveBeenCalled();

    setDocumentHidden(false);
    await vi.advanceTimersByTimeAsync(5 * 60 * 1000);
    expect(mocks.post).toHaveBeenCalledTimes(1);
  });

  // resetModules() re-imports auth.js, which registers another visibilitychange
  // listener on the shared document, so earlier tests leave listeners behind.
  // These assertions therefore measure growth across flips, not absolute counts.
  it('throttles the visibility refresh so tab flipping is not one request per flip', async () => {
    const { authState } = await importAuth();
    mocks.post.mockResolvedValue({ data: {} });
    authState.setAuthenticated(true, '0x123');

    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(1000);
    const afterFirstFlip = mocks.post.mock.calls.length;
    expect(afterFirstFlip).toBeGreaterThan(0);

    for (let flip = 0; flip < 4; flip += 1) {
      setDocumentHidden(true);
      document.dispatchEvent(new Event('visibilitychange'));
      setDocumentHidden(false);
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(1000);
    }

    expect(mocks.post.mock.calls.length).toBe(afterFirstFlip);
  });

  it('catches up on visibility once the throttle window has passed', async () => {
    const { authState } = await importAuth();
    mocks.post.mockResolvedValue({ data: {} });
    authState.setAuthenticated(true, '0x123');

    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(0);
    const afterFirstFlip = mocks.post.mock.calls.length;
    expect(afterFirstFlip).toBeGreaterThan(0);

    await vi.advanceTimersByTimeAsync(61 * 1000);
    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(0);

    expect(mocks.post.mock.calls.length).toBeGreaterThan(afterFirstFlip);
  });

  it('does not re-verify immediately after a 5xx', async () => {
    const { verifyAuth } = await importAuth();
    const serverError = new Error('boom');
    serverError.response = { status: 500 };
    mocks.get.mockRejectedValue(serverError);

    await verifyAuth({ force: true });
    await verifyAuth({ force: true });
    await verifyAuth({ force: true });

    // One attempt, then the cooldown absorbs the rest.
    expect(mocks.get).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(31 * 1000);
    await verifyAuth({ force: true });
    expect(mocks.get).toHaveBeenCalledTimes(2);
  });

  it('still logs out on a definitive rejection', async () => {
    const { verifyAuth, authState } = await importAuth();
    const authError = new Error('gone');
    authError.response = { status: 403 };
    mocks.get.mockRejectedValue(authError);

    await expect(verifyAuth({ force: true })).resolves.toBe(false);
    expect(authState.get().isAuthenticated).toBe(false);
  });
});
