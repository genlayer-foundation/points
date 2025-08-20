<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { getCurrentUser, journeyAPI } from '../lib/api';
  import Icon from '../components/Icons.svelte';
  
  let currentUser = $state(null);
  let hasDeployedContract = $state(false);
  let isClaimingBadge = $state(false);
  let error = $state('');
  let loading = $state(true);
  
  onMount(async () => {
    await loadData();
  });
  
  async function loadData() {
    try {
      if ($authState.isAuthenticated) {
        currentUser = await getCurrentUser();
      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    } finally {
      loading = false;
    }
  }
  
  async function handleClaimBadge() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }
    
    if (!hasDeployedContract) {
      return;
    }
    
    isClaimingBadge = true;
    error = '';
    
    try {
      await journeyAPI.completeBuilderJourney();
      sessionStorage.setItem('journeySuccess', 'Successfully earned your Builder Welcome badge!');
      push(`/participant/${$authState.address}`);
    } catch (err) {
      error = err.response?.data?.error || 'Failed to claim badge';
      isClaimingBadge = false;
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
        <!-- Step 1: Learn & Build -->
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
        
        <!-- Step 2: Deploy Contract -->
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
        
        <!-- Step 3: Level Up -->
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

  <!-- Start Journey Section -->
  <div class="bg-white shadow-sm rounded-lg p-6 sm:p-8">
    <h2 class="text-xl font-bold text-gray-900 mb-3">Start Your Builder Journey</h2>
    
    <p class="text-gray-700 mb-6">
      Dive into our docs, experiment in the Studio, and deploy your first Intelligent Contract. 
      Claim your Builder badge when you're ready.
    </p>
    
    <div class="space-y-4">
      <div class="flex flex-col sm:flex-row gap-3">
        <a 
          href="https://docs.genlayer.com" 
          target="_blank" 
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center px-5 py-2.5 bg-orange-50 text-orange-700 border border-orange-300 rounded-lg hover:bg-orange-100 transition-colors font-medium"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
          </svg>
          Read Documentation
        </a>
        
        <a 
          href="https://studio.genlayer.com" 
          target="_blank" 
          rel="noopener noreferrer"
          class="inline-flex items-center justify-center px-5 py-2.5 bg-orange-50 text-orange-700 border border-orange-300 rounded-lg hover:bg-orange-100 transition-colors font-medium"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          Open GenLayer Studio
        </a>
      </div>
      
      <div class="pt-2">
        <div class="flex items-start space-x-3 mb-4">
          <input 
            type="checkbox" 
            id="contractDeployed" 
            bind:checked={hasDeployedContract}
            class="mt-0.5 h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded"
          />
          <label for="contractDeployed" class="text-sm text-gray-700">
            I have deployed my first Intelligent Contract in GenLayer Studio
          </label>
        </div>
        
        <button
          onclick={handleClaimBadge}
          disabled={!hasDeployedContract || isClaimingBadge}
          class="inline-flex items-center px-8 py-3 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          <Icon name="builder" className="mr-2 text-white" />
          {#if !$authState.isAuthenticated}
            Connect Wallet to Claim Badge
          {:else if isClaimingBadge}
            Claiming Badge...
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