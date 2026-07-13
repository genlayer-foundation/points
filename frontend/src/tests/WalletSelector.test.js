import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { afterEach, describe, expect, it, vi } from 'vitest';

import WalletSelector from '../components/WalletSelector.svelte';

describe('WalletSelector provider support', () => {
  afterEach(() => {
    cleanup();
    document.querySelectorAll('.wallet-selector-backdrop').forEach((node) => node.remove());
    document.body.style.overflow = '';
    delete window.ethereum;
    delete window.okxwallet;
    vi.restoreAllMocks();
  });

  function dispatchProviderAnnouncement({ provider, name, rdns, uuid }) {
    window.dispatchEvent(new CustomEvent('eip6963:announceProvider', {
      detail: {
        info: {
          uuid,
          name,
          icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>',
          rdns,
        },
        provider,
      },
    }));
  }

  function announceProvider(detail) {
    const announce = () => dispatchProviderAnnouncement(detail);
    window.addEventListener('eip6963:requestProvider', announce, { once: true });
  }

  it('selects the Rabby provider announced through EIP-6963', async () => {
    const provider = {
      isMetaMask: true,
      isRabby: true,
      request: vi.fn(),
    };
    const onSelect = vi.fn().mockResolvedValue(undefined);
    announceProvider({
      provider,
      name: 'Rabby Wallet',
      rdns: 'io.rabby',
      uuid: 'd8d3e4f2-cbd1-48e2-950a-7b640a7b7c13',
    });

    render(WalletSelector, {
      props: {
        isOpen: true,
        onSelect,
      },
    });

    const rabbyButton = await screen.findByRole('button', { name: /Rabby Wallet/ });
    await waitFor(() => expect(rabbyButton.textContent).toContain('Ready'));
    expect(screen.getByRole('button', { name: /MetaMask/ }).textContent).not.toContain('Ready');

    await fireEvent.click(rabbyButton);

    await waitFor(() => {
      expect(onSelect).toHaveBeenCalledWith(provider, 'Rabby Wallet');
    });
  });

  it('selects OKX without misidentifying its MetaMask-compatible provider', async () => {
    const provider = {
      isMetaMask: true,
      isOkxWallet: true,
      request: vi.fn(),
    };
    const onSelect = vi.fn().mockResolvedValue(undefined);
    announceProvider({
      provider,
      name: 'OKX Wallet',
      rdns: 'com.okex.wallet',
      uuid: '9f9889f6-b3dc-4f92-85e6-d836b4d70e67',
    });

    render(WalletSelector, { props: { isOpen: true, onSelect } });

    const okxButton = await screen.findByRole('button', { name: /OKX Wallet/ });
    await waitFor(() => expect(okxButton.textContent).toContain('Ready'));
    expect(screen.getByRole('button', { name: /MetaMask/ }).textContent).not.toContain('Ready');

    await fireEvent.click(okxButton);
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith(provider, 'OKX Wallet'));
  });

  it('supports the OKX legacy injected namespace', async () => {
    const provider = {
      isOkxWallet: true,
      request: vi.fn(),
    };
    const onSelect = vi.fn().mockResolvedValue(undefined);
    window.okxwallet = provider;

    render(WalletSelector, { props: { isOpen: true, onSelect } });

    const okxButton = await screen.findByRole('button', { name: /OKX Wallet/ });
    expect(okxButton.textContent).toContain('Ready');
    await fireEvent.click(okxButton);
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith(provider, 'OKX Wallet'));
  });

  it('shows other EIP-6963 wallets without needing a hard-coded integration', async () => {
    const provider = { request: vi.fn() };
    const onSelect = vi.fn().mockResolvedValue(undefined);
    announceProvider({
      provider,
      name: 'Example Wallet',
      rdns: 'com.example.wallet',
      uuid: '08b353b7-7d16-4751-9689-96bff322b90a',
    });

    render(WalletSelector, { props: { isOpen: true, onSelect } });

    const walletButton = await screen.findByRole('button', { name: /Example Wallet/ });
    expect(walletButton.textContent).toContain('Ready');
    await fireEvent.click(walletButton);
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith(provider, 'Example Wallet'));
  });

  it('reuses an injected wallet entry when the same provider changes UUID', async () => {
    const provider = { request: vi.fn() };
    announceProvider({
      provider,
      name: 'Example Wallet',
      uuid: '08b353b7-7d16-4751-9689-96bff322b90a',
    });

    render(WalletSelector, { props: { isOpen: true } });
    await screen.findByRole('button', { name: /Example Wallet/ });

    dispatchProviderAnnouncement({
      provider,
      name: 'Example Wallet',
      uuid: '0ecb060b-5f89-4fdc-aafd-d1b9e917a4a6',
    });

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /Example Wallet/ })).toHaveLength(1);
    });
  });

  it('explains the OKX app handoff on mobile browsers', async () => {
    vi.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)');

    render(WalletSelector, { props: { isOpen: true } });

    const okxButton = await screen.findByRole('button', { name: /OKX Wallet/ });
    await waitFor(() => {
      expect(okxButton.textContent).toContain('Continue in the OKX Wallet app');
      expect(okxButton.textContent).toContain('Open app');
    });
    expect(screen.getByText('Continue in a wallet app')).toBeTruthy();
  });
});
