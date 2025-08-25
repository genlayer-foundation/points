<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { getCurrentUser, journeyAPI, usersAPI } from '../lib/api';
  import { getValidatorBalance } from '../lib/blockchain';
  import Icon from '../components/Icons.svelte';
  import BuilderProgress from '../components/BuilderProgress.svelte';
  
  let currentUser = $state(null);
  let hasBuilderWelcome = $state(false);
  let isClaimingBuilderBadge = $state(false);
  let testnetBalance = $state(null);
  let hasDeployedContract = $state(false);
  let hasSubmittedContribution = $state(false);
  let error = $state('');
  let loading = $state(true);
  let isRefreshingBalance = $state(false);
  
  // Derived states for requirements
  let requirement1Met = $derived(hasBuilderWelcome);
  let requirement2Met = $derived(testnetBalance > 0);
  let requirement3Met = $derived(hasDeployedContract);
  let allRequirementsMet = $derived(requirement1Met && requirement2Met && requirement3Met);
  let hasCalledComplete = $state(false);
  
  // Auto-complete journey when all requirements are met
  $effect(() => {
    if (allRequirementsMet && !hasCalledComplete && $authState.isAuthenticated) {
      hasCalledComplete = true;
      completeBuilderJourney();
    }
  });
  
  onMount(async () => {
    await loadData();
    // Check balance periodically
    const interval = setInterval(async () => {
      // Balance check removed - we get balance from RPC
    }, 5000); // Check every 5 seconds
    
    return () => clearInterval(interval);
  });
  
  async function loadData() {
    try {
      if ($authState.isAuthenticated) {
        currentUser = await getCurrentUser();
        hasBuilderWelcome = currentUser?.has_builder_welcome || false;
        hasSubmittedContribution = (currentUser?.builder?.total_contributions || 0) > 0;
        await checkTestnetBalance();
        await checkDeployments();
      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    } finally {
      loading = false;
    }
  }
  
  async function checkTestnetBalance() {
    try {
      if ($authState.address) {
        const result = await getValidatorBalance($authState.address);
        testnetBalance = parseFloat(result.formatted);
      }
    } catch (err) {
      console.error('Failed to check testnet balance:', err);
      testnetBalance = 0;
    }
  }
  
  
  async function checkDeployments() {
    try {
      const response = await usersAPI.getDeploymentStatus();
      hasDeployedContract = response.data.has_deployments || false;
    } catch (err) {
      console.error('Failed to check deployments:', err);
      hasDeployedContract = false;
    }
  }
  
  async function refreshBalance() {
    if (!$authState.isAuthenticated || !$authState.address) {
      return;
    }
    
    isRefreshingBalance = true;
    try {
      const result = await getValidatorBalance($authState.address);
      testnetBalance = parseFloat(result.formatted);
    } catch (err) {
      console.error('Failed to refresh balance:', err);
      testnetBalance = 0;
    } finally {
      isRefreshingBalance = false;
    }
  }
  
  async function checkRequirements() {
    // Check balance and deployments
    await Promise.all([
      refreshBalance(),
      checkDeployments()
    ]);
  }

  async function claimBuilderWelcome() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }
    
    isClaimingBuilderBadge = true;
    error = '';
    
    try {
      await journeyAPI.startBuilderJourney();
      // Reload user data to get updated contribution status
      currentUser = await getCurrentUser();
      hasBuilderWelcome = currentUser?.has_builder_welcome || false;
    } catch (err) {
      error = err.response?.data?.error || 'Failed to claim builder contribution';
    } finally {
      isClaimingBuilderBadge = false;
    }
  }
  
  async function completeBuilderJourney() {
    if (!$authState.isAuthenticated || !allRequirementsMet) {
      return;
    }
    
    try {
      const response = await journeyAPI.completeBuilderJourney();
      
      // If successful, redirect to profile with success message
      if (response.status === 201) {
        // New builder created
        sessionStorage.setItem('builderJourneySuccess', 'true');
        push(`/participant/${$authState.address}`);
      } else if (response.status === 200) {
        // Already a builder, just redirect
        push(`/participant/${$authState.address}`);
      }
    } catch (err) {
      // If already has the contribution and Builder profile, redirect anyway
      if (err.response?.status === 200) {
        push(`/participant/${$authState.address}`);
      } else {
        console.error('Failed to complete builder journey:', err);
        // Reset flag to allow retry
        hasCalledComplete = false;
      }
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
    <h2 class="text-xl font-bold text-gray-900 mb-3">Builder Journey Requirements</h2>
    
    <p class="text-gray-700 mb-6">
      Complete these requirements to become a GenLayer Builder:
    </p>
    
    <BuilderProgress 
      testnetBalance={testnetBalance}
      hasBuilderWelcome={hasBuilderWelcome}
      hasDeployedContract={hasDeployedContract}
      showActions={true}
      colorTheme="orange"
      onClaimBuilderBadge={claimBuilderWelcome}
      isClaimingBuilderBadge={isClaimingBuilderBadge}
      onRefreshBalance={refreshBalance}
      isRefreshingBalance={isRefreshingBalance}
      onCheckRequirements={checkRequirements}
      isCheckingRequirements={false}
    />

      <!-- Status Message -->
      {#if allRequirementsMet && !hasCalledComplete}
        <div class="pt-4">
          <div class="w-full inline-flex items-center justify-center px-8 py-3 bg-green-100 text-green-800 rounded-lg font-medium shadow-sm">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Completing your Builder Journey...
          </div>
        </div>
      {:else if hasBuilderWelcome || (allRequirementsMet && hasCalledComplete)}
        <div class="pt-4">
          <button
            onclick={() => push(`/participant/${$authState.address}`)}
            class="w-full inline-flex items-center justify-center px-8 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors shadow-sm"
          >
            <Icon name="builder" className="mr-2 text-white" />
            View Your Profile
          </button>
        </div>
      {/if}
      
      {#if error}
        <div class="mt-4 text-red-600 text-sm">{error}</div>
      {/if}
    </div>
  </div>