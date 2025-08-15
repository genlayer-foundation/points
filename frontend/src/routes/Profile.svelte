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
        
        <div>
          <label for="nodeVersion" class="block text-sm font-medium text-gray-700 mb-1">
            Node Version
            {#if user?.validator?.target_version}
              <span class="text-xs text-gray-500 ml-2">(Target: {user.validator.target_version})</span>
            {/if}
          </label>
          <input
            id="nodeVersion"
            type="text"
            bind:value={nodeVersion}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 1.2.3"
            disabled={isSaving}
          />
          <p class="mt-1 text-sm text-gray-500">
            Your current GenLayer node version
            {#if user?.validator?.matches_target}
              <span class="text-green-600 font-medium ml-1">✓ Matches target</span>
            {/if}
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