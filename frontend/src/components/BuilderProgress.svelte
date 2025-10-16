<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { onMount } from 'svelte';
  import { showWarning, showError } from '../lib/toastStore';
  
  let {
    testnetBalance = null,
    hasBuilderWelcome = false,
    hasDeployedContract = false,
    githubUsername = '',
    hasStarredRepo = false,
    repoToStar = 'genlayerlabs/genlayer-project-boilerplate',
    showActions = true,
    colorTheme = 'orange',
    onClaimBuilderBadge = null,
    isClaimingBuilderBadge = false,
    onRefreshBalance = null,
    isRefreshingBalance = false,
    onCheckRequirements = null,
    isCheckingRequirements = false,
    onCheckDeployments = null,
    isCheckingDeployments = false,
    onOpenStudio = null,
    onLinkGitHub = null,
    onCheckRepoStar = null,
    isCheckingRepoStar = false
  } = $props();
  
  // Network states
  let hasAsimovNetwork = $state(false);
  let hasStudioNetwork = $state(false);
  let isCheckingNetworks = $state(false);
  let isAddingAsimov = $state(false);
  let isAddingStudio = $state(false);

  // Derive wallet address from auth state
  let walletAddress = $derived($authState.address);

  // Get wallet-specific localStorage keys
  function getStorageKey(network) {
    if (!walletAddress) return null;
    return `genlayer_${network}_network_added_${walletAddress.toLowerCase()}`;
  }

  // Load network state from localStorage for current wallet
  function loadNetworkState() {
    if (typeof window === 'undefined' || !walletAddress) return;

    const asimovKey = getStorageKey('asimov');
    const studioKey = getStorageKey('studio');

    hasAsimovNetwork = asimovKey ? localStorage.getItem(asimovKey) === 'true' : false;
    hasStudioNetwork = studioKey ? localStorage.getItem(studioKey) === 'true' : false;
  }

  // Watch for wallet address changes and reload network state
  $effect(() => {
    loadNetworkState();
  });
  
  // Network configurations
  const ASIMOV_NETWORK = {
    chainId: '0x107D', // 4221 in hex
    chainName: 'GenLayer Asimov Testnet',
    nativeCurrency: {
      name: 'GEN',
      symbol: 'GEN',
      decimals: 18
    },
    rpcUrls: ['https://genlayer-testnet.rpc.caldera.xyz/http'],
    blockExplorerUrls: ['https://genlayer-testnet.explorer.caldera.xyz']
  };
  
  const STUDIO_NETWORK = {
    chainId: '0xF22F', // 61999 in hex
    chainName: 'GenLayer Studio',
    nativeCurrency: {
      name: 'GEN',
      symbol: 'GEN',
      decimals: 18
    },
    rpcUrls: ['https://studio.genlayer.com/api'],
    blockExplorerUrls: []
  };
  
  // Check if networks are configured (passive - no popups)
  async function checkNetworks() {
    // Get the connected wallet's provider from authState or fallback to window.ethereum
    const provider = $authState.provider || window.ethereum;
    if (!provider || !walletAddress) {
      return;
    }

    isCheckingNetworks = true;
    try {
      // Get current network (doesn't trigger popup)
      const currentChainId = await provider.request({ method: 'eth_chainId' });

      // If user is on Asimov or Studio network, mark as added and persist for this wallet
      if (currentChainId === ASIMOV_NETWORK.chainId && !hasAsimovNetwork) {
        hasAsimovNetwork = true;
        const key = getStorageKey('asimov');
        if (key) localStorage.setItem(key, 'true');
      }
      if (currentChainId === STUDIO_NETWORK.chainId && !hasStudioNetwork) {
        hasStudioNetwork = true;
        const key = getStorageKey('studio');
        if (key) localStorage.setItem(key, 'true');
      }
    } catch (error) {
      console.error('Error checking networks:', error);
    } finally {
      isCheckingNetworks = false;
    }
  }

  // Add network to wallet
  async function addNetwork(network, isStudio = false) {
    // Get the connected wallet's provider from authState or fallback to window.ethereum
    const provider = $authState.provider || window.ethereum;
    if (!provider) {
      showWarning('Please connect your wallet first');
      return;
    }

    if (isStudio) {
      isAddingStudio = true;
    } else {
      isAddingAsimov = true;
    }

    try {
      await provider.request({
        method: 'wallet_addEthereumChain',
        params: [network],
      });

      // Network added successfully - update state and persist for this wallet
      if (isStudio) {
        hasStudioNetwork = true;
        const key = getStorageKey('studio');
        if (key) localStorage.setItem(key, 'true');
      } else {
        hasAsimovNetwork = true;
        const key = getStorageKey('asimov');
        if (key) localStorage.setItem(key, 'true');
      }
    } catch (error) {
      console.error('Error adding network:', error);
      if (error.code !== 4001) { // User didn't reject
        showError('Failed to add network. Please try manually.');
      }
    } finally {
      if (isStudio) {
        isAddingStudio = false;
      } else {
        isAddingAsimov = false;
      }
    }
  }
  
  // Removed automatic network checking on mount and wallet change
  // Networks are only checked when:
  // 1. User manually adds a network (triggers automatic switch by MetaMask)
  // 2. State is loaded from wallet-specific localStorage
  // No automatic MetaMask API calls
  
  // Calculate completed requirements (8 total - including GitHub and star)
  let completedCount = $derived(
    (walletAddress ? 1 : 0) +
    (hasBuilderWelcome ? 1 : 0) +
    (githubUsername ? 1 : 0) +
    (hasStarredRepo ? 1 : 0) +
    (hasAsimovNetwork ? 1 : 0) +
    (testnetBalance && testnetBalance > 0 ? 1 : 0) +
    (hasStudioNetwork ? 1 : 0) +
    (hasDeployedContract ? 1 : 0)
  );
  
  // Check if wallet has testnet balance
  let hasTestnetBalance = $derived(testnetBalance && testnetBalance > 0);
</script>

<div class="bg-white rounded-lg p-5 border border-orange-200">
  <h3 class="text-base font-semibold text-gray-900 mb-3 flex items-center">
    <svg class="w-5 h-5 mr-2 text-orange-500" fill="currentColor" viewBox="0 0 20 20">
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
    </svg>
    Builder Requirements
  </h3>
  
  <div class="max-w-2xl">
    <!-- Requirements List -->
    <div class="space-y-3">
      <!-- Requirement 1: Connect Wallet -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if walletAddress}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Connect your wallet</p>
            <p class="text-xs text-gray-500">
              {#if walletAddress}
                Connected: {walletAddress.slice(0, 6)}...{walletAddress.slice(-4)}
              {:else}
                Connect to get started
              {/if}
            </p>
          </div>
        </div>
        {#if showActions && !walletAddress}
          <button
            onclick={() => push('/builders/welcome')}
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
          >
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
            </svg>
            Connect Wallet
          </button>
        {/if}
      </div>
    
      <!-- Requirement 2: Earn your first points -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if hasBuilderWelcome}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Earn your first points</p>
            <p class="text-xs text-gray-500">
              {#if hasBuilderWelcome}
                Welcome! You've earned your first points in the Builder Journey
              {:else}
                Claim your Builder Welcome contribution
              {/if}
            </p>
          </div>
        </div>
        {#if showActions && !hasBuilderWelcome}
          <button
            onclick={() => onClaimBuilderBadge ? onClaimBuilderBadge() : null}
            disabled={isClaimingBuilderBadge || !onClaimBuilderBadge || !walletAddress}
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {#if isClaimingBuilderBadge}
              <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Claiming...
            {:else}
              <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
              </svg>
              Claim Contribution
            {/if}
          </button>
        {/if}
      </div>

      <!-- Requirement 3: Link GitHub Profile -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if githubUsername}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Connect your GitHub account</p>
            <p class="text-xs text-gray-500">
              {#if githubUsername}
                Connected: @{githubUsername}
              {:else}
                Connect your GitHub account
              {/if}
            </p>
          </div>
        </div>
        {#if showActions && !githubUsername && onLinkGitHub}
          <button
            onclick={() => onLinkGitHub ? onLinkGitHub() : null}
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
          >
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 0C4.477 0 0 4.477 0 10c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.341-3.369-1.341-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0110 4.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C17.137 18.163 20 14.418 20 10c0-5.523-4.477-10-10-10z" clip-rule="evenodd"/>
            </svg>
            Link GitHub
          </button>
        {/if}
      </div>

      <!-- Requirement 4: Star GenLayer Repository -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if hasStarredRepo}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Star the GenLayer Project Boilerplate repository</p>
            <p class="text-xs text-gray-500 flex items-center gap-2">
              {#if !githubUsername}
                <span>Connect GitHub first</span>
              {:else if hasStarredRepo}
                <span>Get familiarized with the GenLayer boilerplate repo.</span>
              {:else}
                <span>Show your support for the project</span>
              {/if}
              {#if showActions && onCheckRepoStar && githubUsername}
                <button
                  onclick={onCheckRepoStar}
                  disabled={isCheckingRepoStar}
                  class="inline-flex items-center justify-center w-4 h-4 rounded hover:bg-gray-100 transition-colors disabled:opacity-50"
                  title="Check star status"
                >
                  {#if isCheckingRepoStar}
                    <svg class="animate-spin w-3 h-3 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  {:else}
                    <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                  {/if}
                </button>
              {/if}
            </p>
          </div>
        </div>
        {#if showActions && githubUsername}
          <a
            href="https://github.com/{repoToStar}"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
          >
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
            {hasStarredRepo ? 'View Repo' : 'Star Repo'}
          </a>
        {/if}
      </div>

      <!-- Requirement 5: Add Asimov Network -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if hasAsimovNetwork}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Add GenLayer Asimov Network to your wallet</p>
            <p class="text-xs text-gray-500">
              {#if hasAsimovNetwork}
                Network configured in your wallet
              {:else if walletAddress}
                To top-up and deploy in Testnet Asimov
              {:else}
                Connect wallet first
              {/if}
            </p>
          </div>
        </div>
        {#if showActions}
          {#if !hasAsimovNetwork && walletAddress}
            <button
              onclick={() => addNetwork(ASIMOV_NETWORK, false)}
              disabled={isAddingAsimov}
              class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {#if isAddingAsimov}
                <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Adding...
              {:else}
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
                </svg>
                Add Network
              {/if}
            </button>
          {/if}
        {/if}
      </div>
    
      <!-- Requirement 3: Top-up with Testnet GEN -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if hasTestnetBalance}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Top-up your wallet with testnet GEN</p>
            <p class="text-xs text-gray-500 flex items-center gap-2">
              {#if !hasAsimovNetwork}
                <span>Add Asimov Network first</span>
              {:else if testnetBalance === null}
                <span>Click refresh icon to check balance</span>
              {:else if hasTestnetBalance}
                <span>Current balance: {testnetBalance} GEN</span>
              {:else}
                <span>Visit the faucet to get testnet tokens</span>
              {/if}
              {#if showActions && onRefreshBalance && testnetBalance !== null && hasAsimovNetwork}
                <button
                  onclick={onRefreshBalance}
                  disabled={isRefreshingBalance}
                  class="inline-flex items-center justify-center w-4 h-4 rounded hover:bg-gray-100 transition-colors disabled:opacity-50"
                  title="Refresh balance"
                >
                  {#if isRefreshingBalance}
                    <svg class="animate-spin w-3 h-3 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  {:else}
                    <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                  {/if}
                </button>
              {/if}
            </p>
          </div>
        </div>
        {#if showActions}
          <a
            href="https://genlayer-faucet.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
          >
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
            </svg>
            {hasTestnetBalance ? 'Get More' : 'Get Tokens'}
          </a>
        {/if}
      </div>
    
      <!-- Requirement 4: Add Studio Network -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if hasStudioNetwork}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Add the Studio Network to your wallet</p>
            <p class="text-xs text-gray-500">
              {#if hasStudioNetwork}
                Network configured in your wallet
              {:else if walletAddress}
                To use studio.genlayer.com
              {:else}
                Connect wallet first
              {/if}
            </p>
          </div>
        </div>
        {#if showActions}
          {#if !hasStudioNetwork && walletAddress}
            <button
              onclick={() => addNetwork(STUDIO_NETWORK, true)}
              disabled={isAddingStudio}
              class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            >
              {#if isAddingStudio}
                <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Adding...
              {:else}
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
                </svg>
                Add Network
              {/if}
            </button>
          {/if}
        {/if}
      </div>
    
      <!-- Requirement 5: Deploy Contract -->
      <div class="flex items-center justify-between">
        <div class="flex items-start gap-3">
          <div class="mt-0.5">
            {#if hasDeployedContract}
              <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
                <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </div>
            {:else}
              <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
                <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
              </div>
            {/if}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">Deploy your first GenLayer contract</p>
            <p class="text-xs text-gray-500">
              {#if hasDeployedContract}
                Contract deployed successfully!
              {:else if !hasTestnetBalance}
                Top-up your wallet first
              {:else}
                Deploy on Asimov or Studio network
              {/if}
            </p>
          </div>
        </div>
        {#if showActions}
          <div class="flex items-center gap-2">
            {#if !hasDeployedContract && onCheckDeployments}
              <button
                onclick={onCheckDeployments}
                disabled={isCheckingDeployments || !$authState.isAuthenticated}
                class="px-2 py-1 text-xs font-medium text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Check for deployed contracts"
              >
                {#if isCheckingDeployments}
                  <svg class="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                {:else}
                  <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
                  </svg>
                {/if}
              </button>
            {/if}
            {#if onOpenStudio}
              <button
                onclick={onOpenStudio}
                class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
              >
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/>
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"/>
                </svg>
                Open Studio
              </button>
            {:else}
              <a
                href="https://studio.genlayer.com"
                target="_blank"
                rel="noopener noreferrer"
                class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
              >
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/>
                  <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"/>
                </svg>
                Open Studio
              </a>
            {/if}
          </div>
        {/if}
      </div>
    </div>
    
    {#if showActions}
      <!-- Progress status -->
      <div class="mt-4 text-xs text-gray-500">
        <span class="font-medium">{completedCount} of 8</span> requirements completed
      </div>
    {/if}
  </div>
</div>