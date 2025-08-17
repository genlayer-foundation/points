<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Pagination from './Pagination.svelte';
  import { contributionsAPI } from '../lib/api';
  
  const { 
    contributions = [], 
    loading: externalLoading = false, 
    error: externalError = null, 
    showUser = true, 
    userAddress = null,
    category = null,
    compact = false,
    limit: maxLimit = null
  } = $props();
  
  
  // Local state
  let page = $state(1);
  let limit = $state(maxLimit || (compact ? 5 : 10));
  let totalCount = $state(0);
  let localContributions = $state(contributions || []);
  let localLoading = $state(externalLoading);
  let localError = $state(externalError);
  
  // Process contributions - handle both grouped and ungrouped formats
  function processContributions(contribs) {
    if (!contribs || contribs.length === 0) return [];
    
    // Check if data is already grouped (from backend)
    if (contribs[0] && contribs[0].grouped_contributions) {
      // Data is already grouped, just format it for display
      return contribs.map(group => ({
        id: group.id,
        typeId: group.contribution_type.id,
        typeName: group.contribution_type_name || group.contribution_type.name,
        count: group.count || group.grouped_contributions.length,
        totalPoints: group.frozen_global_points,
        startDate: group.contribution_date,
        endDate: group.end_date || group.contribution_date,
        users: group.users || (group.user_details ? [group.user_details] : []),
        userDetails: group.user_details  // For single-user groups
      }));
    }
    
    // Data is not grouped (fallback for old API or when group_consecutive=false)
    // Group consecutive contributions of the same type
    const grouped = [];
    let currentGroup = null;
    
    for (const contrib of contribs) {
      const typeId = contrib.contribution_type?.id || contrib.contribution_type;
      const typeName = contrib.contribution_type_name || contrib.contribution_type?.name || 'Unknown Type';
      
      if (!currentGroup || currentGroup.typeId !== typeId) {
        // Start a new group
        currentGroup = {
          id: `group_${contrib.id}`,
          typeId,
          typeName,
          count: 1,
          totalPoints: contrib.frozen_global_points || 0,
          startDate: contrib.contribution_date,
          endDate: contrib.contribution_date,
          users: [],
          userDetails: contrib.user_details
        };
        
        if (contrib.user_details) {
          currentGroup.users = [{
            address: contrib.user_details.address,
            name: contrib.user_details.name
          }];
        }
        
        grouped.push(currentGroup);
      } else {
        // Add to existing group
        currentGroup.count++;
        currentGroup.totalPoints += (contrib.frozen_global_points || 0);
        currentGroup.endDate = contrib.contribution_date;
        
        // Add unique user
        if (contrib.user_details) {
          const userExists = currentGroup.users.some(u => 
            u.address === contrib.user_details.address
          );
          if (!userExists) {
            currentGroup.users.push({
              address: contrib.user_details.address,
              name: contrib.user_details.name
            });
          }
        }
      }
    }
    
    return grouped;
  }
  
  // Process contributions for display
  let processedContributions = $derived(processContributions(localContributions));
  
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
      
      // Add category filter if specified
      if (category) {
        params.category = category;
      }
      
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
      {#each processedContributions as group}
        <div class="{category === 'validator' ? 'bg-sky-50 border border-sky-200' : category === 'builder' ? 'bg-orange-50 border border-orange-200' : 'bg-white shadow'} rounded-lg p-4 hover:shadow-lg transition-shadow">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <div class="w-4 h-4 rounded-full {category === 'validator' ? 'bg-sky-500' : category === 'builder' ? 'bg-orange-500' : 'bg-green-500'} flex items-center justify-center flex-shrink-0">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 6v12m6-6H6"></path>
                  </svg>
                </div>
                <h3 class="text-base font-semibold text-gray-900 flex items-center gap-2">
                  <button
                    class="{category === 'validator' ? 'hover:text-sky-600' : category === 'builder' ? 'hover:text-orange-600' : 'hover:text-primary-600'} transition-colors"
                    onclick={() => push(`/contribution-type/${group.typeId}`)}
                  >
                    {group.typeName}
                  </button>
                  {#if group.count > 1}
                    <span class="text-sm font-normal text-gray-500">
                      × {group.count}
                    </span>
                  {/if}
                </h3>
              </div>
              
              <div class="flex items-center gap-3 text-xs">
                {#if showUser}
                  {#if group.users.length === 1}
                    <button 
                      class="{category === 'validator' ? 'text-sky-600 hover:text-sky-700' : category === 'builder' ? 'text-orange-600 hover:text-orange-700' : 'text-primary-600 hover:text-primary-700'} font-medium"
                      onclick={() => push(`/participant/${group.users[0].address || ''}`)}
                    >
                      {group.users[0].name || `${group.users[0].address?.slice(0, 6)}...${group.users[0].address?.slice(-4)}` || 'Anonymous'}
                    </button>
                  {:else if group.users.length > 1}
                    <span class="{category === 'validator' ? 'text-sky-600' : category === 'builder' ? 'text-orange-600' : 'text-primary-600'} font-medium">
                      {group.users.length} participants
                    </span>
                  {:else if group.userDetails}
                    <button 
                      class="{category === 'validator' ? 'text-sky-600 hover:text-sky-700' : category === 'builder' ? 'text-orange-600 hover:text-orange-700' : 'text-primary-600 hover:text-primary-700'} font-medium"
                      onclick={() => push(`/participant/${group.userDetails.address || ''}`)}
                    >
                      {group.userDetails.name || `${group.userDetails.address?.slice(0, 6)}...${group.userDetails.address?.slice(-4)}` || 'Anonymous'}
                    </button>
                  {/if}
                  <span class="text-gray-400">•</span>
                {/if}
                <span class="text-gray-500">
                  {#if group.count === 1}
                    {formatDate(group.startDate)}
                  {:else}
                    {formatDate(group.startDate)} - {formatDate(group.endDate)}
                  {/if}
                </span>
              </div>
            </div>
            
            <div class="ml-3 flex-shrink-0">
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {category === 'validator' ? 'bg-sky-100 text-sky-800' : category === 'builder' ? 'bg-orange-100 text-orange-800' : 'bg-purple-100 text-purple-800'}">
                {group.totalPoints} pts
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