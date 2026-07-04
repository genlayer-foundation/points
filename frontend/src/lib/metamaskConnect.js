// MetaMask Connect SDK wrapper. Only ever load this module via dynamic
// import() — a static import would pull the SDK into the entry chunk.
import { createEVMClient } from '@metamask/connect-evm';

const GENLAYER_CHAIN_ID = '0x107d';
const DEFAULT_GENLAYER_RPC_URL = 'https://rpc.testnet-chain.genlayer.com';
const GENLAYER_STUDIO_CHAIN_ID = '0xf22f';
const GENLAYER_STUDIO_RPC_URL = 'https://studio.genlayer.com/api';
// Always granted: the SDK includes mainnet in every permission request as a
// bootstrap fallback, so this scope is a safe last resort for signing.
const MAINNET_CHAIN_ID = '0x1';
const MAINNET_RPC_URL = 'https://cloudflare-eth.com';

let metaMaskClientPromise = null;

function getDappUrl() {
  if (typeof window === 'undefined') return 'https://portal.genlayer.com';
  return window.location.origin;
}

function getDappIconUrl() {
  if (typeof window === 'undefined') return undefined;
  return `${window.location.origin}/favicon.svg`;
}

// The SDK provider rejects EVERY request (personal_sign included) whose
// active chain is not listed here, and the active chain follows the wallet's
// selected network — not just the chain we request. So this must cover the
// networks our users actually sit on, plus mainnet as the universal fallback.
function getSupportedNetworks() {
  return {
    [GENLAYER_CHAIN_ID]: import.meta.env.VITE_VALIDATOR_RPC_URL || DEFAULT_GENLAYER_RPC_URL,
    [GENLAYER_STUDIO_CHAIN_ID]: GENLAYER_STUDIO_RPC_URL,
    [MAINNET_CHAIN_ID]: MAINNET_RPC_URL,
  };
}

// ponytail: users on chains outside this map fall back to the mainnet scope
// for signing; enumerate more networks (or an Infura key) if that ever bites.
function pickSupportedChainId(selectedChainId) {
  const current = String(selectedChainId || '').toLowerCase();
  return getSupportedNetworks()[current] ? current : MAINNET_CHAIN_ID;
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
  // After connect the provider's selected chain is whatever network the
  // wallet is on (e.g. GenLayer Studio, Polygon). If that chain isn't in
  // supportedNetworks, the SDK throws on personal_sign and SIWE login breaks.
  // Pin to a supported chain: keep the wallet's network when we support it,
  // otherwise use mainnet, which the SDK always includes in the session.
  const pinnedChainId = pickSupportedChainId(provider.selectedChainId);
  if (provider.selectedChainId !== pinnedChainId) {
    provider.selectedChainId = pinnedChainId;
  }
  Object.defineProperty(provider, '__genlayerMetaMaskConnect', {
    value: true,
    configurable: true,
  });
  return provider;
}
