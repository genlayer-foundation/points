import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock('axios', () => ({
  default: { get: mocks.get },
}));

async function loadCsrf() {
  vi.resetModules();
  return import('../lib/csrf.js');
}

function csrfResponse(token = 'token-1') {
  return { data: { csrfToken: token, csrfCookieName: 'csrftoken' } };
}

function clearCsrfCookie() {
  document.cookie = 'csrftoken=; Max-Age=0; path=/';
}

describe('csrf token cache', () => {
  beforeEach(() => {
    mocks.get.mockReset();
    // Production splits the SPA and API across hosts, so document.cookie never
    // carries the CSRF cookie. Model that here.
    clearCsrfCookie();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not touch the endpoint for safe methods', async () => {
    const { attachCsrfToken } = await loadCsrf();

    const config = await attachCsrfToken({ method: 'get' });

    expect(mocks.get).not.toHaveBeenCalled();
    expect(config.headers?.['X-CSRFToken']).toBeUndefined();
  });

  it('fetches once and reuses the token for sequential unsafe requests', async () => {
    mocks.get.mockResolvedValue(csrfResponse());
    const { attachCsrfToken } = await loadCsrf();

    const first = await attachCsrfToken({ method: 'post' });
    const second = await attachCsrfToken({ method: 'patch' });
    const third = await attachCsrfToken({ method: 'delete' });

    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(first.headers['X-CSRFToken']).toBe('token-1');
    expect(second.headers['X-CSRFToken']).toBe('token-1');
    expect(third.headers['X-CSRFToken']).toBe('token-1');
  });

  it('coalesces simultaneous unsafe requests into one fetch', async () => {
    let resolveGet;
    mocks.get.mockImplementation(
      () => new Promise((resolve) => { resolveGet = resolve; })
    );
    const { attachCsrfToken } = await loadCsrf();

    const pending = Promise.all([
      attachCsrfToken({ method: 'post' }),
      attachCsrfToken({ method: 'post' }),
    ]);
    resolveGet(csrfResponse());
    const [first, second] = await pending;

    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(first.headers['X-CSRFToken']).toBe('token-1');
    expect(second.headers['X-CSRFToken']).toBe('token-1');
  });

  it('refetches after clearCsrfToken', async () => {
    mocks.get
      .mockResolvedValueOnce(csrfResponse('token-1'))
      .mockResolvedValueOnce(csrfResponse('token-2'));
    const { attachCsrfToken, clearCsrfToken } = await loadCsrf();

    await attachCsrfToken({ method: 'post' });
    clearCsrfToken();
    const after = await attachCsrfToken({ method: 'post' });

    expect(mocks.get).toHaveBeenCalledTimes(2);
    expect(after.headers['X-CSRFToken']).toBe('token-2');
  });

  it('never writes the token to persistent storage', async () => {
    mocks.get.mockResolvedValue(csrfResponse('secret-token'));
    const localSpy = vi.spyOn(Storage.prototype, 'setItem');
    const { attachCsrfToken } = await loadCsrf();

    await attachCsrfToken({ method: 'post' });

    const persisted = localSpy.mock.calls.map(([, value]) => String(value));
    expect(persisted.some((value) => value.includes('secret-token'))).toBe(false);
  });

  it('prefers a readable cookie over the cached token', async () => {
    document.cookie = 'csrftoken=cookie-token';
    const { attachCsrfToken } = await loadCsrf();

    const config = await attachCsrfToken({ method: 'post' });

    expect(mocks.get).not.toHaveBeenCalled();
    expect(config.headers['X-CSRFToken']).toBe('cookie-token');
  });
});

describe('isCsrfFailure', () => {
  it('recognises a DRF CSRF rejection', async () => {
    const { isCsrfFailure } = await loadCsrf();

    expect(isCsrfFailure({
      response: { status: 403, data: { detail: 'CSRF Failed: Origin checking failed.' } },
    })).toBe(true);
  });

  it('does not treat a permission 403 as a CSRF failure', async () => {
    const { isCsrfFailure } = await loadCsrf();

    expect(isCsrfFailure({
      response: {
        status: 403,
        data: { detail: 'You do not have permission to perform this action.' },
      },
    })).toBe(false);
  });

  it('ignores non-403 responses and network errors', async () => {
    const { isCsrfFailure } = await loadCsrf();

    expect(isCsrfFailure({ response: { status: 401, data: { detail: 'CSRF Failed: x' } } })).toBe(false);
    expect(isCsrfFailure({ response: { status: 500, data: {} } })).toBe(false);
    expect(isCsrfFailure({})).toBe(false);
    expect(isCsrfFailure(undefined)).toBe(false);
  });
});

describe('retryOnceAfterCsrfFailure', () => {
  beforeEach(() => {
    mocks.get.mockReset();
    clearCsrfCookie();
  });

  it('clears the stale token and retries once with a fresh token', async () => {
    mocks.get
      .mockResolvedValueOnce(csrfResponse('stale-token'))
      .mockResolvedValueOnce(csrfResponse('fresh-token'));
    const { attachCsrfToken, retryOnceAfterCsrfFailure } = await loadCsrf();
    const csrfError = {
      response: { status: 403, data: { detail: 'CSRF Failed: CSRF token incorrect.' } },
    };
    const request = vi.fn(async () => {
      const config = await attachCsrfToken({ method: 'post' });
      if (request.mock.calls.length === 1) throw csrfError;
      return config;
    });

    const response = await retryOnceAfterCsrfFailure(request);

    expect(request).toHaveBeenCalledTimes(2);
    expect(mocks.get).toHaveBeenCalledTimes(2);
    expect(response.headers['X-CSRFToken']).toBe('fresh-token');
  });

  it('does not retry authorization or application failures', async () => {
    const { retryOnceAfterCsrfFailure } = await loadCsrf();
    const permissionError = {
      response: { status: 403, data: { detail: 'You do not have permission.' } },
    };
    const request = vi.fn().mockRejectedValue(permissionError);

    await expect(retryOnceAfterCsrfFailure(request)).rejects.toBe(permissionError);
    expect(request).toHaveBeenCalledTimes(1);
  });

  it('stops after one retry if the fresh token is also rejected', async () => {
    const { retryOnceAfterCsrfFailure } = await loadCsrf();
    const csrfError = {
      response: { status: 403, data: { detail: 'CSRF Failed: CSRF token incorrect.' } },
    };
    const request = vi.fn().mockRejectedValue(csrfError);

    await expect(retryOnceAfterCsrfFailure(request)).rejects.toBe(csrfError);
    expect(request).toHaveBeenCalledTimes(2);
  });
});
