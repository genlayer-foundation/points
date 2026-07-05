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
});
