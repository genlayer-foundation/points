<script>
  import { onMount } from 'svelte';
  import api from '../lib/api';
  
  // Props using Svelte 5 runes
  const { address = '' } = $props();
  
  // State variables
  let isActive = $state(false);
  let isBanned = $state(false);
  let loading = $state(true);
  let error = $state(null);
  
  onMount(async () => {
    await checkValidatorStatus();
  });
  
  async function checkValidatorStatus() {
    if (!address) {
      loading = false;
      return;
    }
    
    try {
      loading = true;
      error = null;
      
      // Normalize the address
      const normalizedAddress = address.toLowerCase();
      
      // Fetch all active validators
      const activeRes = await api.get('/users/validators/');
      const activeValidators = activeRes.data;
      
      // Fetch all banned validators
      const bannedRes = await api.get('/users/banned-validators/');
      const bannedValidators = bannedRes.data;
      
      // Check if this address is in either list
      isActive = activeValidators.includes(normalizedAddress);
      isBanned = bannedValidators.includes(normalizedAddress);
      
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to check validator status';
      loading = false;
    }
  }
</script>

{#if loading}
  <div class="inline-flex items-center">
    <div class="animate-spin h-4 w-4 border-b-2 border-gray-500 rounded-full mr-2"></div>
    <span class="text-sm text-gray-500">Checking validator status...</span>
  </div>
{:else if error}
  <span class="text-sm text-red-500">Error: {error}</span>
{:else if isActive || isBanned}
  <div class="flex space-x-2">
    {#if isActive}
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        <svg class="mr-1 h-3 w-3 text-green-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
        </svg>
        Active Validator
      </span>
    {/if}
    
    {#if isBanned}
      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        <svg class="mr-1 h-3 w-3 text-red-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
        </svg>
        Banned Validator
      </span>
    {/if}
  </div>
{/if}