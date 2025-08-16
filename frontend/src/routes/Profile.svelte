<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getCurrentUser, updateUserProfile } from '../lib/api';
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { getValidatorBalance } from '../lib/blockchain';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Icon from '../components/Icons.svelte';
  
  let user = $state(null);
  let name = $state('');
  let nodeVersion = $state('');
  let isSaving = $state(false);
  let error = $state('');
  let balance = $state(null);
  let loadingBalance = $state(false);
  
  // Determine user type
  let userType = $derived(
    !user ? null :
    user.validator ? 'validator' :
    user.builder ? 'builder' :
    user.steward ? 'steward' :
    'participant'
  );
  
  // Get type-specific color theme
  let typeColor = $derived(
    userType === 'validator' ? 'sky' :
    userType === 'builder' ? 'orange' :
    userType === 'steward' ? 'green' :
    'gray'
  );
  
  // Track if any field has changed
  let hasChanges = $derived(user && (
    name !== (user.name || '') || 
    (userType === 'validator' && nodeVersion !== (user.validator?.node_version || ''))
  ));
  
  // Calculate days since target was set
  let daysSinceTarget = $derived(() => {
    if (!user?.validator?.target_created_at) return null;
    const created = new Date(user.validator.target_created_at);
    const now = new Date();
    const diff = now - created;
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  });
  
  // Humanize time since target was set
  function humanizeTimeSince(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (minutes < 60) {
      return minutes === 1 ? '1 minute ago' : `${minutes} minutes ago`;
    } else if (hours < 24) {
      return hours === 1 ? '1 hour ago' : `${hours} hours ago`;
    } else if (days < 7) {
      return days === 1 ? '1 day ago' : `${days} days ago`;
    } else if (days < 30) {
      const weeks = Math.floor(days / 7);
      return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`;
    } else {
      const months = Math.floor(days / 30);
      return months === 1 ? '1 month ago' : `${months} months ago`;
    }
  }
  
  // Format date nicely
  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric' 
    });
  }
  
  // Get points for current day
  function getPointsForDay(day) {
    if (day <= 0) return 4;
    if (day === 1) return 3;
    if (day === 2) return 2;
    return 1;
  }
  
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
          // Don't show error, just leave balance as null
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
</script>

<div class="max-w-2xl mx-auto p-6">
  <h1 class="text-3xl font-bold mb-6">Edit Profile</h1>
  
  {#if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
      {error}
    </div>
  {/if}
  
  {#if user}
    <div class="bg-white shadow rounded-lg p-6">
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Wallet Address</label>
          <p class="text-gray-900 font-mono text-sm">{user.address || 'Not connected'}</p>
        </div>
        
        {#if user.address}
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Balance</label>
          {#if loadingBalance}
            <p class="text-gray-500">Loading balance...</p>
          {:else if balance}
            <p class="text-gray-900 font-mono text-sm">{balance.formatted} GEN</p>
          {:else}
            <p class="text-gray-500">Unable to fetch balance</p>
          {/if}
        </div>
        {/if}
        
        <div>
          <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
          <input
            id="name"
            type="text"
            bind:value={name}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter your display name"
            disabled={isSaving}
          />
          <p class="mt-1 text-sm text-gray-500">This name will be displayed on your public profile</p>
        </div>
        
        <!-- Category-specific sections -->
        <div class="border-t pt-4 space-y-6">
          <h2 class="text-lg font-semibold text-gray-900">Category Profiles</h2>
          
          <!-- Validator Profile -->
          {#if user.validator}
            <div class="bg-sky-50 rounded-lg p-4 border-2 border-sky-200">
              <h3 class="text-md font-medium text-sky-900 mb-3 flex items-center">
                <Icon name="validator" size="sm" className="mr-2 text-sky-600" />
                Validator Profile
              </h3>
              <div>
            <label for="nodeVersion" class="block text-sm font-medium text-gray-700 mb-2">
              Node Version
            </label>
          
          {#if user?.validator?.target_version}
            <!-- Status Banner -->
            {#if user?.validator?.matches_target}
              <div class="bg-green-50 border-2 border-green-400 rounded-lg p-4 mb-3">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <svg class="h-8 w-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3">
                    <h3 class="text-sm font-bold text-green-800">Your node is up to date!</h3>
                    <p class="text-xs text-green-700 mt-1">
                      Version {nodeVersion || 'not set'} meets or exceeds target {user.validator.target_version}
                    </p>
                  </div>
                </div>
              </div>
            {:else if daysSinceTarget() > 3}
              <div class="bg-red-50 border-2 border-red-400 rounded-lg p-4 mb-3">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <svg class="h-8 w-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3 flex-1">
                    <h3 class="text-sm font-bold text-red-800">Update overdue!</h3>
                    <p class="text-xs text-red-700 mt-1">
                      Update requested: {humanizeTimeSince(user.validator.target_created_at)}
                    </p>
                  </div>
                  <div class="relative group">
                    <a href="#/contribution-type/3" class="text-lg text-red-600 hover:text-red-700 hover:underline cursor-pointer">①*</a>
                    <div class="absolute right-0 top-6 px-2 py-1 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">
                      Node Upgrade
                    </div>
                  </div>
                </div>
              </div>
            {:else}
              <div class="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-4 mb-3">
                <div class="flex items-center">
                  <div class="flex-shrink-0">
                    <svg class="h-8 w-8 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3 flex-1">
                    <h3 class="text-sm font-bold text-yellow-800">Update needed</h3>
                    <p class="text-xs text-yellow-700 mt-1">
                      Update requested: {humanizeTimeSince(user.validator.target_created_at)}
                    </p>
                  </div>
                  <div class="relative group">
                    <a href="#/contribution-type/3" class="text-lg text-yellow-600 hover:text-yellow-700 hover:underline cursor-pointer">
                      {#if daysSinceTarget() === 0}④{:else if daysSinceTarget() === 1}③{:else if daysSinceTarget() === 2}②{:else}①{/if}*
                    </a>
                    <div class="absolute right-0 top-6 px-2 py-1 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">
                      Node Upgrade
                    </div>
                  </div>
                </div>
              </div>
            {/if}
            
            <div class="bg-blue-50 border border-blue-200 rounded-md p-3 mb-3">
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-sm font-medium text-blue-900">
                    Target Version: <span class="font-mono">{user.validator.target_version}</span>
                  </p>
                  <p class="text-xs text-blue-700 mt-1">
                    Set on {formatDate(user.validator.target_created_at)}
                  </p>
                </div>
              </div>
            </div>
          {/if}
          
          <input
            id="nodeVersion"
            type="text"
            bind:value={nodeVersion}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 0.3.9"
            disabled={isSaving}
          />
          <p class="mt-1 text-sm text-gray-500">
            Enter your current GenLayer node version (semantic versioning format)
          </p>
              </div>
            </div>
          {:else if userType === 'validator'}
            <div class="bg-sky-50/50 rounded-lg p-4 border-2 border-sky-200/50">
              <h3 class="text-md font-medium text-sky-600/70 mb-2 flex items-center">
                <Icon name="validator" size="sm" className="mr-2 text-sky-500/50" />
                Validator Profile
              </h3>
              <p class="text-sm text-sky-600/60">Not a validator yet. Run a node to activate this profile.</p>
            </div>
          {/if}
          
          <!-- Builder Profile -->
          {#if user.builder}
            <div class="bg-orange-50 rounded-lg p-4 border-2 border-orange-200">
              <h3 class="text-md font-medium text-orange-900 mb-3 flex items-center">
                <Icon name="builder" size="sm" className="mr-2 text-orange-600" />
                Builder Profile
              </h3>
              <div class="text-sm text-orange-800">
                <p>Total Points: <span class="font-bold text-orange-900">{user.builder.total_points || 0}</span></p>
                <p>Rank: <span class="font-bold text-orange-900">#{user.builder.rank || 'Unranked'}</span></p>
                <p class="text-xs text-orange-600 mt-2">Profile created: {formatDate(user.builder.created_at)}</p>
              </div>
            </div>
          {:else}
            <div class="bg-orange-50/50 rounded-lg p-4 border-2 border-orange-200/50">
              <h3 class="text-md font-medium text-orange-600/70 mb-2 flex items-center">
                <Icon name="builder" size="sm" className="mr-2 text-orange-500/50" />
                Builder Profile
              </h3>
              <p class="text-sm text-orange-600/60">Not a builder yet. Contribute to builder projects to activate this profile.</p>
            </div>
          {/if}
          
          <!-- Steward Profile -->
          {#if user.steward}
            <div class="bg-green-50 rounded-lg p-4 border-2 border-green-200">
              <h3 class="text-md font-medium text-green-900 mb-3 flex items-center">
                <span class="mr-2 text-lg">🌱</span>
                Steward Profile
              </h3>
              <div class="text-sm">
                <p class="text-green-700 font-medium">
                  Thanks for keeping things running smoothly around here 🛡️
                </p>
                <p class="text-gray-600 mt-2">
                  Your steward profile is active. You have access to review and manage community submissions.
                </p>
                <p class="text-xs text-green-600 mt-3">Profile created: {formatDate(user.steward.created_at)}</p>
              </div>
            </div>
          {:else}
            <div class="bg-green-50/50 rounded-lg p-4 border-2 border-green-200/50">
              <h3 class="text-md font-medium text-green-600/70 mb-2 flex items-center">
                <Icon name="steward" size="sm" className="mr-2 text-green-500/50" />
                Steward Profile
              </h3>
              <p class="text-sm text-green-600/60">Not a steward yet. Contribute to community initiatives to activate this profile.</p>
            </div>
          {/if}
        </div>
      </div>
      
      <div class="mt-6 flex gap-2">
        <button
          onclick={handleSave}
          disabled={isSaving || !hasChanges}
          class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </button>
        <button
          onclick={handleCancel}
          disabled={isSaving}
          class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
      </div>
    </div>
  {:else if !error}
    <div class="text-center py-8">
      <p class="text-gray-500">Loading profile...</p>
    </div>
  {/if}
</div>