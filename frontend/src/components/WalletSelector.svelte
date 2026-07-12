<script>
  import { onMount } from 'svelte';
  import metamaskLogo from '../assets/wallets/metamask.svg';
  import rabbyLogo from '../assets/wallets/rabby.svg';
  import okxLogo from '../assets/wallets/okx.svg';
  import trustLogo from '../assets/wallets/trust.svg';
  import coinbaseLogo from '../assets/wallets/coinbase.svg';
  import phantomLogo from '../assets/wallets/phantom.svg';
  import { showError } from '../lib/toastStore';

  let {
    isOpen = $bindable(false),
    onSelect = () => {},
    onDismiss = () => {},
  } = $props();
  
  let availableWallets = $state([]);
  let loading = $state(true);
  let detectedProviders = $state(new Map()); // Store providers detected via EIP-6963
  let connectingWallet = $state(null); // Track which wallet is currently connecting
  let installedWalletCount = $derived(availableWallets.filter((wallet) => wallet.installed).length);
  let portalEl = $state(null);
  let closeButtonEl = $state(null);
  let isMobileDevice = $state(false);
  
  // Constants
  const INSTALL_URLS = {
    phantom: 'https://phantom.app/download',
    metamask: 'https://metamask.io/download/',
    rabby: 'https://rabby.io/',
    okx: 'https://web3.okx.com/download',
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

    if (walletId === 'okx') {
      const deepLink = `okx://wallet/dapp/url?dappUrl=${encodeURIComponent(dappUrl)}`;
      return `https://web3.okx.com/download?deeplink=${encodeURIComponent(deepLink)}`;
    }

    return null;
  }
  
  const WALLET_LOGOS = {
    phantom: phantomLogo,
    metamask: metamaskLogo,
    rabby: rabbyLogo,
    okx: okxLogo,
    trust: trustLogo,
    coinbase: coinbaseLogo
  };

  const KNOWN_WALLET_RDNS = {
    'io.metamask': 'metamask',
    'io.rabby': 'rabby',
    'com.okex.wallet': 'okx',
    'app.phantom': 'phantom',
    'com.trustwallet.app': 'trust',
    'com.coinbase.wallet': 'coinbase',
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
               window.ethereum?.providers?.some(p => p.isMetaMask && !p.isTrust && !p.isPhantom && !p.isRabby && !p.isOkxWallet && !p.isOKExWallet) ||
               (window.ethereum?.isMetaMask && !window.ethereum?.isTrust && !window.ethereum?.isPhantom && !window.ethereum?.isRabby && !window.ethereum?.isOkxWallet && !window.ethereum?.isOKExWallet);
      },
      getProvider: async () => {
        // SDK-first: every MetaMask selection goes through Connect SDK
        // (preferExtension routes to the extension when present).
        try {
          const { getMetaMaskConnectProvider } = await import('../lib/metamaskConnect.js');
          return await getMetaMaskConnectProvider();
        } catch (error) {
          // Deliberate cancel — never silently fall back
          if (error?.code === 4001) throw error;
          // SDK chunk failed to load or SDK errored — use the injected
          // extension provider when one exists, otherwise surface the failure.
          const injected =
            getEIP6963Provider('metamask') ||
            findProviderInArray(p => p.isMetaMask && !p.isTrust && !p.isPhantom && !p.isRabby && !p.isOkxWallet && !p.isOKExWallet) ||
            ((window.ethereum?.isMetaMask && !window.ethereum?.isTrust && !window.ethereum?.isPhantom && !window.ethereum?.isRabby && !window.ethereum?.isOkxWallet && !window.ethereum?.isOKExWallet)
              ? window.ethereum : null);
          if (injected) return injected;
          throw error;
        }
      }
    },
    rabby: {
      name: 'Rabby Wallet',
      checkInstalled: () => {
        return detectedProviders.has('rabby') ||
               window.ethereum?.providers?.some(p => p.isRabby) ||
               window.ethereum?.isRabby === true;
      },
      getProvider: async () => {
        return getEIP6963Provider('rabby') ||
               findProviderInArray(p => p.isRabby) ||
               (window.ethereum?.isRabby ? window.ethereum : null);
      }
    },
    okx: {
      name: 'OKX Wallet',
      checkInstalled: () => {
        return detectedProviders.has('okx') ||
               window.ethereum?.providers?.some(p => p.isOkxWallet || p.isOKExWallet) ||
               window.okxwallet?.isOkxWallet ||
               window.okxwallet?.isOKExWallet ||
               window.ethereum?.isOkxWallet ||
               window.ethereum?.isOKExWallet;
      },
      getProvider: async () => {
        return getEIP6963Provider('okx') ||
               window.okxwallet ||
               findProviderInArray(p => p.isOkxWallet || p.isOKExWallet) ||
               ((window.ethereum?.isOkxWallet || window.ethereum?.isOKExWallet) ? window.ethereum : null);
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
    isMobileDevice = isMobileBrowser();

    // Set up EIP-6963 listener for wallet detection
    function handleProviderAnnouncement(event) {
      const providerDetail = event.detail;
      const provider = providerDetail?.provider;
      const info = providerDetail?.info;
      
      
      if (!provider) return;
      
      // Prefer EIP-6963's stable wallet identifier, then keep legacy flags as
      // fallbacks for older extension versions.
      const knownWalletId = KNOWN_WALLET_RDNS[info?.rdns];
      if (knownWalletId) {
        detectedProviders.set(knownWalletId, { provider, info });
      } else if (provider.isRabby) {
        detectedProviders.set('rabby', { provider, info });
      } else if (provider.isOkxWallet || provider.isOKExWallet) {
        detectedProviders.set('okx', { provider, info });
      } else if (provider.isPhantom) {
        detectedProviders.set('phantom', { provider, info });
      } else if (provider.isMetaMask && !provider.isTrust && !provider.isTrustWallet && !provider.isPhantom && !provider.isRabby && !provider.isOkxWallet && !provider.isOKExWallet) {
        detectedProviders.set('metamask', { provider, info });
      } else if (provider.isTrust || provider.isTrustWallet) {
        detectedProviders.set('trust', { provider, info });
      } else if (provider.isCoinbaseWallet) {
        detectedProviders.set('coinbase', { provider, info });
      } else if (info?.rdns || info?.uuid) {
        // Keep standards-compliant injected wallets usable even when they are
        // not part of the curated list. EIP-6963 icons stay inside <img> tags.
        const existingEntry = [...detectedProviders.entries()]
          .find(([walletId, detail]) => walletId.startsWith('injected:') && detail.provider === provider);
        const walletId = info.rdns ? `injected:${info.rdns}` : (existingEntry?.[0] || `injected:${info.uuid}`);

        if (existingEntry && existingEntry[0] !== walletId) {
          detectedProviders.delete(existingEntry[0]);
        }
        detectedProviders.set(walletId, { provider, info });
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
    const primaryWallets = ['metamask', 'rabby', 'okx', 'phantom', 'trust', 'coinbase'];
    
    for (const walletId of primaryWallets) {
      const config = walletConfigs[walletId];
      const installed = Boolean(config.checkInstalled());
      // UI-only flag: routing always goes through getProvider (SDK-first for
      // MetaMask); this just picks pill text and bypasses the install gate.
      const connectsViaSdk = walletId === 'metamask' && !installed;
      wallets.push({
        id: walletId,
        name: config.name,
        installed,
        connectsViaSdk,
        mobileDeepLink: isMobileBrowser() && !installed && !connectsViaSdk ? getMobileDeepLink(walletId) : null,
        getProvider: config.getProvider
      });
    }

    for (const [walletId, detail] of detectedProviders.entries()) {
      if (!walletId.startsWith('injected:')) continue;
      const info = detail?.info || {};
      wallets.push({
        id: walletId,
        name: info.name || 'Browser wallet',
        installed: true,
        connectsViaSdk: false,
        mobileDeepLink: null,
        icon: typeof info.icon === 'string' && info.icon.startsWith('data:image/') ? info.icon : null,
        getProvider: () => detail.provider,
      });
    }
    
    // Add "Other Wallets" option if ethereum is available but not from primary wallets
    if (window.ethereum) {
      const hasOtherWallet = primaryWallets.every((walletId) => !walletConfigs[walletId].checkInstalled()) &&
                             !wallets.some((wallet) => wallet.id.startsWith('injected:'));
      
      if (hasOtherWallet) {
        wallets.push({
          id: 'other',
          name: 'Other Wallets',
          installed: true,
          getProvider: () => window.ethereum
        });
      }
    }
    
    const actionRank = (wallet) => wallet.installed ? 3 : (wallet.connectsViaSdk || wallet.mobileDeepLink ? 2 : 1);
    availableWallets = wallets
      .map((wallet, index) => ({ ...wallet, originalIndex: index }))
      .sort((a, b) => actionRank(b) - actionRank(a) || a.originalIndex - b.originalIndex);
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
    
    if (!wallet.installed && !wallet.connectsViaSdk) {
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
    const providerType = connectingWallet?.id;
    connectionDismissed = true;

    // Stop the local loading race if it exists. Provider prompts may continue.
    if (connectionController) {
      connectionController.abort();
    }

    connectingWallet = null;
    isConnecting = false;
    isOpen = false;
    onDismiss({ reason: 'connection_view_close', providerType, connecting: true });
  }

  function closeSelector(reason) {
    if (!isOpen || connectingWallet) return;
    isOpen = false;
    onDismiss({ reason, connecting: false });
  }

  function walletHelpText(wallet) {
    if (wallet.installed) return 'Detected in this browser';
    if (wallet.connectsViaSdk) return isMobileDevice ? 'Open the wallet app to continue' : 'Extension, QR, or mobile';
    if (wallet.mobileDeepLink) return `Continue in the ${wallet.name} app`;
    if (isMobileDevice && wallet.id === 'rabby') return 'Open Portal inside Rabby’s browser';
    if (isMobileDevice) return 'Get the wallet app to continue';
    return 'Install the browser extension';
  }

  function walletStatusText(wallet) {
    if (wallet.installed) return 'Ready';
    if (wallet.connectsViaSdk) return 'Connect';
    if (wallet.mobileDeepLink) return 'Open app';
    if (isMobileDevice) return 'Get app';
    return 'Install';
  }

  function walletActionKind(wallet) {
    if (wallet.installed) return 'ready';
    if (wallet.connectsViaSdk || wallet.mobileDeepLink) return 'open';
    return 'install';
  }

  function handleBackdropClick(e) {
    // Don't close if currently connecting
    if (e.target === e.currentTarget && !connectingWallet) {
      closeSelector('backdrop');
    }
  }

  function handleKeyDown(e) {
    // Don't close if currently connecting
    if (isOpen && e.key === 'Escape' && !connectingWallet) {
      closeSelector('escape');
    }

    if (isOpen && e.key === 'Tab' && portalEl) {
      const focusable = [...portalEl.querySelectorAll('button:not(:disabled), a[href]')];
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }

  $effect(() => {
    if (!isOpen || typeof document === 'undefined') return;

    const previousActive = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    queueMicrotask(() => closeButtonEl?.focus());

    return () => {
      document.body.style.overflow = previousOverflow;
      previousActive?.focus?.();
    };
  });

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

{#snippet walletIcon(wallet)}
  {#if wallet.icon}
    <img src={wallet.icon} alt="" class="wallet-icon" />
  {:else if WALLET_LOGOS[wallet.id]}
    <img src={WALLET_LOGOS[wallet.id]} alt="" class="wallet-icon" />
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
    <div class="wallet-selector-modal" role="dialog" aria-modal="true" aria-labelledby="wallet-selector-title" aria-describedby="wallet-selector-description">
      <div class="wallet-selector-hero">
        <div class="wallet-hero-copy">
          <div class="wallet-kicker">
            <span class="wallet-hero-mark" aria-hidden="true">
              {@render genlayerHexMark()}
            </span>
            <span>GenLayer Portal</span>
          </div>
          <h2 id="wallet-selector-title" class="wallet-selector-title">Connect wallet</h2>
          <p id="wallet-selector-description">Choose how you want to sign in. No transaction required.</p>
        </div>
        <button
          class="wallet-selector-close"
          bind:this={closeButtonEl}
          onclick={() => {
            if (!connectingWallet) {
              closeSelector('close_button');
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
            <p>Looking for wallets in this browser…</p>
          </div>
        {:else if connectingWallet}
          <div class="wallet-selector-loading">
            <div class="connecting-wallet-container">
              <div class="connecting-wallet-logo">
                <div class="connecting-logo">
                  {@render walletIcon(connectingWallet)}
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
          <div class="wallet-guidance">
            <span class="wallet-guidance-icon" aria-hidden="true">
              {#if isMobileDevice}
                <svg viewBox="0 0 24 24" fill="none"><rect x="7" y="2.75" width="10" height="18.5" rx="2.25" stroke="currentColor" stroke-width="1.7"/><path d="M10 5h4M11 18.5h2" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
              {:else}
                <svg viewBox="0 0 24 24" fill="none"><rect x="2.75" y="4" width="18.5" height="13" rx="2.25" stroke="currentColor" stroke-width="1.7"/><path d="M8.5 20h7M12 17v3" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
              {/if}
            </span>
            <span class="wallet-guidance-copy">
              <strong>{isMobileDevice ? 'Continue in a wallet app' : 'Choose a browser wallet'}</strong>
              <span>{isMobileDevice ? 'We’ll open the app when a direct connection is available.' : 'Detected extensions are shown first.'}</span>
            </span>
          </div>

          <div class="wallet-section-heading" aria-live="polite">
            <span>Wallets</span>
            <span>{installedWalletCount > 0 ? `${installedWalletCount} ready` : 'Select to continue'}</span>
          </div>
          <div class="wallet-selector-list">
            {#each availableWallets as wallet, index}
              <button
                class="wallet-option wallet-action-{walletActionKind(wallet)}"
                style={`--wallet-index: ${index}`}
                onclick={() => selectWallet(wallet)}
                disabled={connectingWallet !== null}
                data-wallet-id={wallet.id}
              >
                <div class="wallet-icon-wrapper">
                  {@render walletIcon(wallet)}
                </div>
                <span class="wallet-copy">
                  <span class="wallet-name">
                    {wallet.name}
                  </span>
                  <span class="wallet-help">
                    {walletHelpText(wallet)}
                  </span>
                </span>
                <span class="wallet-status" class:wallet-status-ready={wallet.installed} class:wallet-status-open={!wallet.installed && (wallet.connectsViaSdk || wallet.mobileDeepLink)}>
                  {walletStatusText(wallet)}
                </span>
                <svg class="wallet-chevron" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="m7.5 4.5 5 5.5-5 5.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </button>
            {/each}
          </div>

          <div class="wallet-security-note">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3.25 19 6v5.25c0 4.2-2.75 7.55-7 9.5-4.25-1.95-7-5.3-7-9.5V6l7-2.75Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m9 12 2 2 4-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span><strong>Sign-in only.</strong> Connecting asks for a signature. It never moves funds or costs gas.</span>
          </div>
          
          <div class="wallet-selector-disclaimer">
            By continuing, you agree to the
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
    padding: 24px;
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
    border: 0;
    border-radius: 22px;
    box-shadow:
      0 0 0 1px rgba(19, 18, 20, 0.07),
      0 34px 70px rgba(15, 15, 15, 0.22),
      0 1px 0 rgba(255, 255, 255, 0.85) inset;
    display: flex;
    flex-direction: column;
    width: 560px;
    max-width: min(100%, 560px);
    max-height: min(92vh, 820px);
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
    padding: 24px 26px 22px;
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
    border: 0;
    box-shadow: 0 0 0 1px rgba(19, 18, 20, 0.08), 0 4px 12px rgba(19, 18, 20, 0.05);
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
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 20px 22px 22px;
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
  
  .wallet-guidance {
    align-items: center;
    background: #f7f7f5;
    border-radius: 14px;
    box-shadow: 0 0 0 1px rgba(19, 18, 20, 0.055), 0 2px 5px rgba(19, 18, 20, 0.035);
    color: #5f6067;
    display: flex;
    gap: 11px;
    margin-bottom: 17px;
    padding: 11px 13px;
  }

  .wallet-guidance-icon {
    align-items: center;
    background: #fff;
    border-radius: 9px;
    box-shadow: 0 0 0 1px rgba(19, 18, 20, 0.07), 0 2px 5px rgba(19, 18, 20, 0.04);
    color: #29292d;
    display: inline-flex;
    flex: 0 0 auto;
    height: 34px;
    justify-content: center;
    width: 34px;
  }

  .wallet-guidance-icon svg {
    height: 20px;
    width: 20px;
  }

  .wallet-guidance-copy {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .wallet-guidance-copy strong {
    color: #242428;
    font-size: 13px;
    font-weight: 800;
    line-height: 1.25;
  }

  .wallet-guidance-copy > span {
    font-size: 11.5px;
    line-height: 1.35;
    margin-top: 2px;
    text-wrap: pretty;
  }

  .wallet-section-heading {
    align-items: center;
    color: #77777d;
    display: flex;
    font-family: var(--font-mono);
    font-size: 10.5px;
    font-weight: 700;
    justify-content: space-between;
    letter-spacing: 0.02em;
    margin: 0 2px 9px;
    text-transform: uppercase;
  }
  
  .wallet-selector-list {
    display: grid;
    gap: 9px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  
  .wallet-option {
    align-items: center;
    background:
      linear-gradient(180deg, rgba(19, 18, 20, 0.02), rgba(255, 255, 255, 0)),
      #fff;
    border: 0;
    border-radius: 14px;
    box-shadow: 0 0 0 1px rgba(19, 18, 20, 0.07), 0 2px 5px rgba(19, 18, 20, 0.035);
    cursor: pointer;
    display: flex;
    gap: 12px;
    min-height: 78px;
    padding: 12px;
    position: relative;
    text-align: left;
    width: 100%;
    animation: walletCardIn 280ms cubic-bezier(0.2, 0, 0, 1) both;
    animation-delay: calc(var(--wallet-index) * 38ms);
    transition-duration: 160ms;
    transition-property: background-color, box-shadow, opacity, transform;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  @keyframes walletCardIn {
    from {
      filter: blur(4px);
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      filter: blur(0);
      opacity: 1;
      transform: translateY(0);
    }
  }

  .wallet-option:active {
    transform: scale(0.96);
  }

  .wallet-option:focus-visible,
  .wallet-selector-close:focus-visible,
  .cancel-connect:focus-visible {
    outline: 3px solid rgba(56, 125, 232, 0.28);
    outline-offset: 2px;
  }
  
  .wallet-icon-wrapper {
    align-items: center;
    background: #fff;
    border-radius: 13px;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.08), 0 4px 10px rgba(19, 18, 20, 0.06);
    display: flex;
    flex-shrink: 0;
    height: 44px;
    justify-content: center;
    padding: 3px;
    width: 44px;
  }
  
  .wallet-icon {
    width: 100%;
    height: 100%;
    border-radius: 10px;
    object-fit: contain;
    outline: 1px solid rgba(0, 0, 0, 0.1);
    outline-offset: -1px;
  }

  .wallet-copy {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
  }
  
  .wallet-name {
    font-size: 0.9rem;
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
    text-wrap: pretty;
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

  .wallet-status-open {
    background: #edf3ff;
    color: #2e67bd;
  }

  .wallet-chevron {
    color: #a5a5aa;
    flex: 0 0 auto;
    height: 18px;
    width: 18px;
    display: none;
  }

  .wallet-action-install {
    background: #fbfbfb;
  }

  .wallet-security-note {
    align-items: flex-start;
    background: #f1f8f4;
    border-radius: 12px;
    box-shadow: 0 0 0 1px rgba(22, 137, 77, 0.1);
    color: #46705a;
    display: flex;
    font-size: 11.5px;
    gap: 9px;
    line-height: 1.45;
    margin-top: 14px;
    padding: 10px 12px;
    text-wrap: pretty;
  }

  .wallet-security-note svg {
    color: #16894d;
    flex: 0 0 auto;
    height: 19px;
    margin-top: 1px;
    width: 19px;
  }

  .wallet-security-note strong {
    color: #22553a;
  }
  
  .wallet-selector-disclaimer {
    border-top: 1px solid #f0f0f2;
    margin-top: 14px;
    padding-top: 14px;
    text-align: center;
    font-size: 0.75rem;
    color: #9CA3AF;
    line-height: 1.5;
    text-wrap: pretty;
  }

  .wallet-selector-disclaimer a {
    color: #5a5a61;
    font-weight: 700;
    text-decoration-color: rgba(90, 90, 97, 0.35);
    text-underline-offset: 2px;
  }

  @media (hover: hover) and (pointer: fine) {
    .wallet-option:hover {
      background-color: #fafafa;
      box-shadow: 0 0 0 1px rgba(19, 18, 20, 0.1), 0 14px 28px rgba(19, 18, 20, 0.09);
      transform: translateY(-1px);
    }
  }

  /* Responsive design */
  @media (max-width: 640px) {
    .wallet-selector-backdrop {
      align-items: flex-end;
      padding: 0;
    }

    .wallet-selector-modal {
      animation-name: sheetUp;
      border-radius: 24px 24px 0 0;
      max-height: 94vh;
      max-height: 94dvh;
      max-width: none;
      width: 100%;
    }

    @keyframes sheetUp {
      from {
        opacity: 0;
        transform: translateY(18px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .wallet-selector-hero {
      padding: 18px 20px 16px;
    }

    .wallet-kicker {
      margin-bottom: 9px;
    }

    .wallet-hero-mark {
      border-radius: 12px;
      height: 36px;
      width: 36px;
    }

    .genlayer-hex-mark {
      height: 29px;
      width: 29px;
    }

    .wallet-selector-title {
      font-size: 23px;
    }

    .wallet-selector-hero p {
      font-size: 13px;
      margin-top: 6px;
    }

    .wallet-selector-close {
      height: 44px;
      width: 44px;
    }
    
    .wallet-selector-body {
      padding: 14px 16px max(18px, env(safe-area-inset-bottom));
    }

    .wallet-guidance {
      margin-bottom: 14px;
      padding: 10px 12px;
    }

    .wallet-selector-list {
      gap: 8px;
      grid-template-columns: minmax(0, 1fr);
    }

    .wallet-option {
      min-height: 68px;
      padding: 10px 11px;
    }

    .wallet-icon-wrapper {
      height: 42px;
      width: 42px;
    }

    .wallet-chevron {
      display: block;
    }

    .wallet-security-note {
      margin-top: 12px;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .wallet-selector-backdrop,
    .wallet-selector-modal,
    .wallet-option {
      animation: none;
    }

    .wallet-option,
    .wallet-selector-close,
    .cancel-connect {
      transition-duration: 0.01ms;
    }
  }
</style>
