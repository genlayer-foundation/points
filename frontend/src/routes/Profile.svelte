<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getCurrentUser, updateUserProfile } from '../lib/api';
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { getValidatorBalance } from '../lib/blockchain';
  import { journeyAPI } from '../lib/api';
  import Icon from '../components/Icons.svelte';
  
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
  let showJourneyConfirm = $state(null); // 'validator' or 'builder'
  let journeySuccessMessage = $state('');
  
  // Track if any field has changed
  let hasChanges = $derived(user && (
    name !== (user.name || '') || 
    (user.validator && nodeVersion !== (user.validator?.node_version || ''))
  ));
  
  // Format date helper
  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  }
  
  onMount(async () => {
    try {
      const userData = await getCurrentUser();
      user = userData;
      name = userData.name || '';
      nodeVersion = userData.validator?.node_version || '';
      
      // Check for journey success message
      const journeySuccess = sessionStorage.getItem('journeySuccess');
      if (journeySuccess) {
        journeySuccessMessage = journeySuccess;
        sessionStorage.removeItem('journeySuccess');
        // Auto-hide after 5 seconds
        setTimeout(() => {
          journeySuccessMessage = '';
        }, 5000);
      }
      
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
    showJourneyConfirm = 'validator';
  }
  
  async function startBuilderJourney() {
    showJourneyConfirm = 'builder';
  }
  
  async function confirmJourney(type) {
    if (type === 'validator') {
      await completeValidatorJourney();
    } else if (type === 'builder') {
      await completeBuilderJourney();
    }
    showJourneyConfirm = null;
    
    // Scroll to the relevant profile section after a short delay
    setTimeout(() => {
      const element = document.querySelector(`[data-profile-type="${type}"]`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);
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
      // Show success message in a nicer way
      sessionStorage.setItem('journeySuccess', 'Validator waitlist badge awarded! +20 points earned.');
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
      // Show success message in a nicer way
      sessionStorage.setItem('journeySuccess', 'Builder initiate badge awarded! +20 points earned.');
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
  
  {#if journeySuccessMessage}
    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded flex items-center justify-between">
      <div class="flex items-center">
        <Icon name="star" className="mr-2" />
        <span>{journeySuccessMessage}</span>
      </div>
      <button 
        onclick={() => journeySuccessMessage = ''}
        class="text-green-700 hover:text-green-900"
      >
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
        </svg>
      </button>
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
    
    <!-- Validator Profile -->
    {#if !showValidatorJourney && !showBuilderJourney}
      {#if user.validator}
        <div class="bg-sky-100 shadow rounded-lg p-6 border border-sky-300" data-profile-type="validator">
          <h2 class="text-lg font-semibold text-sky-900 mb-4 flex items-center">
            <Icon name="validator" className="mr-2 text-sky-700" />
            Validator Profile
          </h2>
          <div class="text-sm text-sky-800">
            <p>You're running a validator node! Keep it up.</p>
            {#if user.validator.total_points}
              <p class="mt-1">Total Points: <span class="font-bold text-sky-900">{user.validator.total_points}</span></p>
            {/if}
            {#if user.validator.rank}
              <p>Validator Rank: <span class="font-bold text-sky-900">#{user.validator.rank}</span></p>
            {/if}
          </div>
        </div>
      {:else if user.has_validator_waitlist}
        <div class="bg-sky-100 shadow rounded-lg p-6 border border-sky-300" data-profile-type="validator">
          <h2 class="text-lg font-semibold text-sky-900 mb-4 flex items-center">
            <Icon name="validator" className="mr-2 text-sky-700" />
            Validator Profile
          </h2>
          <p class="text-sm text-sky-800">You're on the waitlist! Keep earning points to become a validator.</p>
          <div class="mt-3 inline-flex items-center px-2 py-1 rounded-full bg-sky-200 text-sky-900 text-xs">
            <Icon name="star" size="xs" className="mr-1" />
            +20 Points Earned
          </div>
        </div>
      {:else}
        <div class="bg-sky-50 shadow rounded-lg p-6 border border-sky-200">
          <h2 class="text-lg font-semibold text-sky-900 mb-4 flex items-center">
            <Icon name="validator" className="mr-2 text-sky-500" />
            Validator Profile
          </h2>
          <p class="text-sm text-sky-700 mb-2">Want to become a GenLayer Validator? Join the waitlist, start earning points, and climb the ranks.</p>
          <p class="text-sm text-sky-700 mb-4">Top contributors will be invited to run nodes on Testnet Asimov.</p>
          <button
            onclick={startValidatorJourney}
            class="px-3 py-1.5 bg-sky-600 text-white rounded text-sm hover:bg-sky-700 transition-colors"
          >
            Start Validator Journey →
          </button>
        </div>
      {/if}
      
      <!-- Builder Profile -->
      {#if user.builder}
        <div class="bg-orange-100 shadow rounded-lg p-6 border border-orange-300" data-profile-type="builder">
          <h2 class="text-lg font-semibold text-orange-900 mb-4 flex items-center">
            <Icon name="builder" className="mr-2 text-orange-700" />
            Builder Profile
          </h2>
          <div class="text-sm text-orange-800">
            <p>You're building on GenLayer! Keep creating.</p>
            {#if user.builder.total_points}
              <p class="mt-1">Total Points: <span class="font-bold text-orange-900">{user.builder.total_points}</span></p>
            {/if}
            {#if user.builder.rank}
              <p>Builder Rank: <span class="font-bold text-orange-900">#{user.builder.rank}</span></p>
            {/if}
          </div>
        </div>
      {:else if user.has_builder_initiate}
        <div class="bg-orange-100 shadow rounded-lg p-6 border border-orange-300" data-profile-type="builder">
          <h2 class="text-lg font-semibold text-orange-900 mb-4 flex items-center">
            <Icon name="builder" className="mr-2 text-orange-700" />
            Builder Profile
          </h2>
          <p class="text-sm text-orange-800">You've started building! Keep deploying contracts to level up.</p>
          <div class="mt-3 inline-flex items-center px-2 py-1 rounded-full bg-orange-200 text-orange-900 text-xs">
            <Icon name="star" size="xs" className="mr-1" />
            +20 Points Earned
          </div>
        </div>
      {:else}
        <div class="bg-orange-50 shadow rounded-lg p-6 border border-orange-200">
          <h2 class="text-lg font-semibold text-orange-900 mb-4 flex items-center">
            <Icon name="builder" className="mr-2 text-orange-500" />
            Builder Profile
          </h2>
          <p class="text-sm text-orange-700 mb-2">Start building on GenLayer. Deploy contracts, earn points, and join our growing developer community.</p>
          <p class="text-sm text-orange-700 mb-4">Top contributors get special rewards.</p>
          <button
            onclick={startBuilderJourney}
            class="px-3 py-1.5 bg-orange-600 text-white rounded text-sm hover:bg-orange-700 transition-colors"
          >
            Start Builder Journey →
          </button>
        </div>
      {/if}
      
      <!-- Steward Profile -->
      {#if user.steward}
        <div class="bg-green-100 shadow rounded-lg p-6 border border-green-300">
          <h2 class="text-lg font-semibold text-green-900 mb-4 flex items-center">
            <Icon name="steward" className="mr-2 text-green-700" />
            Steward Profile
          </h2>
          <div class="text-sm">
            <p class="text-green-800 font-medium">
              Thanks for keeping things running smoothly around here 🛡️
            </p>
            <p class="text-gray-700 mt-2">
              Your steward profile is active. You have access to review and manage community submissions.
            </p>
            <p class="text-xs text-green-700 mt-3">Profile created: {formatDate(user.steward.created_at)}</p>
          </div>
        </div>
      {:else}
        <div class="bg-green-50 shadow rounded-lg p-6 border border-green-200">
          <h2 class="text-lg font-semibold text-green-900 mb-4 flex items-center">
            <Icon name="steward" className="mr-2 text-green-600" />
            Steward Profile
          </h2>
          <p class="text-sm text-green-700 mb-2">Steward positions are earned through exceptional contribution.</p>
          <p class="text-sm text-green-700">Keep building, validating, and supporting the community to unlock this role.</p>
        </div>
      {/if}
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
  
  <!-- Journey Confirmation Modal -->
  {#if showJourneyConfirm}
    <div class="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <div class="flex items-center mb-4">
          {#if showJourneyConfirm === 'validator'}
            <Icon name="validator" className="mr-3 text-sky-500" size="lg" />
            <h2 class="text-xl font-semibold text-gray-900">Start Validator Journey?</h2>
          {:else}
            <Icon name="builder" className="mr-3 text-orange-500" size="lg" />
            <h2 class="text-xl font-semibold text-gray-900">Start Builder Journey?</h2>
          {/if}
        </div>
        
        <div class="mb-6">
          {#if showJourneyConfirm === 'validator'}
            <p class="text-gray-600 mb-3">By joining the Validator Journey, you'll:</p>
            <ul class="space-y-2 text-sm text-gray-700">
              <li class="flex items-start">
                <Icon name="star" size="xs" className="mr-2 text-sky-500 mt-0.5" />
                <span>Join the validator waitlist</span>
              </li>
              <li class="flex items-start">
                <Icon name="star" size="xs" className="mr-2 text-sky-500 mt-0.5" />
                <span>Earn 20 points immediately</span>
              </li>
              <li class="flex items-start">
                <Icon name="star" size="xs" className="mr-2 text-sky-500 mt-0.5" />
                <span>Get priority for node allocation on Testnet Asimov</span>
              </li>
            </ul>
          {:else}
            <p class="text-gray-600 mb-3">By joining the Builder Journey, you'll:</p>
            <ul class="space-y-2 text-sm text-gray-700">
              <li class="flex items-start">
                <Icon name="star" size="xs" className="mr-2 text-orange-500 mt-0.5" />
                <span>Get the Builder Initiate badge</span>
              </li>
              <li class="flex items-start">
                <Icon name="star" size="xs" className="mr-2 text-orange-500 mt-0.5" />
                <span>Earn 20 points immediately</span>
              </li>
              <li class="flex items-start">
                <Icon name="star" size="xs" className="mr-2 text-orange-500 mt-0.5" />
                <span>Unlock builder-specific rewards and features</span>
              </li>
            </ul>
          {/if}
        </div>
        
        <div class="flex gap-3">
          <button
            onclick={() => confirmJourney(showJourneyConfirm)}
            disabled={isCompletingJourney}
            class="flex-1 px-4 py-2 {showJourneyConfirm === 'validator' ? 'bg-sky-600 hover:bg-sky-700' : 'bg-orange-600 hover:bg-orange-700'} text-white rounded-md transition-colors disabled:opacity-50"
          >
            {isCompletingJourney ? 'Starting...' : 'Yes, Start Journey'}
          </button>
          <button
            onclick={() => showJourneyConfirm = null}
            disabled={isCompletingJourney}
            class="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>