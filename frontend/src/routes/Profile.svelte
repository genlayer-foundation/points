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
                {#if user?.validator?.matches_target}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    ✓ Up to date
                  </span>
                {:else}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    Update needed
                  </span>
                {/if}
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