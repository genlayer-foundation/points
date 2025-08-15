<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Pagination from './Pagination.svelte';
  import { contributionsAPI } from '../lib/api';
  
  const { contributions = [], loading: externalLoading = false, error: externalError = null, showUser = true, userAddress = null } = $props();
  
  
  // Local state
  let page = $state(1);
  let limit = $state(10);
  let totalCount = $state(0);
  let localContributions = $state(contributions || []);
  let localLoading = $state(externalLoading);
  let localError = $state(externalError);
  
  // Watch for external prop changes
  $effect(() => {
    localContributions = contributions || [];
  });
  
  $effect(() => {
    localLoading = externalLoading;
  });
  
  $effect(() => {
    localError = externalError;
  });
  
  // Fetch data when userAddress is provided
  $effect(() => {
    if (userAddress) {
      fetchContributions();
    }
  });
  
  async function fetchContributions() {
    if (!userAddress) return;
    
    try {
      localLoading = true;
      localError = null;
      
      const params = {
        page,
        limit,
        user_address: userAddress
      };
      
      const res = await contributionsAPI.getContributions(params);
      totalCount = res.data.count || 0;
      localContributions = res.data.results || [];
      localLoading = false;
    } catch (err) {
      localError = err.message || 'Failed to load contributions';
      localLoading = false;
    }
  }
  
  function handlePageChange(event) {
    page = event.detail;
  }
  
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
</script>

<div>
  {#if localLoading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if localError}
    <div class="p-6 text-center text-red-500">
      Failed to load contributions: {localError}
    </div>
  {:else if localContributions.length === 0}
    <div class="p-6 text-center text-gray-500">
      No contributions found.
    </div>
  {:else}
    <div class="space-y-3">
      {#each localContributions as contribution}
        <div class="bg-white shadow rounded-lg p-4 hover:shadow-lg transition-shadow">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 6v12m6-6H6"></path>
                  </svg>
                </div>
                <h3 class="text-base font-semibold text-gray-900">
                  <button
                    class="hover:text-primary-600 transition-colors"
                    onclick={() => push(`/contribution-type/${contribution.contribution_type?.id || contribution.contribution_type}`)}
                  >
                    {contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type'}
                  </button>
                </h3>
              </div>
              
              <div class="flex items-center gap-3 text-xs">
                {#if showUser}
                  <button 
                    class="text-primary-600 hover:text-primary-700 font-medium"
                    onclick={() => push(`/participant/${contribution.user_details?.address || ''}`)}
                  >
                    {contribution.user_details?.name || `${contribution.user_details?.address?.slice(0, 6)}...${contribution.user_details?.address?.slice(-4)}` || 'Anonymous'}
                  </button>
                  <span class="text-gray-400">•</span>
                {/if}
                <span class="text-gray-500">{formatDate(contribution.contribution_date)}</span>
              </div>
            </div>
            
            <div class="ml-3 flex-shrink-0">
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                {contribution.frozen_global_points != null ? contribution.frozen_global_points : 0} pts
              </span>
            </div>
          </div>
        </div>
      {/each}
    </div>
    
    {#if userAddress}
      <!-- Pagination -->
      <div class="mt-4">
        <Pagination 
          page={page} 
          limit={limit} 
          totalCount={totalCount} 
          on:pageChange={handlePageChange} 
        />
      </div>
    {/if}
  {/if}
</div>