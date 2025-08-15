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
    <div class="space-y-3 p-4">
      {#each localContributions as contribution, i}
        <div class="bg-white border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all duration-200">
          <!-- First Line: Main content with icon -->
          <div class="flex items-start justify-between mb-2">
            <div class="flex items-start gap-3">
              <!-- Contribution Type Icon/Badge -->
              <div class="flex-shrink-0 mt-0.5">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
                  <svg class="w-5 h-5 text-primary-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                  </svg>
                </div>
              </div>
              
              <div class="flex-1">
                <!-- Contribution Type Name -->
                <button
                  class="text-sm font-semibold text-gray-900 hover:text-primary-600 transition-colors"
                  onclick={() => push(`/contribution-type/${contribution.contribution_type?.id || contribution.contribution_type}`)}
                >
                  {contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type'}
                </button>
                
                <!-- Second Line: User and Date -->
                <div class="flex items-center gap-2 mt-1 text-xs text-gray-500">
                  {#if showUser}
                    <button
                      class="font-medium text-gray-600 hover:text-primary-600 transition-colors"
                      onclick={() => push(`/participant/${contribution.user_details?.address || ''}`)}
                    >
                      {contribution.user_details?.name || `${contribution.user_details?.address?.slice(0, 6)}...${contribution.user_details?.address?.slice(-4)}` || 'Anonymous'}
                    </button>
                    <span class="text-gray-400">•</span>
                  {/if}
                  <span class="text-gray-500">{formatDate(contribution.contribution_date)}</span>
                </div>
              </div>
            </div>
            
            <!-- Points Badge -->
            <div class="flex-shrink-0">
              <div class="inline-flex items-center px-3 py-1.5 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 text-white text-sm font-bold shadow-sm">
                {contribution.frozen_global_points != null ? contribution.frozen_global_points : 0}
                <span class="ml-1 text-xs font-normal opacity-90">pts</span>
              </div>
            </div>
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