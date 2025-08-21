<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { getCurrentUser, journeyAPI, usersAPI } from '../lib/api';
  import Icon from '../components/Icons.svelte';
  
  let currentUser = $state(null);
  let hasValidatorWelcome = $state(false);
  let isClaimingValidatorBadge = $state(false);
  let accountBalance = $state(0);
  let hasDeployedContract = $state(false);
  let isClaimingBuilderBadge = $state(false);
  let error = $state('');
  let loading = $state(true);
  
  // Derived states for requirements
  let requirement1Met = $derived(hasValidatorWelcome);
  let requirement2Met = $derived(accountBalance > 0);
  let requirement3Met = $derived(hasDeployedContract);
  let allRequirementsMet = $derived(requirement1Met && requirement2Met && requirement3Met);
  
  onMount(async () => {
    await loadData();
    // Check balance periodically
    const interval = setInterval(async () => {
      if ($authState.isAuthenticated && accountBalance === 0) {
        await checkBalance();
      }
    }, 5000); // Check every 5 seconds
    
    return () => clearInterval(interval);
  });
  
  async function loadData() {
    try {
      if ($authState.isAuthenticated) {
        currentUser = await getCurrentUser();
        hasValidatorWelcome = currentUser?.has_validator_waitlist || false;
        await checkBalance();
      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    } finally {
      loading = false;
    }
  }
  
  async function checkBalance() {
    try {
      // Check account balance via API
      const response = await usersAPI.getAccountBalance();
      accountBalance = response.data.balance || 0;
    } catch (err) {
      console.error('Failed to check balance:', err);
    }
  }
  
  async function claimValidatorWelcome() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }
    
    isClaimingValidatorBadge = true;
    error = '';
    
    try {
      await journeyAPI.completeValidatorJourney();
      // Reload user data to get updated badge status
      currentUser = await getCurrentUser();
      hasValidatorWelcome = currentUser?.has_validator_waitlist || false;
    } catch (err) {
      error = err.response?.data?.error || 'Failed to claim validator welcome badge';
    } finally {
      isClaimingValidatorBadge = false;
    }
  }
  
  async function handleClaimBuilderBadge() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }
    
    if (!allRequirementsMet) {
      error = 'Please complete all requirements first';
      return;
    }
    
    isClaimingBuilderBadge = true;
    error = '';
    
    try {
      await journeyAPI.completeBuilderJourney();
      sessionStorage.setItem('journeySuccess', 'Successfully earned your Builder Welcome badge!');
      push(`/participant/${$authState.address}`);
    } catch (err) {
      error = err.response?.data?.error || 'Failed to claim badge';
      isClaimingBuilderBadge = false;
    }
  }
</script>

<div class="space-y-6 sm:space-y-8">
  <!-- Clean Header -->
  <div>
    <h1 class="text-2xl font-bold text-gray-900">GenLayer Builder Program</h1>
    <p class="mt-1 text-sm text-gray-500">
      Master Intelligent Contracts on GenLayer's AI-powered blockchain
    </p>
  </div>

  <!-- Main Card with Process -->
  <div class="bg-white border border-gray-200 rounded-lg shadow-sm">
    <div class="p-6">
      <!-- Three Steps -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <!-- Step 1: Learn the Basics -->
        <div class="flex items-center">
          <div class="flex items-center justify-center font-bold text-orange-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
            1
          </div>
          <div class="flex items-center justify-center w-10 h-10 bg-orange-100 rounded-lg flex-shrink-0">
            <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
            </svg>
          </div>
          <div class="flex-1 ml-2">
            <h3 class="font-semibold text-gray-900">Learn the Basics</h3>
            <p class="text-sm text-gray-600">
              Explore the <a 
                href="https://studio.genlayer.com" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-orange-600 hover:text-orange-700 underline"
              >Studio</a> and <a 
                href="https://docs.genlayer.com" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-orange-600 hover:text-orange-700 underline"
              >docs</a>
            </p>
          </div>
        </div>
        
        <!-- Step 2: Deploy -->
        <div class="flex items-center">
          <div class="flex items-center justify-center font-bold text-orange-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
            2
          </div>
          <div class="flex items-center justify-center w-10 h-10 bg-orange-100 rounded-lg flex-shrink-0">
            <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
            </svg>
          </div>
          <div class="flex-1 ml-2">
            <h3 class="font-semibold text-gray-900">Deploy</h3>
            <p class="text-sm text-gray-600">Create and deploy your first Intelligent Contract</p>
          </div>
        </div>
        
        <!-- Step 3: Earn Your Badge -->
        <div class="flex items-center">
          <div class="flex items-center justify-center font-bold text-orange-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
            3
          </div>
          <div class="flex items-center justify-center w-10 h-10 bg-orange-100 rounded-lg flex-shrink-0">
            <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="flex-1 ml-2">
            <h3 class="font-semibold text-gray-900">Earn Your Badge</h3>
            <p class="text-sm text-gray-600">Join our builder community</p>
          </div>
        </div>
      </div>

      <!-- Divider -->
      <div class="border-t border-gray-100 pt-6">
        <!-- Two Column Layout for Info -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Getting Started -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">Getting Started</h3>
            <p class="text-sm text-gray-600 mb-2">
              Start building contracts that think. GenLayer's <span class="font-medium">Intelligent Contracts</span> bring AI reasoning directly into blockchain logic.
            </p>
            <div class="space-y-1">
              <a 
                href="https://docs.genlayer.com"
                target="_blank"
                rel="noopener noreferrer"
                class="text-sm text-orange-600 hover:text-orange-700 font-medium inline-flex items-center"
              >
                Read the documentation
                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </a>
              <br/>
              <a 
                href="https://studio.genlayer.com"
                target="_blank"
                rel="noopener noreferrer"
                class="text-sm text-orange-600 hover:text-orange-700 font-medium inline-flex items-center"
              >
                Open GenLayer Studio
                <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </a>
            </div>
          </div>
          
          <!-- What You'll Learn -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">What You'll Learn</h3>
            <ul class="text-sm text-gray-600 space-y-1">
              <li class="flex items-start">
                <span class="text-orange-500 mr-1">•</span>
                <span>Intelligent Contracts fundamentals</span>
              </li>
              <li class="flex items-start">
                <span class="text-orange-500 mr-1">•</span>
                <span>Working with LLM-powered logic</span>
              </li>
              <li class="flex items-start">
                <span class="text-orange-500 mr-1">•</span>
                <span>Optimistic Democracy consensus</span>
              </li>
              <li class="flex items-start">
                <span class="text-orange-500 mr-1">•</span>
                <span>Real-world use cases and patterns</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Requirements Section -->
  <div class="bg-white shadow-sm rounded-lg p-6 sm:p-8">
    <h2 class="text-xl font-bold text-gray-900 mb-3">Builder Badge Requirements</h2>
    
    <p class="text-gray-700 mb-6">
      Complete these three requirements to earn your Builder badge:
    </p>
    
    <div class="space-y-4">
      <!-- Requirement 1: Validator Welcome Badge -->
      <div class="border border-gray-200 rounded-lg p-4">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="validatorBadge" 
                checked={requirement1Met}
                disabled={true}
                class="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded mr-3"
              />
              <label for="validatorBadge" class="text-sm font-medium text-gray-900">
                1. Claim Validator Welcome Badge
              </label>
            </div>
            <p class="text-xs text-gray-600 mt-1 ml-7">
              Join the validator waitlist to get started
            </p>
          </div>
          {#if !hasValidatorWelcome}
            <button
              onclick={claimValidatorWelcome}
              disabled={isClaimingValidatorBadge}
              class="ml-3 px-4 py-2 bg-sky-600 text-white text-sm rounded-md hover:bg-sky-700 transition-colors disabled:opacity-50"
            >
              {isClaimingValidatorBadge ? 'Claiming...' : 'Claim Badge'}
            </button>
          {:else}
            <span class="ml-3 px-3 py-2 bg-green-100 text-green-800 text-sm rounded-md">
              ✓ Claimed
            </span>
          {/if}
        </div>
      </div>

      <!-- Requirement 2: Top up Account -->
      <div class="border border-gray-200 rounded-lg p-4">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="accountBalance" 
                checked={requirement2Met}
                disabled={true}
                class="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded mr-3"
              />
              <label for="accountBalance" class="text-sm font-medium text-gray-900">
                2. Top up your GenLayer account
              </label>
            </div>
            <p class="text-xs text-gray-600 mt-1 ml-7">
              Get test tokens from the faucet. Current balance: {accountBalance} GEN
            </p>
          </div>
          {#if !requirement2Met}
            <a
              href="https://genlayer-faucet.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
              class="ml-3 px-4 py-2 bg-orange-600 text-white text-sm rounded-md hover:bg-orange-700 transition-colors inline-flex items-center"
            >
              Open Faucet
              <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
            </a>
          {:else}
            <span class="ml-3 px-3 py-2 bg-green-100 text-green-800 text-sm rounded-md">
              ✓ Funded
            </span>
          {/if}
        </div>
      </div>

      <!-- Requirement 3: Deploy Contract -->
      <div class="border border-gray-200 rounded-lg p-4">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="deployContract" 
                bind:checked={hasDeployedContract}
                disabled={!requirement1Met || !requirement2Met}
                class="h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded mr-3 disabled:opacity-50"
              />
              <label for="deployContract" class="text-sm font-medium text-gray-900">
                3. Deploy an Intelligent Contract
              </label>
            </div>
            <p class="text-xs text-gray-600 mt-1 ml-7">
              Use GenLayer Studio to deploy your first contract
            </p>
          </div>
          <a
            href="https://studio.genlayer.com"
            target="_blank"
            rel="noopener noreferrer"
            class="ml-3 px-4 py-2 bg-orange-600 text-white text-sm rounded-md hover:bg-orange-700 transition-colors inline-flex items-center"
          >
            Open Studio
            <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        </div>
      </div>

      <!-- Claim Builder Badge Button -->
      <div class="pt-4">
        <button
          onclick={handleClaimBuilderBadge}
          disabled={!allRequirementsMet || isClaimingBuilderBadge}
          class="w-full inline-flex items-center justify-center px-8 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          <Icon name="builder" className="mr-2 text-white" />
          {#if !$authState.isAuthenticated}
            Connect Wallet to Claim Badge
          {:else if isClaimingBuilderBadge}
            Claiming Badge...
          {:else if !allRequirementsMet}
            Complete All Requirements First
          {:else}
            Claim Builder Welcome Badge
          {/if}
        </button>
        
        {#if error}
          <div class="mt-4 text-red-600 text-sm">{error}</div>
        {/if}
      </div>
    </div>
  </div>
</div>