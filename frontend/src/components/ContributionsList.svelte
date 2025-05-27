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
    <p class="mt-1 max-w-2xl text-sm text-gray-500">
      Recent contributions with points and multipliers
    </p>
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
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            {#if showUser}
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contributor
              </th>
            {/if}
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Points
            </th>
            <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Evidence
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#each localContributions as contribution, i}
            <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              {#if showUser}
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-900">
                      <a href={`/participant/${contribution.user_details?.address || contribution.user?.address || contribution.address || ''}`} onclick={(e) => { e.preventDefault(); push(`/participant/${contribution.user_details?.address || contribution.user?.address || contribution.address || ''}`); }}>
                        {contribution.user_details?.name || contribution.user.name || contribution.user_details?.email || contribution.user.email}
                      </a>
                    </div>
                  </div>
                </td>
              {/if}
              <td class="px-6 py-4 whitespace-nowrap">
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
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(contribution.contribution_date)}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">
                  {contribution.frozen_global_points != null ? contribution.frozen_global_points : 0}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                {#if contribution.evidence_items && contribution.evidence_items.length > 0}
                  <div class="flex flex-col items-end gap-1">
                    {#each contribution.evidence_items as evidence}
                      <div class="flex items-center gap-2">
                        {#if evidence.description}
                          <span class="text-xs text-gray-500 max-w-xs truncate text-right" title={evidence.description}>
                            {evidence.description}
                          </span>
                        {/if}
                        
                        {#if evidence.url}
                          <a href={evidence.url} target="_blank" rel="noopener noreferrer" 
                             class="inline-flex items-center text-primary-600 hover:text-primary-900">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        {/if}
                        
                        {#if evidence.file_url}
                          <a href={evidence.file_url} target="_blank" rel="noopener noreferrer" 
                             class="inline-flex items-center text-primary-600 hover:text-primary-900">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                          </a>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {:else}
                  <span class="text-gray-400">None</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
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