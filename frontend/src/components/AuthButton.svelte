<!-- AuthButton.svelte -->
<script>
  import { onMount } from 'svelte';
  import { push, location } from 'svelte-spa-router';
  import { authState, signInWithEthereum, logout } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { showError, showWarning } from '../lib/toastStore';
  import {
    consumeConnectWalletIntent,
    getAnalyticsContext,
    getFunnelDurationMs,
    markLifecycleTime,
    markFunnelTime,
    trackEvent,
  } from '../lib/analytics.js';
  import WalletSelector from './WalletSelector.svelte';

  // Use $: to access the store values reactively
  $: isAuthenticated = $authState.isAuthenticated;
  $: address = $authState.address;
  $: storeLoading = $authState.loading;
  $: storeError = $authState.error;
  $: userName = $userStore.user?.name;

  let loading = false;
  let showDropdown = false;
  let showWalletSelector = false;
  let isMobileViewport = false;

  $: authButtonLabel = isMobileViewport ? formatAddress(address) : (userName || formatAddress(address));

  function preserveCurrentRouteForLogin() {
    if (sessionStorage.getItem('redirectAfterLogin')) return;

    const currentRoute = $location || window.location.pathname || '/';
    if (currentRoute === '/my-submissions') {
      sessionStorage.setItem('redirectAfterLogin', currentRoute);
    }
  }

  // Show toast for auth store errors with appropriate severity
  $: if (storeError) {
    // User-initiated actions are warnings (less severe)
    if (storeError.includes('Connection rejected') || storeError.includes('MetaMask')) {
      showWarning(storeError);
    } else {
      // Authentication failures are errors
      showError(storeError);
    }
    authState.setError(null);
  }

  async function handleAuth() {
    if (isAuthenticated) {
      // If authenticated, clicking the button should toggle the dropdown
      showDropdown = !showDropdown;
      return;
    }

    const intent = consumeConnectWalletIntent();
    const context = getAnalyticsContext({
      surface: intent.surface || 'navbar',
      cta_id: intent.cta_id || 'auth_button',
      target_route: intent.target_route,
    });
    markFunnelTime('wallet_click');
    trackEvent('connect_wallet_click', context);

    // Show wallet selector modal
    showWalletSelector = true;
    trackEvent('wallet_selector_view', {
      ...context,
      surface: 'modal',
    });
  }

  function providerType(walletName) {
    const value = String(walletName || '').toLowerCase();
    if (value.includes('metamask')) return 'metamask';
    if (value.includes('phantom')) return 'phantom';
    if (value.includes('trust')) return 'trust';
    if (value.includes('coinbase')) return 'coinbase';
    return 'other';
  }

  function walletErrorStage(error) {
    const message = String(error?.message || '').toLowerCase();
    if (error?.code === 4001 || message.includes('user rejected') || message.includes('user denied')) {
      return 'user_rejected';
    }
    if (message.includes('no wallet') || message.includes('provider')) return 'provider_unavailable';
    if (message.includes('signature') || message.includes('sign')) return 'signature';
    if (message.includes('nonce')) return 'nonce';
    if (message.includes('network')) return 'network';
    if (error?.response?.status) return 'backend';
    return 'unknown';
  }

  async function handleWalletSelected(provider, walletName) {
    // Start the connection process with selected wallet
    loading = true;
    const provider_type = providerType(walletName);
    const context = getAnalyticsContext({
      surface: 'modal',
      provider_type,
    });
    trackEvent('wallet_provider_selected', context);
    trackEvent('wallet_auth_started', context);

    try {
      preserveCurrentRouteForLogin();

      // Sign in with Ethereum
      await signInWithEthereum(provider, walletName);

      // Close wallet selector modal
      showWalletSelector = false;
      markFunnelTime('wallet_auth_success');
      markLifecycleTime('first_wallet_auth_success');
      trackEvent('wallet_auth_success', getAnalyticsContext({
        surface: 'modal',
        provider_type,
        time_from_wallet_click_ms: getFunnelDurationMs('wallet_click'),
      }));

      // ProfileCompletionGuard will automatically show if profile is incomplete
      // Otherwise user continues to their profile or intended destination
    } catch (err) {
      trackEvent('wallet_auth_failed', getAnalyticsContext({
        surface: 'modal',
        provider_type,
        error_stage: walletErrorStage(err),
      }));
      // Error is already handled by the reactive statement that watches storeError
      // No need to show toast here to avoid duplicate notifications
      // Keep modal open on error so user can try again
    } finally {
      loading = false;
    }
  }
  
  async function handleLogout() {
    showDropdown = false;
    await logout();
  }
  
  function navigateToProfile() {
    if (address) {
      showDropdown = false;
      push(`/participant/${address}`);
    }
  }
  
  function navigateToEditProfile() {
    showDropdown = false;
    push('/profile');
  }
  
  function formatAddress(addr) {
    if (!addr) return '';
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
  }
  
  function handleClickOutside(event) {
    if (showDropdown && !event.target.closest('.auth-dropdown-container')) {
      showDropdown = false;
    }
  }

  function updateMobileViewport() {
    isMobileViewport = window.matchMedia('(max-width: 767px)').matches;
  }
  
  onMount(() => {
    updateMobileViewport();
    window.addEventListener('resize', updateMobileViewport);
    document.addEventListener('click', handleClickOutside);
    return () => {
      window.removeEventListener('resize', updateMobileViewport);
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<div class="auth-dropdown-container">
  <button 
    class="auth-button {isAuthenticated ? 'connected' : '!min-w-[168px] !h-11 !px-5 !py-2.5 !text-[15px]'}"
    on:click={handleAuth}
    disabled={loading || storeLoading}
    data-auth-button
  >
    {#if loading || storeLoading}
      <span class="loading-spinner"></span>
    {:else if isAuthenticated}
      <span class="address">{authButtonLabel}</span>
      <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
      </svg>
    {:else}
      <span>Connect Wallet</span>
    {/if}
  </button>
  
  {#if showDropdown && isAuthenticated}
    <div class="auth-dropdown">
      <div class="dropdown-address">
        {address}
      </div>
      <button class="dropdown-item" on:click={navigateToProfile}>
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
        </svg>
        View Public Profile
      </button>
      <button class="dropdown-item" on:click={navigateToEditProfile}>
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
        </svg>
        Edit Profile
      </button>
      <button class="dropdown-item logout" on:click={handleLogout}>
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
        </svg>
        Disconnect
      </button>
    </div>
  {/if}
</div>

<!-- Wallet Selector Modal -->
<WalletSelector
  bind:isOpen={showWalletSelector}
  onSelect={handleWalletSelected}
/>

<style>
  .auth-dropdown-container {
    position: relative;
  }
  
  .auth-button {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    background-color: #131214;
    color: white;
    border: none;
    min-width: 140px;
    height: 40px;
    font-size: 0.875rem;
  }

  .auth-button:hover {
    background-color: #1a1a24;
  }

  .auth-button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .auth-button.connected {
    background-color: #131214;
  }

  .auth-button.connected:hover {
    background-color: #1a1a24;
  }
  
  .loading-spinner {
    display: inline-block;
    width: 1rem;
    height: 1rem;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 1s ease-in-out infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .auth-dropdown {
    position: absolute;
    top: calc(100% + 0.5rem);
    right: 0;
    z-index: 50;
    min-width: 280px;
    background-color: white;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    overflow: hidden;
    border: 1px solid #e5e7eb;
  }
  
  .dropdown-address {
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    color: #6b7280;
    border-bottom: 1px solid #e5e7eb;
    word-break: break-all;
    background-color: #f9fafb;
    font-family: monospace;
  }
  
  .dropdown-item {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 0.75rem 1rem;
    text-align: left;
    font-size: 0.875rem;
    color: #374151;
    background-color: transparent;
    border: none;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  
  .dropdown-item:hover {
    background-color: #f3f4f6;
  }
  
  .dropdown-item.logout {
    color: #ef4444;
  }

  .dropdown-item.logout:hover {
    background-color: #fef2f2;
  }

  @media (max-width: 767px) {
    .auth-dropdown-container {
      max-width: min(40vw, 7.75rem);
    }

    .auth-button {
      min-width: 6.75rem;
      max-width: min(40vw, 7.75rem);
      height: 2.125rem;
      padding: 0.375rem 0.625rem;
      border-radius: 1.0625rem;
      font-size: 0.75rem;
      line-height: 1rem;
    }

    .auth-button > span:not(.loading-spinner) {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .auth-button svg {
      flex-shrink: 0;
      height: 0.875rem;
      width: 0.875rem;
    }

    .auth-dropdown {
      min-width: min(15rem, calc(100vw - 1rem));
      max-width: calc(100vw - 1rem);
    }
  }
</style>
