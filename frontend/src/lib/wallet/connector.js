import { createConfig, http } from 'wagmi';
import { mainnet } from 'wagmi/chains';
import { metaMask } from 'wagmi/connectors';

// Create wagmi config with MetaMask connector and persistence
export const config = createConfig({
  chains: [mainnet],
  connectors: [
    metaMask(),
  ],
  transports: {
    [mainnet.id]: http(),
  },
  // Storage configuration for persistence
  storageKey: 'tally-wallet-connection',
  // This will enable automatic reconnection to previously connected wallet
  storage: {
    getItem: (key) => {
      try {
        return JSON.parse(window.localStorage.getItem(key) || '');
      } catch {
        return null;
      }
    },
    setItem: (key, value) => {
      window.localStorage.setItem(key, JSON.stringify(value));
    },
    removeItem: (key) => {
      window.localStorage.removeItem(key);
    },
  },
});

// Export for easy imports
export { metaMask } from 'wagmi/connectors';
export { useAccount, useConnect, useDisconnect } from 'wagmi';