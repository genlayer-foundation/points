import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  createEVMClient: vi.fn(),
}));

vi.mock('@metamask/connect-evm', () => ({
  createEVMClient: mocks.createEVMClient,
}));

function makeClient(overrides = {}) {
  return {
    disconnect: vi.fn().mockResolvedValue(undefined),
    connect: vi.fn().mockResolvedValue(undefined),
    getProvider: vi.fn(() => ({ selectedChainId: '0x107d' })),
    ...overrides,
  };
}

async function freshModule() {
  vi.resetModules();
  return import('../lib/metamaskConnect.js');
}

describe('getMetaMaskConnectProvider', () => {
  beforeEach(() => {
    mocks.createEVMClient.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('drops any persisted session before connecting so a stale relay channel cannot swallow the request', async () => {
    vi.useFakeTimers();
    const calls = [];
    const client = makeClient({
      disconnect: vi.fn(async () => calls.push('disconnect')),
      connect: vi.fn(async () => calls.push('connect')),
    });
    mocks.createEVMClient.mockResolvedValue(client);

    const { getMetaMaskConnectProvider } = await freshModule();
    await getMetaMaskConnectProvider();

    expect(calls).toEqual(['disconnect', 'connect']);
    expect(client.connect).toHaveBeenCalledWith({ chainIds: ['0x107d'], forceRequest: true });
    expect(vi.getTimerCount()).toBe(0);
  });

  it('still connects when tearing down the stale session hangs on the dead relay', async () => {
    vi.useFakeTimers();
    const client = makeClient({
      disconnect: vi.fn(() => new Promise(() => {})), // never resolves
    });
    mocks.createEVMClient.mockResolvedValue(client);

    const { getMetaMaskConnectProvider, METAMASK_CONNECT_DISCONNECT_TIMEOUT_MS } = await freshModule();
    const providerPromise = getMetaMaskConnectProvider();
    await vi.advanceTimersByTimeAsync(METAMASK_CONNECT_DISCONNECT_TIMEOUT_MS);
    const provider = await providerPromise;

    expect(client.connect).toHaveBeenCalledTimes(1);
    expect(provider.__genlayerMetaMaskConnect).toBe(true);
  });

  it('still connects when disconnect rejects', async () => {
    const client = makeClient({
      disconnect: vi.fn().mockRejectedValue(new Error('no session')),
    });
    mocks.createEVMClient.mockResolvedValue(client);

    const { getMetaMaskConnectProvider } = await freshModule();
    await expect(getMetaMaskConnectProvider()).resolves.toBeTruthy();
    expect(client.connect).toHaveBeenCalledTimes(1);
  });

  it('normalizes user cancels from connect to the EIP-1193 4001 shape', async () => {
    const client = makeClient({
      connect: vi.fn().mockRejectedValue(new Error('Request rejected')),
    });
    mocks.createEVMClient.mockResolvedValue(client);

    const { getMetaMaskConnectProvider } = await freshModule();
    await expect(getMetaMaskConnectProvider()).rejects.toMatchObject({ code: 4001 });
  });
});
