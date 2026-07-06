import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  requestUse: vi.fn(),
  responseUse: vi.fn(),
}));

vi.unmock('../lib/api');
vi.unmock('../lib/api.js');

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      delete: vi.fn(),
      get: mocks.get,
      patch: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      interceptors: {
        request: { use: mocks.requestUse },
        response: { use: mocks.responseUse },
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

describe('api client', () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('removes invalid query params while preserving valid falsy values', async () => {
    await import('../lib/api.js');
    const interceptor = mocks.requestUse.mock.calls[0][0];

    const config = await interceptor({
      headers: {},
      params: {
        missing: undefined,
        emptyValue: null,
        undefinedString: 'undefined',
        nullString: 'null',
        zero: 0,
        falseValue: false,
        emptyString: '',
        search: 'builder',
      },
    });

    expect(config.params).toEqual({
      zero: 0,
      falseValue: false,
      emptyString: '',
      search: 'builder',
    });
  });

  it('deduplicates and briefly caches public metrics overview requests', async () => {
    vi.useFakeTimers();
    const firstResponse = { data: { total_points: 10 } };
    const secondResponse = { data: { total_points: 11 } };
    mocks.get.mockResolvedValueOnce(firstResponse).mockResolvedValueOnce(secondResponse);

    const { metricsAPI } = await import('../lib/api.js');

    const [first, second] = await Promise.all([
      metricsAPI.getOverview(),
      metricsAPI.getOverview(),
    ]);
    expect(first).toBe(firstResponse);
    expect(second).toBe(firstResponse);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get).toHaveBeenCalledWith('/metrics/overview/');

    const cached = await metricsAPI.getOverview();
    expect(cached).toBe(firstResponse);
    expect(mocks.get).toHaveBeenCalledTimes(1);

    vi.advanceTimersByTime(31_000);
    const refreshed = await metricsAPI.getOverview();
    expect(refreshed).toBe(secondResponse);
    expect(mocks.get).toHaveBeenCalledTimes(2);
  });

  it('deduplicates network activity metrics separately', async () => {
    const response = { data: { points: [] } };
    mocks.get.mockResolvedValue(response);

    const { metricsAPI } = await import('../lib/api.js');

    const [first, second] = await Promise.all([
      metricsAPI.getNetworkActivity(),
      metricsAPI.getNetworkActivity(),
    ]);

    expect(first).toBe(response);
    expect(second).toBe(response);
    expect(mocks.get).toHaveBeenCalledTimes(1);
    expect(mocks.get).toHaveBeenCalledWith('/metrics/overview/network-activity/');
  });

  it('fetches every page for bounded small catalogs', async () => {
    const oversizedPageSize = 200;
    mocks.get
      .mockResolvedValueOnce({ data: { results: [{ id: 1 }], next: 'page-2' } })
      .mockResolvedValueOnce({ data: { results: [{ id: 2 }], next: null } });

    const { contributionsAPI } = await import('../lib/api.js');
    const response = await contributionsAPI.getAllContributionTypes({
      category: 'community',
      page_size: oversizedPageSize,
    });

    expect(response.data).toEqual([{ id: 1 }, { id: 2 }]);
    expect(mocks.get).toHaveBeenCalledTimes(2);
    expect(mocks.get).toHaveBeenNthCalledWith(1, '/contribution-types/', {
      params: { category: 'community', page_size: 50, page: 1 },
    });
    expect(mocks.get).toHaveBeenNthCalledWith(2, '/contribution-types/', {
      params: { category: 'community', page_size: 50, page: 2 },
    });
  });
});
