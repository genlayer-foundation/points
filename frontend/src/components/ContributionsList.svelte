<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Pagination from './Pagination.svelte';
  import ContributionCard from './ContributionCard.svelte';
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
      // Data is already grouped, but we need to handle highlights properly
      const result = [];
      
      for (const group of contribs) {
        // Process each group - split at highlights but keep non-highlighted consecutive items grouped
        let currentSubgroup = null;
        
        for (const contrib of group.grouped_contributions) {
          if (contrib.highlight) {
            // If we have a current subgroup, push it before the highlight
            if (currentSubgroup) {
              result.push(currentSubgroup);
              currentSubgroup = null;
            }
            
            // Push the highlighted contribution separately
            result.push({
              id: contrib.id,
              contribution_type: contrib.contribution_type,
              contribution_type_name: contrib.contribution_type_name,
              contribution_type_details: contrib.contribution_type_details,
              contribution_date: contrib.contribution_date,
              frozen_global_points: contrib.frozen_global_points,
              points: contrib.frozen_global_points || contrib.points,
              user_details: contrib.user_details,
              category: category || contrib.contribution_type_details?.category,
              highlight: contrib.highlight,
              typeId: contrib.contribution_type_details?.id || contrib.contribution_type,
              count: 1,
              end_date: contrib.contribution_date,
              users: contrib.user_details ? [contrib.user_details] : []
            });
          } else {
            // Non-highlighted contribution - add to current subgroup
            if (!currentSubgroup) {
              // Start a new subgroup
              currentSubgroup = {
                id: contrib.id,
                contribution_type: contrib.contribution_type,
                contribution_type_name: contrib.contribution_type_name,
                contribution_type_details: contrib.contribution_type_details,
                contribution_date: contrib.contribution_date,
                frozen_global_points: contrib.frozen_global_points || contrib.points,
                points: contrib.frozen_global_points || contrib.points,
                user_details: contrib.user_details,
                category: category || contrib.contribution_type_details?.category,
                highlight: null,
                typeId: contrib.contribution_type_details?.id || contrib.contribution_type,
                count: 1,
                end_date: contrib.contribution_date,
                users: contrib.user_details ? [contrib.user_details] : []
              };
            } else {
              // Add to existing subgroup
              currentSubgroup.count++;
              currentSubgroup.frozen_global_points += (contrib.frozen_global_points || contrib.points || 0);
              currentSubgroup.points = currentSubgroup.frozen_global_points;
              currentSubgroup.end_date = contrib.contribution_date;
              
              // Add unique user if different
              if (contrib.user_details) {
                const userExists = currentSubgroup.users.some(u => 
                  u.address === contrib.user_details.address
                );
                if (!userExists) {
                  currentSubgroup.users.push(contrib.user_details);
                }
              }
            }
          }
        }
        
        // Push any remaining subgroup
        if (currentSubgroup) {
          result.push(currentSubgroup);
        }
      }
      
      return result;
    }
    
    // Data is not grouped - group consecutive contributions of the same type
    // but don't group if there's a featured/highlighted contribution
    const grouped = [];
    let currentGroup = null;
    
    for (const contrib of contribs) {
      const typeId = contrib.contribution_type?.id || contrib.contribution_type;
      const typeName = contrib.contribution_type_name || contrib.contribution_type?.name || 'Unknown Type';
      const hasHighlight = contrib.highlight ? true : false;
      
      // Start a new group if: different type, has highlight, or current group has highlight
      if (!currentGroup || currentGroup.typeId !== typeId || hasHighlight || currentGroup.highlight) {
        // Start a new group
        currentGroup = {
          id: contrib.id,
          contribution_type: typeId,
          contribution_type_name: typeName,
          contribution_type_details: contrib.contribution_type,
          contribution_date: contrib.contribution_date,
          frozen_global_points: contrib.frozen_global_points || 0,
          points: contrib.frozen_global_points || 0,
          user_details: contrib.user_details,
          category: category || contrib.contribution_type?.category || contrib.category,
          highlight: contrib.highlight,
          // Grouping info
          typeId: typeId,
          count: 1,
          end_date: contrib.contribution_date,
          users: []
        };
        
        if (contrib.user_details) {
          currentGroup.users = [{
            address: contrib.user_details.address,
            name: contrib.user_details.name,
            profile_image_url: contrib.user_details.profile_image_url
          }];
        }
        
        grouped.push(currentGroup);
      } else {
        // Add to existing group
        currentGroup.count++;
        currentGroup.frozen_global_points += (contrib.frozen_global_points || 0);
        currentGroup.points = currentGroup.frozen_global_points;
        currentGroup.end_date = contrib.contribution_date;
        
        // Add unique user
        if (contrib.user_details) {
          const userExists = currentGroup.users.some(u => 
            u.address === contrib.user_details.address
          );
          if (!userExists) {
            currentGroup.users.push({
              address: contrib.user_details.address,
              name: contrib.user_details.name,
              profile_image_url: contrib.user_details.profile_image_url
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
      // Take just the date part (YYYY-MM-DD) and ignore time/timezone
      const datePart = dateString.split('T')[0];
      const [year, month, day] = datePart.split('-');
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return `${months[parseInt(month) - 1]} ${parseInt(day)}, ${year}`;
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
      {#each processedContributions as contribution}
        <ContributionCard {contribution} {showUser} />
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