<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Badge from './Badge.svelte';
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

<div class="bg-white shadow overflow-hidden rounded-lg">
  <div class="px-4 py-5 sm:px-6">
    <h3 class="text-lg leading-6 font-medium text-gray-900">
      Contributions
    </h3>
  </div>
  
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
    <div class="divide-y divide-gray-200">
      {#each localContributions as contribution, i}
        <div class={`px-6 py-4 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-50 transition-colors`}>
          <!-- First Line: User (if shown), Type, Points -->
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-4">
              {#if showUser}
                <button
                  class="text-sm font-medium text-primary-600 hover:text-primary-700"
                  onclick={() => push(`/participant/${contribution.user_details?.address || ''}`)}
                >
                  {contribution.user_details?.name || `${contribution.user_details?.address?.slice(0, 6)}...${contribution.user_details?.address?.slice(-4)}` || 'N/A'}
                </button>
                <span class="text-gray-400">•</span>
              {/if}
              <Badge
                badge={{
                  id: contribution.contribution_type?.id || contribution.contribution_type,
                  name: contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type',
                  description: contribution.contribution_type_description || contribution.contribution_type?.description || '',
                  points: 0,
                  actionId: contribution.contribution_type?.id || contribution.contribution_type,
                  actionName: contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type',
                  evidenceUrl: ''
                }}
                color="green"
                clickable={true}
              />
            </div>
            <div class="flex items-center gap-3">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                {contribution.frozen_global_points != null ? contribution.frozen_global_points : 0} pts
              </span>
            </div>
          </div>
          
          <!-- Second Line: Date only -->
          <div class="text-xs text-gray-500">
            <span>{formatDate(contribution.contribution_date)}</span>
          </div>
        </div>
      {/each}
    </div>
    
    <!-- Pagination -->
    <Pagination 
      page={page} 
      limit={limit} 
      totalCount={totalCount} 
      on:pageChange={handlePageChange} 
    />
  {/if}
</div>