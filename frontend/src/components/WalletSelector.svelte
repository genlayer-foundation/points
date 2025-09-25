<script>
  import { onMount } from 'svelte';
  import metamaskLogo from '../assets/wallets/metamask.svg';
  import trustLogo from '../assets/wallets/trust.svg';
  import coinbaseLogo from '../assets/wallets/coinbase.svg';
  import phantomLogo from '../assets/wallets/phantom.svg';
  
  let { 
    isOpen = $bindable(false),
    onSelect = () => {}
  } = $props();
  
  let availableWallets = $state([]);
  let loading = $state(true);
  let detectedProviders = $state(new Map()); // Store providers detected via EIP-6963
  let connectingWallet = $state(null); // Track which wallet is currently connecting
  
  // Constants
  const INSTALL_URLS = {
    phantom: 'https://phantom.app/download',
    metamask: 'https://metamask.io/download/',
    trust: 'https://trustwallet.com/download',
    coinbase: 'https://www.coinbase.com/wallet/downloads'
  };
  
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
               (window.ethereum?._metamask && !window.ethereum?.isPhantom && !window.ethereum?.isTrust) ||
               window.ethereum?.providers?.some(p => p.isMetaMask && !p.isTrust && !p.isPhantom) ||
               (window.ethereum?.isMetaMask && !window.ethereum?.isTrust && !window.ethereum?.isPhantom);
      },
      getProvider: async () => {
        const eip6963 = getEIP6963Provider('metamask');
        if (eip6963) return eip6963;
        
        const provider = findProviderInArray(p => p._metamask && !p.isTrust && !p.isPhantom) ||
                        findProviderInArray(p => p.isMetaMask && !p.isTrust && !p.isPhantom);
        if (provider) return provider;
        
        if (window.ethereum?._metamask && !window.ethereum?.isTrust && !window.ethereum?.isPhantom) {
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
    
    // Request providers to announce themselves
    window.dispatchEvent(new Event('eip6963:requestProvider'));
    
    // Also do traditional detection after a small delay
    setTimeout(() => {
      detectWallets();
    }, 100);
    
    // Cleanup
    return () => {
      window.removeEventListener('eip6963:announceProvider', handleProviderAnnouncement);
    };
  });
  
  function detectWallets() {
    loading = true;
    const wallets = [];
    
    // Always show these wallets in priority order
    const primaryWallets = ['metamask', 'phantom', 'trust', 'coinbase'];
    
    for (const walletId of primaryWallets) {
      const config = walletConfigs[walletId];
      wallets.push({
        id: walletId,
        name: config.name,
        installed: config.checkInstalled(),
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
  
  let connectionAborted = $state(false);
  let connectionController = null;
  let isConnecting = $state(false);
  
  async function selectWallet(wallet) {
    // Prevent double connections
    if (isConnecting) {
      console.log('Connection already in progress');
      return;
    }
    
    if (!wallet.installed) {
      // If wallet not installed, open appropriate installation page
      if (INSTALL_URLS[wallet.id]) {
        window.open(INSTALL_URLS[wallet.id], '_blank');
      }
      return;
    }
    
    // Reset abort flag and set connecting state
    connectionAborted = false;
    connectingWallet = wallet;
    isConnecting = true;
    
    // Create new AbortController for this connection attempt
    connectionController = new AbortController();
    
    try {
      // Get the provider (now async)
      const provider = await wallet.getProvider();
      
      // Check if user aborted
      if (connectionAborted) {
        console.log('Connection aborted by user');
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
        alert(`Could not connect to ${wallet.name}. Please ensure the extension is enabled and try refreshing the page.`);
        return;
      }
      
      // Check again if user aborted before calling onSelect
      if (connectionAborted) {
        console.log('Connection aborted by user');
        return;
      }
      
      // Call onSelect with abort signal support
      const connectionPromise = onSelect(provider, wallet.name);
      
      // Race between connection and abort signal
      await Promise.race([
        connectionPromise,
        new Promise((_, reject) => {
          connectionController.signal.addEventListener('abort', () => {
            reject(new Error('Connection aborted by user'));
          });
        })
      ]);
      // Don't close here - let parent component handle closing after successful connection
    } catch (error) {
      // Check if error is user rejection (MetaMask error code 4001)
      const isUserRejection = error?.code === 4001 || 
                             error?.message?.includes('User rejected') || 
                             error?.message?.includes('User denied');
      
      // Only show error if not aborted and not user rejection
      if (!connectionAborted && !isUserRejection && error?.message !== 'Connection aborted by user') {
        console.error('Wallet connection error:', error);
      }
    } finally {
      // Always clear connecting state
      connectingWallet = null;
      connectionAborted = false;
      connectionController = null;
      isConnecting = false;
    }
  }
  
  function cancelConnection() {
    connectionAborted = true;
    
    // Abort the connection controller if it exists
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
    if (e.key === 'Escape' && !connectingWallet) {
      isOpen = false;
    }
  }
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

{#if isOpen}
  <div 
    class="wallet-selector-backdrop"
    onclick={handleBackdropClick}
    onkeydown={handleKeyDown}
    role="button"
    tabindex="-1"
  >
    <div class="wallet-selector-modal">
      <div class="wallet-selector-header">
        <h2 class="wallet-selector-title">Connect Wallet</h2>
        <button 
          class="wallet-selector-close"
          onclick={() => !connectingWallet && (isOpen = false)}
          disabled={connectingWallet !== null}
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
      
      <div class="wallet-selector-body">
        {#if loading}
          <div class="wallet-selector-loading">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p class="text-gray-500 mt-3">Detecting wallets...</p>
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
              <p class="text-gray-700 mt-4 font-medium">Connecting to {connectingWallet.name}...</p>
              <p class="text-gray-500 text-sm mt-2">Please confirm in your wallet</p>
            </div>
          </div>
        {:else}
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
                <span class="wallet-name">
                  {wallet.name}
                </span>
                {#if !wallet.installed}
                  <span class="wallet-status">Not installed</span>
                {/if}
              </button>
            {/each}
          </div>
          
          <div class="wallet-selector-footer">
            <a 
              href="https://ethereum.org/wallets/find-wallet/" 
              target="_blank" 
              rel="noopener noreferrer"
              class="dont-have-wallet"
            >
              I don't have a wallet
            </a>
          </div>
          
          <div class="wallet-selector-disclaimer">
            By connecting your wallet you agree to the<br>
            <a href="#" class="text-blue-600 hover:underline">Terms of Service</a> and 
            <a href="#" class="text-blue-600 hover:underline">Privacy Policy</a>
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
    background-color: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
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
    background-color: white;
    border-radius: 1rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    width: 420px;
    max-width: 90vw;
    max-height: 85vh;
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
  
  .wallet-selector-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 1.5rem 0;
  }
  
  .wallet-selector-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
    letter-spacing: -0.01em;
  }
  
  .wallet-selector-close {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9CA3AF;
    background: transparent;
    border: none;
    cursor: pointer;
    border-radius: 0.5rem;
    transition: all 0.15s;
  }
  
  .wallet-selector-close:hover:not(:disabled) {
    background-color: #F3F4F6;
    color: #6B7280;
  }
  
  .wallet-selector-close:disabled {
    cursor: not-allowed;
    opacity: 0.3;
    color: #D1D5DB;
  }
  
  .wallet-selector-body {
    padding: 1.5rem;
  }
  
  .wallet-selector-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 2rem;
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
    border-top-color: #2563eb;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  /* Removed unused CSS rules for wallet-selector-empty and wallet-install-link */
  
  .wallet-selector-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .wallet-option {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.875rem 1rem;
    background-color: #FAFAFA;
    border: 1px solid #E5E7EB;
    border-radius: 0.75rem;
    cursor: pointer;
    transition: all 0.15s;
    text-align: left;
  }
  
  .wallet-option:hover {
    background-color: #F9FAFB;
    border-color: #D1D5DB;
    transform: translateX(2px);
  }
  
  .wallet-icon-wrapper {
    width: 40px;
    height: 40px;
    margin-right: 0.875rem;
    flex-shrink: 0;
  }
  
  .wallet-icon {
    width: 100%;
    height: 100%;
    border-radius: 0.5rem;
    object-fit: contain;
  }
  
  .wallet-name {
    font-size: 0.9375rem;
    font-weight: 500;
    color: #111827;
    letter-spacing: -0.01em;
    flex: 1;
    text-align: left;
  }
  
  .wallet-status {
    font-size: 0.75rem;
    color: #9CA3AF;
    font-weight: 400;
  }
  
  .wallet-option.wallet-not-installed {
    opacity: 0.7;
  }
  
  .wallet-option.wallet-not-installed:hover {
    opacity: 1;
  }
  
  .wallet-selector-footer {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #F3F4F6;
    text-align: center;
  }
  
  .dont-have-wallet {
    color: #6B7280;
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    transition: color 0.15s;
  }
  
  .dont-have-wallet:hover {
    color: #2563EB;
  }
  
  .wallet-selector-disclaimer {
    margin-top: 1rem;
    padding-top: 1rem;
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
    
    .wallet-selector-header {
      padding: 1.25rem 1.25rem 0;
    }
    
    .wallet-selector-body {
      padding: 1.25rem;
    }
  }
</style>