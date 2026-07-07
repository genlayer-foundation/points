import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  markSeen: vi.fn(),
  unseenCount: vi.fn(),
}));

vi.mock('../lib/api.js', () => ({
  whatsNewAPI: {
    list: mocks.list,
    markSeen: mocks.markSeen,
    unseenCount: mocks.unseenCount,
  },
}));

describe('whatsNewStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  it('shares one unseen-count request across concurrent refresh calls', async () => {
    const { whatsNewStore } = await import('../lib/whatsNewStore.js');
    let resolveCount;
    mocks.unseenCount.mockImplementation(() => new Promise(resolve => {
      resolveCount = resolve;
    }));

    const firstRefresh = whatsNewStore.refresh();
    const secondRefresh = whatsNewStore.refresh();

    expect(mocks.unseenCount).toHaveBeenCalledTimes(1);

    resolveCount({ data: { count: 7 } });
    await expect(Promise.all([firstRefresh, secondRefresh])).resolves.toEqual([7, 7]);
    expect(get(whatsNewStore).unseenCount).toBe(7);
  });
});
