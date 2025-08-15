<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getCurrentUser, updateUserProfile } from '../lib/api';
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  
  let user = $state(null);
  let name = $state('');
  let nodeVersion = $state('');
  let isSaving = $state(false);
  let error = $state('');
  
  // Track if any field has changed
  let hasChanges = $derived(user && (
    name !== (user.name || '') || 
    nodeVersion !== (user.validator?.node_version || '')
  ));
  
  // Calculate days since target was set
  let daysSinceTarget = $derived(() => {
    if (!user?.validator?.target_created_at) return null;
    const created = new Date(user.validator.target_created_at);
    const now = new Date();
    const diff = now - created;
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  });
  
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
  
  onMount(async () => {
    try {
      const userData = await getCurrentUser();
      user = userData;
      name = userData.name || '';
      nodeVersion = userData.validator?.node_version || '';
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
        
        <div class="border-t pt-4">
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
                  <div class="ml-3">
                    <h3 class="text-sm font-bold text-red-800">Update overdue!</h3>
                    <p class="text-xs text-red-700 mt-1">
                      You're {daysSinceTarget()} days late. Update now to get 1 point.
                    </p>
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
                  <div class="ml-3">
                    <h3 class="text-sm font-bold text-yellow-800">Update needed</h3>
                    <p class="text-xs text-yellow-700 mt-1">
                      Target version {user.validator.target_version} is available - Day {daysSinceTarget() + 1}
                    </p>
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
                    {#if user.validator.target_date}
                      • Due by {formatDate(user.validator.target_date)}
                    {/if}
                  </p>
                </div>
              </div>
              
              <div class="mt-3 pt-3 border-t border-blue-200">
                <p class="text-xs font-medium text-blue-900 mb-1">Points for upgrading:</p>
                <div class="grid grid-cols-4 gap-2 text-xs">
                  <div class="text-center">
                    <div class="font-medium text-blue-900">Day 1</div>
                    <div class="text-blue-700">4 points</div>
                  </div>
                  <div class="text-center">
                    <div class="font-medium text-blue-900">Day 2</div>
                    <div class="text-blue-700">3 points</div>
                  </div>
                  <div class="text-center">
                    <div class="font-medium text-blue-900">Day 3</div>
                    <div class="text-blue-700">2 points</div>
                  </div>
                  <div class="text-center">
                    <div class="font-medium text-blue-900">Day 4+</div>
                    <div class="text-blue-700">1 point</div>
                  </div>
                </div>
                {#if daysSinceTarget() !== null}
                  <p class="text-xs text-blue-600 mt-2 text-center">
                    {#if daysSinceTarget() === 0}
                      <strong>Today is day 1 - Upgrade now for maximum points!</strong>
                    {:else if daysSinceTarget() === 1}
                      Day {daysSinceTarget() + 1} - You'll get 3 points
                    {:else if daysSinceTarget() === 2}
                      Day {daysSinceTarget() + 1} - You'll get 2 points
                    {:else}
                      Day {daysSinceTarget() + 1} - You'll get 1 point
                    {/if}
                  </p>
                {/if}
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