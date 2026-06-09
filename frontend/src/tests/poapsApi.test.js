import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  delete: vi.fn(),
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  requestUse: vi.fn(),
  responseUse: vi.fn(),
}));

vi.unmock('../lib/api');
vi.unmock('../lib/api.js');

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      delete: mocks.delete,
      get: mocks.get,
      patch: mocks.patch,
      post: mocks.post,
      put: mocks.put,
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

describe('poapsAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts claim-link tokens in the request body', async () => {
    const { poapsAPI } = await import('../lib/api.js');

    poapsAPI.claimLink('synthetic-claim-token');

    expect(mocks.post).toHaveBeenCalledWith(
      '/poaps/claim-link/',
      { token: 'synthetic-claim-token' }
    );
  });
});
