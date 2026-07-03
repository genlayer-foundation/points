// MetaMask Connect SDK wrapper. Only ever load this module via dynamic
// import() — a static import would pull the SDK into the entry chunk.
import { createEVMClient } from '@metamask/connect-evm';

const GENLAYER_CHAIN_ID = '0x107d';
const DEFAULT_GENLAYER_RPC_URL = 'https://rpc.testnet-chain.genlayer.com';

let metaMaskClientPromise = null;

function getDappUrl() {
  if (typeof window === 'undefined') return 'https://portal.genlayer.com';
  return window.location.origin;
}

function getDappIconUrl() {
  if (typeof window === 'undefined') return undefined;
  return `${window.location.origin}/favicon.svg`;
}

function getSupportedNetworks() {
  return {
    [GENLAYER_CHAIN_ID]: import.meta.env.VITE_VALIDATOR_RPC_URL || DEFAULT_GENLAYER_RPC_URL,
  };
}

// The SDK rejects user cancels with shapes the app doesn't recognize:
// 'User closed modal' (QR modal), 'Request rejected' (mobile), or a wrapped
// extension rejection whose outer code is 53 with the raw 4001 in rpcCode.
function isUserRejectionError(error) {
  const message = String(error?.message || '').toLowerCase();
  return (
    error?.code === 4001 ||
    error?.rpcCode === 4001 ||
    message.includes('reject') ||
    message.includes('denied') ||
    message.includes('cancel') ||
    message.includes('closed modal')
  );
}

export async function getMetaMaskConnectClient() {
  if (!metaMaskClientPromise) {
    metaMaskClientPromise = createEVMClient({
      dapp: {
        name: 'GenLayer Portal',
        url: getDappUrl(),
        iconUrl: getDappIconUrl(),
      },
      api: {
        supportedNetworks: getSupportedNetworks(),
      },
      analytics: {
        enabled: false,
      },
      ui: {
        preferExtension: true,
        // Must stay false (SDK default): besides ordering the modal sections,
        // this flag gates connect()'s mobile branch — when true, mobile web
        // gets the desktop QR modal instead of deeplinking into the MetaMask
        // app. Desktop still shows the QR modal either way.
        showInstallModal: false,
      },
      skipAutoAnnounce: true,
    }).catch((error) => {
      metaMaskClientPromise = null;
      throw error;
    });
  }

  return metaMaskClientPromise;
}

export async function getMetaMaskConnectProvider() {
  const client = await getMetaMaskConnectClient();
  try {
    // forceRequest re-prompts even when a persisted session exists, so an
    // explicit MetaMask selection always shows the wallet's account picker
    // (matching the old injected wallet_requestPermissions behavior) instead
    // of silently reconnecting to the previously used account.
    await client.connect({ chainIds: [GENLAYER_CHAIN_ID], forceRequest: true });
  } catch (error) {
    if (isUserRejectionError(error)) {
      // Normalize to the EIP-1193 shape the existing catch logic understands.
      const rejection = new Error('User rejected the request.');
      rejection.code = 4001;
      rejection.cause = error;
      throw rejection;
    }
    throw error;
  }
  const provider = client.getProvider();
  Object.defineProperty(provider, '__genlayerMetaMaskConnect', {
    value: true,
    configurable: true,
  });
  return provider;
}
