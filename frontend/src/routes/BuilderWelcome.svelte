<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { getCurrentUser, journeyAPI, usersAPI, githubAPI } from '../lib/api';
  import { getValidatorBalance } from '../lib/blockchain';
  import Icon from '../components/Icons.svelte';
  import BuilderProgress from '../components/BuilderProgress.svelte';
  import GitHubLink from '../components/GitHubLink.svelte';

  let currentUser = $state(null);
  let hasBuilderWelcome = $state(false);
  let isClaimingBuilderBadge = $state(false);
  let testnetBalance = $state(null);
  let hasDeployedContract = $state(false);
  let hasSubmittedContribution = $state(false);
  let githubUsername = $state('');
  let hasStarredRepo = $state(false);
  let repoToStar = $state('genlayerlabs/genlayer-project-boilerplate');
  let isCheckingRepoStar = $state(false);
  let error = $state('');
  let loading = $state(true);
  let isRefreshingBalance = $state(false);
  let isCheckingDeployments = $state(false);
  let hasCheckedDeploymentsOnce = $state(false);
  let showStudioInstructions = $state(false);
  let isCompletingJourney = $state(false);

  // Debounce utility to prevent button spam
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Derived states for requirements
  let requirement1Met = $derived(hasBuilderWelcome);
  let requirement2Met = $derived(!!githubUsername);
  let requirement3Met = $derived(hasStarredRepo);
  let requirement4Met = $derived(testnetBalance > 0);
  let requirement5Met = $derived(hasDeployedContract);
  let allRequirementsMet = $derived(requirement1Met && requirement2Met && requirement3Met && requirement4Met && requirement5Met);
  let hasCalledComplete = $state(false);
  
  // Auto-complete journey when all requirements are met
  $effect(() => {
    if (allRequirementsMet && !hasCalledComplete && $authState.isAuthenticated && !isCompletingJourney) {
      hasCalledComplete = true;
      // If we already know deployments exist, just complete immediately
      completeBuilderJourney();
    }
  });
  
  onMount(async () => {
    await loadData();
  });
  
  async function loadData() {
    try {
      if ($authState.isAuthenticated) {
        currentUser = await getCurrentUser();
        hasBuilderWelcome = currentUser?.has_builder_welcome || false;
        hasSubmittedContribution = (currentUser?.builder?.total_contributions || 0) > 0;
        githubUsername = currentUser?.github_username || '';
        // Removed all automatic checks - user must manually refresh each requirement
        // - checkTestnetBalance() - Removed: only check when user clicks refresh
        // - checkDeployments() - Removed: only check when user clicks refresh
        // - checkRepoStar() - Removed: only check when user clicks refresh
      }
    } catch (err) {
      // Failed to load user data
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
      testnetBalance = 0;
    }
  }
  
  
  async function checkDeployments() {
    // Show spinner on first check
    if (!hasCheckedDeploymentsOnce) {
      isCheckingDeployments = true;
    }
    
    try {
      const response = await usersAPI.getDeploymentStatus();
      hasDeployedContract = response.data.has_deployments || false;
    } catch (err) {
      hasDeployedContract = false;
    } finally {
      hasCheckedDeploymentsOnce = true;
      isCheckingDeployments = false;
    }
  }
  
  async function refreshDeployments() {
    // Manual refresh of deployment status
    isCheckingDeployments = true;
    try {
      await checkDeployments();
      
      // If deployments detected and all requirements met, complete immediately
      if (hasDeployedContract && requirement1Met && requirement2Met && !hasCalledComplete) {
        hasCalledComplete = true;
        await completeBuilderJourney();
      }
      // Show instructions if still no deployments after manual check
      else if (!hasDeployedContract && hasCheckedDeploymentsOnce) {
        showStudioInstructions = true;
      }
    } finally {
      isCheckingDeployments = false;
    }
  }
  
  function openStudioWithInstructions() {
    // Show instructions popup (Studio will be opened from the popup button)
    showStudioInstructions = true;
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
      testnetBalance = 0;
    } finally {
      isRefreshingBalance = false;
    }
  }

  async function checkRepoStar() {
    if (!githubUsername) return;

    isCheckingRepoStar = true;
    try {
      const response = await githubAPI.checkStar();
      hasStarredRepo = response.data.has_starred;
      repoToStar = response.data.repo || 'genlayerlabs/genlayer-project-boilerplate';
    } catch (err) {
      hasStarredRepo = false;
    } finally {
      isCheckingRepoStar = false;
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
  
  async function handleGitHubLinked(updatedUser) {
    // Update local state with the updated user info
    currentUser = updatedUser;
    hasBuilderWelcome = updatedUser?.has_builder_welcome || false;
    hasSubmittedContribution = (updatedUser?.builder?.total_contributions || 0) > 0;
    githubUsername = updatedUser?.github_username || '';
  }

  async function completeBuilderJourney() {
    if (!$authState.isAuthenticated || !allRequirementsMet) {
      return;
    }

    // Don't re-check deployments if we already know they exist
    // Just proceed with completion
    isCompletingJourney = true;

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
        // Reset flag to allow retry
        hasCalledComplete = false;
      }
    } finally {
      isCompletingJourney = false;
    }
  }

  // Create debounced versions AFTER all functions are defined (500ms delay)
  const debouncedRefreshBalance = debounce(refreshBalance, 500);
  const debouncedRefreshDeployments = debounce(refreshDeployments, 500);
  const debouncedCheckRepoStar = debounce(checkRepoStar, 500);

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
      githubUsername={githubUsername}
      hasStarredRepo={hasStarredRepo}
      repoToStar={repoToStar}
      showActions={true}
      colorTheme="orange"
      onClaimBuilderBadge={claimBuilderWelcome}
      isClaimingBuilderBadge={isClaimingBuilderBadge}
      onRefreshBalance={debouncedRefreshBalance}
      isRefreshingBalance={isRefreshingBalance}
      onCheckRequirements={checkRequirements}
      isCheckingRequirements={false}
      onCheckDeployments={debouncedRefreshDeployments}
      isCheckingDeployments={isCheckingDeployments}
      onOpenStudio={openStudioWithInstructions}
      onGitHubLinked={handleGitHubLinked}
      onCheckRepoStar={debouncedCheckRepoStar}
      isCheckingRepoStar={isCheckingRepoStar}
    />

      <!-- Status Message -->
      {#if isCompletingJourney}
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
      
  </div>

  <!-- Studio Instructions Modal -->
  {#if showStudioInstructions}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onclick={() => showStudioInstructions = false}>
      <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white" onclick={(e) => e.stopPropagation()}>
        <div class="mt-3">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg leading-6 font-medium text-gray-900">
              Connect Your Wallet in Studio
            </h3>
            <button
              onclick={() => showStudioInstructions = false}
              class="text-gray-400 hover:text-gray-500"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
          
          <div class="mt-2 px-2 py-3">
            <p class="text-sm text-gray-600 mb-4">
              To deploy contracts on GenLayer Studio, you need to:
            </p>
            
            <ol class="text-sm text-gray-600 space-y-3 list-decimal list-inside">
              <li>
                <span class="font-medium">Connect your wallet</span> in GenLayer Studio using the same address: 
                <code class="text-xs bg-gray-100 px-1 py-0.5 rounded break-all">{$authState.address}</code>
              </li>
              <li>
                <span class="font-medium">Deploy your contract</span> using the Studio interface
              </li>
              <li>
                <span class="font-medium">Return here and click refresh</span> to verify your deployment
              </li>
            </ol>
            
            <div class="mt-4 p-3 bg-orange-50 rounded-md">
              <p class="text-xs text-orange-800">
                <strong>Important:</strong> Make sure to use the same wallet address in Studio that you're using here.
              </p>
            </div>
          </div>
          
          <div class="flex gap-3 mt-5">
            <button
              onclick={() => showStudioInstructions = false}
              class="flex-1 px-4 py-2 bg-gray-200 text-gray-800 text-base font-medium rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-300"
            >
              Close
            </button>
            <button
              onclick={() => {
                showStudioInstructions = false;
                window.open('https://studio.genlayer.com', '_blank', 'noopener,noreferrer');
              }}
              class="flex-1 px-4 py-2 bg-orange-600 text-white text-base font-medium rounded-md hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-300"
            >
              Open Studio
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>