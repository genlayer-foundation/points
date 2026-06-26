<script>
  import { onMount } from 'svelte';
  import metamaskLogo from '../assets/wallets/metamask.svg';
  import trustLogo from '../assets/wallets/trust.svg';
  import coinbaseLogo from '../assets/wallets/coinbase.svg';
  import phantomLogo from '../assets/wallets/phantom.svg';
  import { showError } from '../lib/toastStore';

  let {
    isOpen = $bindable(false),
    onSelect = () => {}
  } = $props();
  
  let availableWallets = $state([]);
  let loading = $state(true);
  let detectedProviders = $state(new Map()); // Store providers detected via EIP-6963
  let connectingWallet = $state(null); // Track which wallet is currently connecting
  let installedWalletCount = $derived(availableWallets.filter((wallet) => wallet.installed).length);
  let portalEl = $state(null);
  
  // Constants
  const INSTALL_URLS = {
    phantom: 'https://phantom.app/download',
    metamask: 'https://metamask.io/download/',
    trust: 'https://trustwallet.com/download',
    coinbase: 'https://www.coinbase.com/wallet/downloads'
  };

  function isMobileBrowser() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera || '';
    return /android|iphone|ipad|ipod/i.test(userAgent);
  }

  function getCurrentDappUrl() {
    return `${window.location.origin}${window.location.pathname}${window.location.search}${window.location.hash}`;
  }

  function getMobileDeepLink(walletId) {
    const dappUrl = getCurrentDappUrl();

    if (walletId === 'metamask') {
      // Append host + path + search + hash literally — encoding the `/`, `?`,
      // and `#` causes the in-app browser to open with a blank tab.
      const dappPath = `${window.location.host}${window.location.pathname}${window.location.search}${window.location.hash}`;
      return `https://link.metamask.io/dapp/${dappPath}`;
    }

    if (walletId === 'phantom') {
      return `https://phantom.app/ul/browse/${encodeURIComponent(dappUrl)}?ref=${encodeURIComponent(window.location.origin)}`;
    }

    if (walletId === 'trust') {
      return `https://link.trustwallet.com/open_url?coin_id=60&url=${encodeURIComponent(dappUrl)}`;
    }

    if (walletId === 'coinbase') {
      return `https://go.cb-w.com/dapp?cb_url=${encodeURIComponent(dappUrl)}`;
    }

    return null;
  }
  
  const WALLET_LOGOS = {
    phantom: phantomLogo,
    metamask: metamaskLogo,
    trust: trustLogo,
    coinbase: coinbaseLogo
  };
  
  // Helper function to get EIP-6963 provider
  function getEIP6963Provider(walletId) {
    const provider = detectedProviders.get(walletId);
    if (provider?.provider) {
      return provider.provider;
    }
    return null;
  }
  
  // Helper function to check provider in array
  function findProviderInArray(checkFn) {
    if (window.ethereum?.providers?.length) {
      return window.ethereum.providers.find(checkFn);
    }
    return null;
  }
  
  // Wallet configurations with SVG icons
  const walletConfigs = {
    phantom: {
      name: 'Phantom',
      checkInstalled: () => {
        return detectedProviders.has('phantom') ||
               window.phantom?.ethereum ||
               window.ethereum?.providers?.some(p => p.isPhantom) ||
               window.ethereum?.isPhantom === true;
      },
      getProvider: async () => {
        return getEIP6963Provider('phantom') ||
               window.phantom?.ethereum ||
               findProviderInArray(p => p.isPhantom) ||
               (window.ethereum?.isPhantom ? window.ethereum : null);
      }
    },
    metamask: {
      name: 'MetaMask',
      checkInstalled: () => {
        return detectedProviders.has('metamask') ||
               window.ethereum?.providers?.some(p => p.isMetaMask && !p.isTrust && !p.isPhantom) ||
               (window.ethereum?.isMetaMask && !window.ethereum?.isTrust && !window.ethereum?.isPhantom);
      },
      getProvider: async () => {
        const eip6963 = getEIP6963Provider('metamask');
        if (eip6963) return eip6963;
        
        const provider = findProviderInArray(p => p.isMetaMask && !p.isTrust && !p.isPhantom);
        if (provider) return provider;

        if (window.ethereum?.isMetaMask && !window.ethereum?.isTrust && !window.ethereum?.isPhantom) {
          return window.ethereum;
        }
        
        if (window.ethereum?.isMetaMask && (window.ethereum?.isTrust || window.ethereum?.isPhantom)) {
          return 'conflict';
        }
        
        return null;
      }
    },
    trust: {
      name: 'Trust Wallet', 
      checkInstalled: () => {
        return detectedProviders.has('trust') ||
               window.ethereum?.providers?.some(p => p.isTrust || p.isTrustWallet) ||
               window.ethereum?.isTrust ||
               window.ethereum?.isTrustWallet ||
               window.trustwallet !== undefined;
      },
      getProvider: async () => {
        return getEIP6963Provider('trust') ||
               findProviderInArray(p => p.isTrust || p.isTrustWallet) ||
               window.trustwallet ||
               ((window.ethereum?.isTrust || window.ethereum?.isTrustWallet) ? window.ethereum : null);
      }
    },
    coinbase: {
      name: 'Coinbase Wallet',
      checkInstalled: () => {
        return detectedProviders.has('coinbase') ||
               window.ethereum?.providers?.some(p => p.isCoinbaseWallet) ||
               window.ethereum?.isCoinbaseWallet === true;
      },
      getProvider: async () => {
        return getEIP6963Provider('coinbase') ||
               findProviderInArray(p => p.isCoinbaseWallet) ||
               (window.ethereum?.isCoinbaseWallet ? window.ethereum : null);
      }
    },
  };
  
  onMount(() => {
    // Set up EIP-6963 listener for wallet detection
    function handleProviderAnnouncement(event) {
      const providerDetail = event.detail;
      const provider = providerDetail?.provider;
      const info = providerDetail?.info;
      
      
      if (!provider) return;
      
      // Store provider with its info - be more specific about detection
      if (provider.isPhantom) {
        detectedProviders.set('phantom', { provider, info });
      } else if (provider.isMetaMask && !provider.isTrust && !provider.isTrustWallet && !provider.isPhantom) {
        detectedProviders.set('metamask', { provider, info });
      } else if (provider.isTrust || provider.isTrustWallet) {
        detectedProviders.set('trust', { provider, info });
      } else if (provider.isCoinbaseWallet) {
        detectedProviders.set('coinbase', { provider, info });
      }
      
      // Re-detect wallets after provider announcement
      detectWallets();
    }
    
    // Listen for wallet announcements
    window.addEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    window.addEventListener('ethereum#initialized', detectWallets, { once: true });
    
    // Request providers to announce themselves
    window.dispatchEvent(new Event('eip6963:requestProvider'));
    
    // Also do traditional detection after a small delay
    setTimeout(() => {
      detectWallets();
    }, 100);

    // MetaMask Mobile may inject the provider later than extension wallets.
    setTimeout(() => {
      detectWallets();
    }, 3000);
    
    // Cleanup
    return () => {
      window.removeEventListener('eip6963:announceProvider', handleProviderAnnouncement);
      window.removeEventListener('ethereum#initialized', detectWallets);
    };
  });

  function detectWallets() {
    loading = true;
    const wallets = [];
    
    // Always show these wallets in priority order
    const primaryWallets = ['metamask', 'phantom', 'trust', 'coinbase'];
    
    for (const walletId of primaryWallets) {
      const config = walletConfigs[walletId];
      const installed = Boolean(config.checkInstalled());
      wallets.push({
        id: walletId,
        name: config.name,
        installed,
        mobileDeepLink: isMobileBrowser() && !installed ? getMobileDeepLink(walletId) : null,
        getProvider: config.getProvider
      });
    }
    
    // Add "Other Wallets" option if ethereum is available but not from primary wallets
    if (window.ethereum) {
      const hasOtherWallet = !walletConfigs.metamask.checkInstalled() && 
                            !walletConfigs.trust.checkInstalled() && 
                            !walletConfigs.coinbase.checkInstalled();
      
      if (hasOtherWallet) {
        wallets.push({
          id: 'other',
          name: 'Other Wallets',
          installed: true,
          getProvider: () => window.ethereum
        });
      }
    }
    
    availableWallets = wallets;
    loading = false;
  }
  
  let connectionDismissed = $state(false);
  let connectionController = null;
  let isConnecting = $state(false);
  
  async function selectWallet(wallet) {
    // Prevent double connections
    if (isConnecting) {
      return;
    }
    
    if (!wallet.installed) {
      if (wallet.mobileDeepLink) {
        window.location.href = wallet.mobileDeepLink;
        return;
      }

      // If wallet not installed, open appropriate installation page
      if (INSTALL_URLS[wallet.id]) {
        window.open(INSTALL_URLS[wallet.id], '_blank');
      }
      return;
    }
    
    // Reset dismiss flag and set connecting state
    connectionDismissed = false;
    connectingWallet = wallet;
    isConnecting = true;
    
    // Create new AbortController for this connection attempt
    connectionController = new AbortController();
    
    try {
      // Get the provider (now async)
      const provider = await wallet.getProvider();

      // Check if user dismissed the local connection view
      if (connectionDismissed) {
        return;
      }
      
      // Handle special conflict case for MetaMask
      if (provider === 'conflict' && wallet.id === 'metamask') {
        connectingWallet = null; // Clear connecting state
        
        // Trust Wallet is hijacking the connection
        const response = confirm(
          'Trust Wallet is interfering with MetaMask connection.\n\n' +
          'To use MetaMask, you have two options:\n' +
          '1. Click OK to try anyway (may connect to Trust Wallet instead)\n' +
          '2. Click Cancel, then disable Trust Wallet extension and refresh the page\n\n' +
          'Continue anyway?'
        );
        
        if (response) {
          connectingWallet = wallet; // Set connecting state again
          // Try with the conflicted provider
          await onSelect(window.ethereum, wallet.name);
          // Don't close here - let parent component handle it
        }
        return;
      }
      
      if (!provider) {
        showError(`Could not connect to ${wallet.name}. Please ensure the extension is enabled and try refreshing the page.`);
        return;
      }
      
      // Check again if user dismissed before calling onSelect
      if (connectionDismissed) {
        return;
      }
      
      // Call onSelect with abort signal support
      const connectionPromise = onSelect(provider, wallet.name);
      
      // Race between connection and local UI dismissal. This does not cancel
      // wallet-provider work already started by onSelect.
      await Promise.race([
        connectionPromise,
        new Promise((_, reject) => {
          connectionController.signal.addEventListener('abort', () => {
            reject(new Error('Connection view closed by user'));
          });
        })
      ]);
      // Don't close here - let parent component handle closing after successful connection
    } catch (error) {
      // Check if error is user rejection (MetaMask error code 4001)
      const isUserRejection = error?.code === 4001 || 
                             error?.message?.includes('User rejected') || 
                             error?.message?.includes('User denied');
      
      // Only show error if not dismissed and not user rejection
      if (!connectionDismissed && !isUserRejection && error?.message !== 'Connection view closed by user') {
        showError('Failed to connect wallet. Please try again.');
      }
    } finally {
      // Always clear connecting state
      connectingWallet = null;
      connectionDismissed = false;
      connectionController = null;
      isConnecting = false;
    }
  }
  
  function closeConnectionView() {
    connectionDismissed = true;

    // Stop the local loading race if it exists. Provider prompts may continue.
    if (connectionController) {
      connectionController.abort();
    }

    connectingWallet = null;
    isConnecting = false;
    isOpen = false;
  }

  function handleBackdropClick(e) {
    // Don't close if currently connecting
    if (e.target === e.currentTarget && !connectingWallet) {
      isOpen = false;
    }
  }

  function handleKeyDown(e) {
    // Don't close if currently connecting
    if (isOpen && e.key === 'Escape' && !connectingWallet) {
      isOpen = false;
    }
  }

  $effect(() => {
    if (!isOpen || !portalEl || typeof document === 'undefined') return;

    const node = portalEl;
    const originalParent = node.parentNode;
    const marker = document.createComment('wallet-selector-portal');
    originalParent?.insertBefore(marker, node);
    document.body.appendChild(node);

    return () => {
      if (marker.parentNode && node.parentNode) {
        marker.parentNode.insertBefore(node, marker);
      }
      marker.remove();
    };
  });
</script>

{#snippet walletIcon(walletId)}
  {#if WALLET_LOGOS[walletId]}
    <img src={WALLET_LOGOS[walletId]} alt={walletConfigs[walletId]?.name || walletId} class="wallet-icon" />
  {:else}
    <svg class="wallet-icon" width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="40" rx="8" fill="#F3F4F6"/>
      <rect x="12" y="12" width="6" height="6" rx="1" fill="#9CA3AF"/>
      <rect x="22" y="12" width="6" height="6" rx="1" fill="#9CA3AF"/>
      <rect x="12" y="22" width="6" height="6" rx="1" fill="#9CA3AF"/>
      <rect x="22" y="22" width="6" height="6" rx="1" fill="#9CA3AF"/>
    </svg>
  {/if}
{/snippet}

{#snippet genlayerHexMark()}
  <svg class="genlayer-hex-mark" viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M21.75 2.304c1.393-.804 3.107-.804 4.5 0l15.535 8.968c1.393.804 2.25 2.29 2.25 3.897v17.937c0 1.607-.857 3.092-2.25 3.897L26.25 45.971c-1.393.804-3.107.804-4.5 0L6.215 37.003c-1.393-.805-2.25-2.29-2.25-3.897V15.169c0-1.607.857-3.093 2.25-3.897L21.75 2.304Z" fill="#131214" />
    <g transform="translate(10.75 8.5) scale(0.78)" fill="#fff">
      <path d="M15.4065 11.2607L9.64908 23.3639L15.0689 26.072L0 32L15.4065 0V11.2607Z" />
      <path d="M18.6229 11.2607L24.3803 23.3639L18.9605 26.072L34.0294 32L18.6229 0V11.2607Z" />
      <path d="M16.9311 15.2394L20.3041 21.9088L16.9311 23.5623L13.7392 21.9019L16.9311 15.2394Z" />
    </g>
  </svg>
{/snippet}

<svelte:window onkeydown={handleKeyDown} />

{#if isOpen}
  <div
    bind:this={portalEl}
    class="wallet-selector-backdrop"
    onclick={handleBackdropClick}
    role="presentation"
  >
    <div class="wallet-selector-modal" role="dialog" aria-modal="true" aria-labelledby="wallet-selector-title">
      <div class="wallet-selector-hero">
        <div class="wallet-hero-copy">
          <div class="wallet-kicker">
            <span class="wallet-hero-mark" aria-hidden="true">
              {@render genlayerHexMark()}
            </span>
            <span>GenLayer Portal</span>
          </div>
          <h2 id="wallet-selector-title" class="wallet-selector-title">Connect wallet</h2>
          <p>Select a wallet to continue into the Portal.</p>
        </div>
        <button
          class="wallet-selector-close"
          onclick={() => {
            if (!connectingWallet) {
              isOpen = false;
            }
          }}
          disabled={connectingWallet !== null}
          aria-label="Close"
        >
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <div class="wallet-selector-body">
        {#if loading}
          <div class="wallet-selector-loading">
            <div class="loading-orbit" aria-hidden="true">
              <img src="/assets/icons/hexagon-genlayer.svg" alt="" />
            </div>
            <p>Detecting wallets...</p>
          </div>
        {:else if connectingWallet}
          <div class="wallet-selector-loading">
            <div class="connecting-wallet-container">
              <div class="connecting-wallet-logo">
                <div class="connecting-logo">
                  {@render walletIcon(connectingWallet.id)}
                </div>
                <div class="connecting-spinner"></div>
              </div>
              <p class="connecting-title">Connecting to {connectingWallet.name}...</p>
              <p class="connecting-copy">Confirm the signature request in your wallet.</p>
              <button type="button" class="cancel-connect" onclick={closeConnectionView}>
                Close
              </button>
            </div>
          </div>
        {:else}
          <div class="wallet-summary" aria-live="polite">
            <span>{availableWallets.length} wallets checked</span>
            <span>{installedWalletCount} detected</span>
          </div>
          <div class="wallet-selector-list">
            {#each availableWallets as wallet}
              <button
                class="wallet-option {!wallet.installed ? 'wallet-not-installed' : ''}"
                onclick={() => selectWallet(wallet)}
                disabled={connectingWallet !== null}
              >
                <div class="wallet-icon-wrapper">
                  {@render walletIcon(wallet.id)}
                </div>
                <span class="wallet-copy">
                  <span class="wallet-name">
                    {wallet.name}
                  </span>
                  <span class="wallet-help">
                    {wallet.installed ? 'Ready in this browser' : wallet.mobileDeepLink ? 'Open the mobile wallet app' : 'Install to continue'}
                  </span>
                </span>
                <span class="wallet-status" class:wallet-status-ready={wallet.installed}>
                  {wallet.installed ? 'Detected' : wallet.mobileDeepLink ? 'Open app' : 'Install'}
                </span>
                <svg class="wallet-chevron" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="m7.5 4.5 5 5.5-5 5.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
            {/each}
          </div>
          
          <div class="wallet-selector-disclaimer">
            By connecting your wallet you agree to the
            <a href="/terms-of-use" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">Terms of Use</a> and
            <a href="/privacy-policy" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline">Privacy Policy</a>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .wallet-selector-backdrop {
    position: fixed;
    inset: 0;
    background:
      radial-gradient(circle at 18% 12%, rgba(238, 133, 33, 0.24), transparent 24rem),
      radial-gradient(circle at 80% 18%, rgba(56, 125, 232, 0.2), transparent 24rem),
      radial-gradient(circle at 50% 84%, rgba(127, 82, 225, 0.22), transparent 24rem),
      rgba(14, 14, 16, 0.54);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    animation: fadeIn 0.15s ease-out;
    backdrop-filter: blur(4px);
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  
  .wallet-selector-modal {
    background: #fff;
    border: 1px solid rgba(19, 18, 20, 0.08);
    border-radius: 16px;
    box-shadow:
      0 34px 70px rgba(15, 15, 15, 0.22),
      0 1px 0 rgba(255, 255, 255, 0.85) inset;
    width: 460px;
    max-width: 90vw;
    max-height: min(88vh, 760px);
    overflow: hidden;
    animation: slideUp 0.2s ease-out;
  }
  
  @keyframes slideUp {
    from {
      transform: translateY(10px);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }
  
  .wallet-selector-hero {
    align-items: flex-start;
    background: #ffffff;
    color: #131214;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 24px;
    position: relative;
    overflow: hidden;
  }

  .wallet-selector-hero::before {
    background:
      linear-gradient(90deg,
        rgba(238, 133, 33, 0.34) 0%,
        rgba(255, 230, 132, 0.28) 18%,
        rgba(95, 213, 165, 0.3) 38%,
        rgba(91, 190, 238, 0.3) 58%,
        rgba(151, 132, 238, 0.28) 78%,
        rgba(245, 151, 194, 0.3) 100%
      );
    content: '';
    filter: blur(18px);
    height: 112px;
    left: -20px;
    opacity: 0.95;
    position: absolute;
    right: -20px;
    top: 46%;
    transform: translateY(-50%);
  }

  .wallet-selector-hero::after {
    background: linear-gradient(180deg, transparent, rgba(255, 255, 255, 0.36));
    bottom: 0;
    content: '';
    height: 42px;
    left: 0;
    pointer-events: none;
    position: absolute;
    right: 0;
  }

  .wallet-hero-copy {
    min-width: 0;
    position: relative;
    z-index: 1;
  }

  .wallet-selector-close {
    position: relative;
    z-index: 1;
  }

  .wallet-kicker {
    align-items: center;
    color: #5d5d64;
    display: flex;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 700;
    gap: 10px;
    letter-spacing: 0;
    margin-bottom: 14px;
    text-transform: uppercase;
  }

  .wallet-hero-mark {
    align-items: center;
    background: rgba(255, 255, 255, 0.74);
    border: 1px solid rgba(255, 255, 255, 0.92);
    border-radius: 14px;
    box-shadow: 0 12px 26px rgba(19, 18, 20, 0.1);
    display: inline-flex;
    height: 42px;
    justify-content: center;
    width: 42px;
  }

  .genlayer-hex-mark {
    display: block;
    height: 34px;
    width: 34px;
  }

  .wallet-selector-title {
    color: #131214;
    font-family: var(--font-heading);
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1.12;
    margin: 0;
    text-wrap: balance;
  }

  .wallet-selector-hero p {
    color: #606068;
    font-size: 14px;
    line-height: 1.5;
    margin: 9px 0 0;
    text-wrap: pretty;
  }
  
  .wallet-selector-close {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #5f6068;
    background: rgba(255, 255, 255, 0.66);
    border: 1px solid rgba(19, 18, 20, 0.08);
    cursor: pointer;
    border-radius: 999px;
    flex: 0 0 auto;
    transition-duration: 160ms;
    transition-property: background-color, color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .wallet-selector-close svg {
    height: 20px;
    width: 20px;
  }
  
  .wallet-selector-close:hover:not(:disabled) {
    background-color: #fff;
    color: #131214;
    box-shadow: 0 10px 22px rgba(19, 18, 20, 0.08);
  }

  .wallet-selector-close:active:not(:disabled) {
    transform: scale(0.96);
  }
  
  .wallet-selector-close:disabled {
    cursor: default;
    opacity: 0.3;
    color: #D1D5DB;
  }
  
  .wallet-selector-body {
    padding: 20px;
  }
  
  .wallet-selector-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 270px;
    padding: 38px 24px;
    text-align: center;
  }

  .wallet-selector-loading p {
    color: #6f6f75;
    font-size: 14px;
    line-height: 1.45;
    margin: 14px 0 0;
  }

  .loading-orbit {
    align-items: center;
    display: flex;
    height: 70px;
    justify-content: center;
    position: relative;
    width: 70px;
  }

  .loading-orbit::before {
    animation: spin 1s linear infinite;
    border: 2px solid #e9e9ec;
    border-top-color: #131214;
    border-radius: 999px;
    content: '';
    inset: 0;
    position: absolute;
  }

  .loading-orbit img {
    height: 42px;
    width: 38px;
  }
  
  .connecting-wallet-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
  
  .connecting-wallet-logo {
    position: relative;
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .connecting-logo {
    width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .connecting-logo .wallet-icon {
    width: 60px;
    height: 60px;
  }
  
  .connecting-spinner {
    position: absolute;
    inset: -8px;
    border: 3px solid #e5e7eb;
    border-top-color: #131214;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .connecting-title {
    color: #131214 !important;
    font-size: 15px !important;
    font-weight: 800;
    margin-top: 18px !important;
  }

  .connecting-copy {
    margin-top: 6px !important;
  }

  .cancel-connect {
    background: #f4f4f5;
    border: 1px solid #e8e8ea;
    border-radius: 999px;
    color: #414145;
    cursor: pointer;
    font-size: 13px;
    font-weight: 700;
    height: 38px;
    margin-top: 18px;
    padding: 0 16px;
    transition-duration: 160ms;
    transition-property: background-color, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .cancel-connect:hover {
    background: #ededee;
  }

  .cancel-connect:active {
    transform: scale(0.96);
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .wallet-summary {
    align-items: center;
    color: #75757a;
    display: flex;
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    justify-content: space-between;
    letter-spacing: 0;
    margin-bottom: 10px;
    text-transform: uppercase;
  }
  
  .wallet-selector-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .wallet-option {
    display: flex;
    align-items: center;
    width: 100%;
    min-height: 64px;
    padding: 10px 12px;
    background:
      linear-gradient(180deg, rgba(19, 18, 20, 0.02), rgba(255, 255, 255, 0)),
      #fff;
    border: 1px solid #ededed;
    border-radius: 8px;
    cursor: pointer;
    gap: 12px;
    text-align: left;
    transition-duration: 160ms;
    transition-property: background-color, border-color, box-shadow, opacity, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }
  
  .wallet-option:hover {
    background-color: #fafafa;
    border-color: #d8d8dc;
    box-shadow: 0 14px 28px rgba(19, 18, 20, 0.08);
    transform: translateY(-1px);
  }

  .wallet-option:active {
    transform: scale(0.96);
  }
  
  .wallet-icon-wrapper {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
  }
  
  .wallet-icon {
    width: 100%;
    height: 100%;
    border-radius: 0.5rem;
    object-fit: contain;
  }

  .wallet-copy {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
  }
  
  .wallet-name {
    font-size: 0.9375rem;
    font-weight: 800;
    color: #111827;
    letter-spacing: 0;
    text-align: left;
  }

  .wallet-help {
    color: #76767c;
    font-size: 12px;
    line-height: 1.35;
    margin-top: 2px;
  }
  
  .wallet-status {
    background: #f4f4f5;
    border-radius: 999px;
    color: #76767c;
    flex: 0 0 auto;
    font-size: 11px;
    font-weight: 800;
    padding: 5px 8px;
  }

  .wallet-status-ready {
    background: #ebf8f0;
    color: #16894d;
  }

  .wallet-chevron {
    color: #a5a5aa;
    flex: 0 0 auto;
    height: 18px;
    width: 18px;
  }
  
  .wallet-option.wallet-not-installed {
    opacity: 0.7;
  }
  
  .wallet-option.wallet-not-installed:hover {
    opacity: 1;
  }
  
  .wallet-selector-disclaimer {
    border-top: 1px solid #f0f0f2;
    margin-top: 14px;
    padding-top: 14px;
    text-align: center;
    font-size: 0.75rem;
    color: #9CA3AF;
    line-height: 1.5;
  }

  /* Responsive design */
  @media (max-width: 640px) {
    .wallet-selector-modal {
      width: calc(100vw - 2rem);
      max-height: 90vh;
    }
    
    .wallet-selector-hero {
      padding: 20px;
    }
    
    .wallet-selector-body {
      padding: 16px;
    }

    .wallet-option {
      align-items: flex-start;
      min-height: 70px;
    }

    .wallet-status {
      display: none;
    }
  }
</style>
