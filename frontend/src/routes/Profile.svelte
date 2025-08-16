<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getCurrentUser, updateUserProfile } from '../lib/api';
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { getValidatorBalance } from '../lib/blockchain';
  import { journeyAPI } from '../lib/api';
  
  let user = $state(null);
  let name = $state('');
  let nodeVersion = $state('');
  let isSaving = $state(false);
  let error = $state('');
  let balance = $state(null);
  let loadingBalance = $state(false);
  let showValidatorJourney = $state(false);
  let showBuilderJourney = $state(false);
  let isCompletingJourney = $state(false);
  
  // Track if any field has changed
  let hasChanges = $derived(user && (
    name !== (user.name || '') || 
    (user.validator && nodeVersion !== (user.validator?.node_version || ''))
  ));
  
  onMount(async () => {
    try {
      const userData = await getCurrentUser();
      user = userData;
      name = userData.name || '';
      nodeVersion = userData.validator?.node_version || '';
      
      // Fetch validator balance if user has an address
      if (userData.address) {
        loadingBalance = true;
        try {
          balance = await getValidatorBalance(userData.address);
        } catch (err) {
          console.error('Failed to fetch balance:', err);
        } finally {
          loadingBalance = false;
        }
      }
    } catch (err) {
      error = 'Failed to load profile';
      console.error('Error loading profile:', err);
    }
  });
  
  async function handleSave() {
    if (!hasChanges) return;
    
    error = '';
    isSaving = true;
    
    try {
      const updateData = { name };
      // Only include node_version if it has changed
      if (nodeVersion !== (user.validator?.node_version || '')) {
        updateData.node_version = nodeVersion;
      }
      
      const updatedUser = await updateUserProfile(updateData);
      // Update the user store with new data
      userStore.updateUser({ 
        name,
        validator: { 
          ...user.validator,
          node_version: nodeVersion 
        }
      });
      // Store success message in sessionStorage to show on profile page
      sessionStorage.setItem('profileUpdateSuccess', 'Profile updated successfully!');
      // Redirect to public profile
      push(`/participant/${$authState.address}`);
    } catch (err) {
      error = err.message || 'Failed to update profile';
      isSaving = false;
    }
  }
  
  function handleCancel() {
    // Go back to public profile without saving
    push(`/participant/${$authState.address}`);
  }
  
  async function startValidatorJourney() {
    showValidatorJourney = true;
  }
  
  async function startBuilderJourney() {
    showBuilderJourney = true;
  }
  
  async function completeValidatorJourney() {
    error = '';
    isCompletingJourney = true;
    
    try {
      const response = await journeyAPI.completeValidatorJourney();
      // Reload user data to get updated badges
      const userData = await getCurrentUser();
      user = userData;
      showValidatorJourney = false;
      alert('Validator waitlist badge awarded! +20 points earned.');
    } catch (err) {
      error = err.response?.data?.error || 'Failed to complete journey';
    } finally {
      isCompletingJourney = false;
    }
  }
  
  async function completeBuilderJourney() {
    error = '';
    isCompletingJourney = true;
    
    try {
      const response = await journeyAPI.completeBuilderJourney();
      // Reload user data to get updated badges
      const userData = await getCurrentUser();
      user = userData;
      showBuilderJourney = false;
      alert('Builder initiate badge awarded! +20 points earned.');
    } catch (err) {
      error = err.response?.data?.error || 'Failed to complete journey';
    } finally {
      isCompletingJourney = false;
    }
  }
</script>

<div class="space-y-6">
  <!-- Header with title and buttons -->
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">Edit Profile</h1>
    <div class="flex gap-2">
      <button
        onclick={handleSave}
        disabled={isSaving || !hasChanges}
        class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
      >
        {isSaving ? 'Saving...' : 'Save Changes'}
      </button>
      <button
        onclick={handleCancel}
        disabled={isSaving}
        class="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
      >
        Cancel
      </button>
    </div>
  </div>

  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {/if}

  {#if user}
    <!-- Basic Information -->
    <div class="bg-white shadow rounded-lg p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">Basic Information</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Wallet Address</label>
          <p class="text-gray-900 font-mono text-sm break-all bg-gray-50 px-3 py-2 rounded">{user.address || 'Not connected'}</p>
        </div>
        
        {#if user.address}
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Balance</label>
            {#if loadingBalance}
              <p class="text-gray-500 bg-gray-50 px-3 py-2 rounded">Loading...</p>
            {:else if balance}
              <p class="text-gray-900 font-mono text-sm bg-gray-50 px-3 py-2 rounded">{balance.formatted} GEN</p>
            {:else}
              <p class="text-gray-500 bg-gray-50 px-3 py-2 rounded">Unable to fetch</p>
            {/if}
          </div>
        {/if}
      </div>
      
      <div class="mt-4">
        <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
        <input
          id="name"
          type="text"
          bind:value={name}
          class="w-full md:w-1/2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Enter your display name"
          disabled={isSaving}
        />
        <p class="mt-1 text-xs text-gray-500">This name will be displayed on leaderboards and profiles</p>
      </div>
      
      {#if user.validator && !showValidatorJourney && !showBuilderJourney}
        <div class="mt-6 pt-6 border-t border-gray-200">
          <label for="nodeVersion" class="block text-sm font-medium text-gray-700 mb-2">
            Node Version
          </label>
          
          {#if user?.validator?.target_version}
            {#if user?.validator?.matches_target}
              <div class="bg-green-50 border border-green-200 rounded-md p-2 mb-2 text-sm">
                <span class="text-green-800">✓ Up to date with target {user.validator.target_version}</span>
              </div>
            {:else}
              <div class="bg-yellow-50 border border-yellow-200 rounded-md p-2 mb-2 text-sm">
                <span class="text-yellow-800">⚠ Update to {user.validator.target_version}</span>
              </div>
            {/if}
          {/if}
          
          <input
            id="nodeVersion"
            type="text"
            bind:value={nodeVersion}
            class="w-full md:w-1/2 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 0.3.9"
            disabled={isSaving}
          />
          <p class="mt-1 text-xs text-gray-500">Enter your current GenLayer node version</p>
        </div>
      {/if}
      
      {#if user.leaderboard_entry}
        <div class="mt-6 pt-6 border-t border-gray-200">
          <h3 class="text-sm font-medium text-gray-900 mb-3">Global Stats</h3>
          <div class="grid grid-cols-2 gap-4 max-w-sm">
            <div class="bg-gray-50 rounded-md p-3">
              <p class="text-2xl font-bold text-gray-900">{user.leaderboard_entry.total_points || 0}</p>
              <p class="text-xs text-gray-600">Total Points</p>
            </div>
            <div class="bg-gray-50 rounded-md p-3">
              <p class="text-2xl font-bold text-gray-900">#{user.leaderboard_entry.rank || '—'}</p>
              <p class="text-xs text-gray-600">Global Rank</p>
            </div>
          </div>
        </div>
      {/if}
    </div>
    
    <!-- Journey Status Section -->
    {#if !showValidatorJourney && !showBuilderJourney}
      <div class="bg-white shadow rounded-lg p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">Journey Status</h2>
        
        <div class="space-y-3">
          <!-- Validator Journey Status -->
          <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-sky-100 rounded-full flex items-center justify-center">
                <svg class="w-5 h-5 text-sky-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                  <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                </svg>
              </div>
              <div>
                <p class="font-medium text-gray-900">Validator</p>
                <p class="text-sm text-gray-500">
                  {#if user.validator}
                    Active Validator
                  {:else if user.has_validator_waitlist}
                    Journey Started - On Waitlist
                  {:else}
                    Not Started
                  {/if}
                </p>
              </div>
            </div>
            {#if !user.validator && !user.has_validator_waitlist}
              <button
                onclick={startValidatorJourney}
                class="px-4 py-2 bg-sky-600 text-white rounded-md hover:bg-sky-700 transition-colors text-sm"
              >
                Start Journey
              </button>
            {:else if user.has_validator_waitlist && !user.validator}
              <span class="inline-flex items-center px-3 py-1 rounded-full bg-sky-100 text-sky-800 text-sm">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
                +20 Points Earned
              </span>
            {:else}
              <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Active
              </span>
            {/if}
          </div>
          
          <!-- Builder Journey Status -->
          <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                <svg class="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
              </div>
              <div>
                <p class="font-medium text-gray-900">Builder</p>
                <p class="text-sm text-gray-500">
                  {#if user.builder}
                    Active Builder
                  {:else if user.has_builder_initiate}
                    Journey Started - Initiate Badge Earned
                  {:else}
                    Not Started
                  {/if}
                </p>
              </div>
            </div>
            {#if !user.builder && !user.has_builder_initiate}
              <button
                onclick={startBuilderJourney}
                class="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors text-sm"
              >
                Start Journey
              </button>
            {:else if user.has_builder_initiate && !user.builder}
              <span class="inline-flex items-center px-3 py-1 rounded-full bg-orange-100 text-orange-800 text-sm">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
                +20 Points Earned
              </span>
            {:else}
              <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Active
              </span>
            {/if}
          </div>
          
          <!-- Steward Journey Status -->
          <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clip-rule="evenodd"/>
                </svg>
              </div>
              <div>
                <p class="font-medium text-gray-900">Steward</p>
                <p class="text-sm text-gray-500">
                  {#if user.steward}
                    Active Steward
                  {:else}
                    Coming Soon
                  {/if}
                </p>
              </div>
            </div>
            {#if user.steward}
              <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800 text-sm">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Active
              </span>
            {:else}
              <span class="inline-flex items-center px-3 py-1 rounded-full bg-gray-100 text-gray-600 text-sm">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v4a1 1 0 002 0V7zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
                </svg>
                Coming Soon
              </span>
            {/if}
          </div>
        </div>
      </div>
    {/if}
    
    <!-- Journey Detail Views -->
    {#if showValidatorJourney}
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">Validator Journey</h2>
          <button
            onclick={() => showValidatorJourney = false}
            class="text-gray-400 hover:text-gray-600"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        
        <p class="text-gray-600 mb-4">Complete the interest form to join the validator waitlist and earn 20 points!</p>
        
        <div class="bg-sky-50 border border-sky-200 rounded-lg p-4 mb-4">
          <h3 class="font-medium text-sky-900 mb-2">Requirements:</h3>
          <ul class="space-y-2 text-sm text-sky-700">
            <li class="flex items-start">
              <svg class="w-4 h-4 text-sky-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              Complete the validator interest form
            </li>
            <li class="flex items-start">
              <svg class="w-4 h-4 text-sky-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              Provide your technical background
            </li>
            <li class="flex items-start">
              <svg class="w-4 h-4 text-sky-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              Join the validator waitlist
            </li>
          </ul>
        </div>
        
        <button
          onclick={completeValidatorJourney}
          disabled={isCompletingJourney}
          class="w-full px-4 py-2 bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isCompletingJourney ? 'Processing...' : 'Complete Validator Journey (Demo)'}
        </button>
      </div>
    {/if}
    
    {#if showBuilderJourney}
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">Builder Journey</h2>
          <button
            onclick={() => showBuilderJourney = false}
            class="text-gray-400 hover:text-gray-600"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
        
        <p class="text-gray-600 mb-4">Deploy your first smart contract to earn the Builder Initiate badge and 20 points!</p>
        
        <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-4">
          <h3 class="font-medium text-orange-900 mb-2">Requirements:</h3>
          <ul class="space-y-2 text-sm text-orange-700">
            <li class="flex items-start">
              <svg class="w-4 h-4 text-orange-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              Deploy a smart contract using GenLayer Studio
            </li>
            <li class="flex items-start">
              <svg class="w-4 h-4 text-orange-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              Complete the builder tutorial
            </li>
          </ul>
        </div>
        
        <div class="bg-yellow-50 border border-yellow-200 rounded-md p-3 mb-4">
          <p class="text-xs text-yellow-700">
            <strong>Note:</strong> Builder tools are coming soon. For now, you can manually claim your initiate badge to get started!
          </p>
        </div>
        
        <button
          onclick={completeBuilderJourney}
          disabled={isCompletingJourney}
          class="w-full px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isCompletingJourney ? 'Processing...' : 'Claim Builder Initiate Badge (Demo)'}
        </button>
      </div>
    {/if}
    
  {:else if !error}
    <div class="bg-white shadow rounded-lg p-8">
      <div class="text-center">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto"></div>
        <p class="text-gray-500 mt-4">Loading profile...</p>
      </div>
    </div>
  {/if}
</div>