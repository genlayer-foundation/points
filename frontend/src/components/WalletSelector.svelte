<script>
  import { onMount } from 'svelte';
  import metamaskLogo from '../assets/wallets/metamask.svg';
  import trustLogo from '../assets/wallets/trust.svg';
  import coinbaseLogo from '../assets/wallets/coinbase.svg';
  
  let { 
    isOpen = $bindable(false),
    onSelect = () => {}
  } = $props();
  
  let availableWallets = $state([]);
  let loading = $state(true);
  let detectedProviders = $state(new Map()); // Store providers detected via EIP-6963
  
  // Wallet configurations with SVG icons
  const walletConfigs = {
    metamask: {
      name: 'MetaMask',
      checkInstalled: () => {
        // First check EIP-6963 detected providers
        if (detectedProviders.has('metamask')) {
          return true;
        }
        // Fallback to traditional detection
        if (window.ethereum?._metamask) {
          return true;
        }
        if (window.ethereum?.providers?.length) {
          return window.ethereum.providers.some(p => p.isMetaMask === true && !p.isTrust);
        }
        return window.ethereum?.isMetaMask === true && !window.ethereum?.isTrust;
      },
      getProvider: async () => {
        // Priority 1: Use EIP-6963 detected MetaMask provider
        const eip6963Provider = detectedProviders.get('metamask');
        if (eip6963Provider?.provider) {
          console.log('Using EIP-6963 detected MetaMask provider');
          return eip6963Provider.provider;
        }
        
        // Priority 2: Check for providers array with real MetaMask
        if (window.ethereum?.providers?.length) {
          const realMetamask = window.ethereum.providers.find(p => p._metamask && !p.isTrust);
          if (realMetamask) return realMetamask;
          
          const metamaskProvider = window.ethereum.providers.find(p => p.isMetaMask === true && !p.isTrust);
          if (metamaskProvider) return metamaskProvider;
        }
        
        // Priority 3: If window.ethereum has _metamask object and not Trust
        if (window.ethereum?._metamask && !window.ethereum?.isTrust) {
          return window.ethereum;
        }
        
        // Priority 4: Conflict case
        if (window.ethereum?.isMetaMask && window.ethereum?.isTrust) {
          return 'conflict';
        }
        
        return null;
      }
    },
    trust: {
      name: 'Trust Wallet', 
      checkInstalled: () => {
        // First check EIP-6963 detected providers
        if (detectedProviders.has('trust')) {
          return true;
        }
        // Fallback to traditional detection
        if (window.ethereum?.providers?.length) {
          return window.ethereum.providers.some(p => p.isTrust === true || p.isTrustWallet === true);
        }
        return window.ethereum?.isTrust === true || window.ethereum?.isTrustWallet === true || window.trustwallet !== undefined;
      },
      getProvider: async () => {
        // Priority 1: Use EIP-6963 detected Trust provider
        const eip6963Provider = detectedProviders.get('trust');
        if (eip6963Provider?.provider) {
          console.log('Using EIP-6963 detected Trust Wallet provider');
          return eip6963Provider.provider;
        }
        
        // Priority 2: Check providers array
        if (window.ethereum?.providers?.length) {
          const trustProvider = window.ethereum.providers.find(p => p.isTrust === true || p.isTrustWallet === true);
          if (trustProvider) return trustProvider;
        }
        
        // Priority 3: Standalone Trust Wallet object
        if (window.trustwallet) {
          return window.trustwallet;
        }
        
        // Priority 4: If window.ethereum is Trust Wallet
        if (window.ethereum?.isTrust === true || window.ethereum?.isTrustWallet === true) {
          return window.ethereum;
        }
        
        return null;
      }
    },
    coinbase: {
      name: 'Coinbase Wallet',
      checkInstalled: () => {
        // First check EIP-6963 detected providers
        if (detectedProviders.has('coinbase')) {
          return true;
        }
        // Fallback to traditional detection
        if (window.ethereum?.providers?.length) {
          return window.ethereum.providers.some(p => p.isCoinbaseWallet === true);
        }
        return window.ethereum?.isCoinbaseWallet === true;
      },
      getProvider: async () => {
        // Priority 1: Use EIP-6963 detected Coinbase provider
        const eip6963Provider = detectedProviders.get('coinbase');
        if (eip6963Provider?.provider) {
          console.log('Using EIP-6963 detected Coinbase Wallet provider');
          return eip6963Provider.provider;
        }
        
        // Priority 2: Check providers array
        if (window.ethereum?.providers?.length) {
          const coinbaseProvider = window.ethereum.providers.find(p => p.isCoinbaseWallet === true);
          if (coinbaseProvider) return coinbaseProvider;
        }
        
        // Priority 3: Direct window.ethereum
        if (window.ethereum?.isCoinbaseWallet === true) {
          return window.ethereum;
        }
        
        return null;
      }
    },
  };
  
  onMount(() => {
    // Set up EIP-6963 listener for wallet detection
    function handleProviderAnnouncement(event) {
      const providerDetail = event.detail;
      const provider = providerDetail?.provider;
      const info = providerDetail?.info;
      
      console.log('EIP-6963 Provider announced:', {
        name: info?.name,
        uuid: info?.uuid,
        isMetaMask: provider?.isMetaMask,
        isTrust: provider?.isTrust,
        isTrustWallet: provider?.isTrustWallet,
        hasTrustWallet: !!provider?.isTrust || !!provider?.isTrustWallet
      });
      
      if (!provider) return;
      
      // Store provider with its info - be more specific about detection
      if (provider.isMetaMask && !provider.isTrust && !provider.isTrustWallet) {
        console.log('Detected real MetaMask via EIP-6963');
        detectedProviders.set('metamask', { provider, info });
      } else if (provider.isTrust || provider.isTrustWallet) {
        console.log('Detected Trust Wallet via EIP-6963');
        detectedProviders.set('trust', { provider, info });
      } else if (provider.isCoinbaseWallet) {
        console.log('Detected Coinbase Wallet via EIP-6963');
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
    
    // Always show these three wallets
    const primaryWallets = ['metamask', 'trust', 'coinbase'];
    
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
  
  async function selectWallet(wallet) {
    if (!wallet.installed) {
      // If wallet not installed, open appropriate installation page
      const installUrls = {
        metamask: 'https://metamask.io/download/',
        trust: 'https://trustwallet.com/download',
        coinbase: 'https://www.coinbase.com/wallet/downloads'
      };
      
      if (installUrls[wallet.id]) {
        window.open(installUrls[wallet.id], '_blank');
      }
      return;
    }
    
    // Get the provider (now async)
    const provider = await wallet.getProvider();
    
    // Handle special conflict case for MetaMask
    if (provider === 'conflict' && wallet.id === 'metamask') {
      // Trust Wallet is hijacking the connection
      const response = confirm(
        'Trust Wallet is interfering with MetaMask connection.\n\n' +
        'To use MetaMask, you have two options:\n' +
        '1. Click OK to try anyway (may connect to Trust Wallet instead)\n' +
        '2. Click Cancel, then disable Trust Wallet extension and refresh the page\n\n' +
        'Continue anyway?'
      );
      
      if (response) {
        // Try with the conflicted provider
        onSelect(window.ethereum, wallet.name);
        isOpen = false;
      }
      return;
    }
    
    if (!provider) {
      alert(`Could not connect to ${wallet.name}. Please ensure the extension is enabled and try refreshing the page.`);
      return;
    }
    
    onSelect(provider, wallet.name);
    isOpen = false;
  }
  
  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      isOpen = false;
    }
  }
  
  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      isOpen = false;
    }
  }
</script>

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
          onclick={() => isOpen = false}
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
        {:else}
          <div class="wallet-selector-list">
            {#each availableWallets as wallet}
              <button
                class="wallet-option {!wallet.installed ? 'wallet-not-installed' : ''}"
                onclick={() => selectWallet(wallet)}
              >
                <div class="wallet-icon-wrapper">
                  {#if wallet.id === 'metamask'}
                    <img src={metamaskLogo} alt="MetaMask" class="wallet-icon" />
                  {:else if wallet.id === 'trust'}
                    <img src={trustLogo} alt="Trust Wallet" class="wallet-icon" />
                  {:else if wallet.id === 'coinbase'}
                    <img src={coinbaseLogo} alt="Coinbase Wallet" class="wallet-icon" />
                  {:else}
                    <svg class="wallet-icon" width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <rect width="40" height="40" rx="8" fill="#F3F4F6"/>
                      <rect x="12" y="12" width="6" height="6" rx="1" fill="#9CA3AF"/>
                      <rect x="22" y="12" width="6" height="6" rx="1" fill="#9CA3AF"/>
                      <rect x="12" y="22" width="6" height="6" rx="1" fill="#9CA3AF"/>
                      <rect x="22" y="22" width="6" height="6" rx="1" fill="#9CA3AF"/>
                    </svg>
                  {/if}
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
  
  .wallet-selector-close:hover {
    background-color: #F3F4F6;
    color: #6B7280;
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
  
  .wallet-selector-empty {
    text-align: center;
    padding: 3rem 2rem;
  }
  
  .wallet-install-link {
    display: inline-block;
    padding: 0.625rem 1.25rem;
    background-color: #2563EB;
    color: white;
    border-radius: 0.5rem;
    text-decoration: none;
    font-weight: 500;
    font-size: 0.875rem;
    transition: all 0.15s;
  }
  
  .wallet-install-link:hover {
    background-color: #1D4ED8;
    transform: translateY(-1px);
  }
  
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
  
  .wallet-option.wallet-not-installed .wallet-status {
    color: #6B7280;
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