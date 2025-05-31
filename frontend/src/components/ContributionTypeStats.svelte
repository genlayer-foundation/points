<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import Badge from './Badge.svelte';
  import { contributionsAPI } from '../lib/api';
  
  // State management
  let typeStats = $state([]);
  let loading = $state(true);
  let error = $state(null);
  
  // Derived state to separate opportunities (zero contributions) from active types
  let opportunityTypes = $derived(typeStats.filter(stats => stats.count === 0));
  let activeTypes = $derived(typeStats.filter(stats => stats.count > 0));
  
  onMount(async () => {
    await fetchTypeStatistics();
  });
  
  async function fetchTypeStatistics() {
    try {
      loading = true;
      error = null;
      
      const res = await contributionsAPI.getContributionTypeStatistics();
      typeStats = res.data || [];
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load contribution type statistics';
      loading = false;
      console.error('Failed to load contribution type statistics:', err);
    }
  }
  
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
</script>

<div class="space-y-6">
  {#if opportunityTypes.length > 0}
    <div class="bg-blue-50 border border-blue-200 shadow overflow-hidden rounded-lg mb-6">
      <div class="px-4 py-5 sm:px-6 bg-blue-100 border-b border-blue-200">
        <div class="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h3 class="text-lg leading-6 font-medium text-blue-900">
            Pioneer Opportunities
          </h3>
        </div>
        <p class="mt-1 max-w-2xl text-sm text-blue-700">
          Be the first to make these contributions and earn extra points!
        </p>
      </div>
      
      {#if loading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if error}
        <div class="p-6 text-center text-red-500">
          Failed to load contribution type statistics: {error}
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-blue-200">
            <thead class="bg-blue-50">
              <tr>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-blue-700 uppercase tracking-wider">
                  Type
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-blue-700 uppercase tracking-wider">
                  Description
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-blue-700 uppercase tracking-wider">
                  Points Available
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-blue-100">
              {#each opportunityTypes as stats, i}
                <tr class="bg-blue-50 hover:bg-blue-100 transition-colors duration-150">
                  <td class="px-6 py-4">
                    <div class="flex items-center">
                      <div class="text-sm font-medium text-blue-900">
                        <Badge
                          badge={{
                            id: stats.id,
                            name: stats.name,
                            description: stats.description || '',
                            points: 0,
                            actionId: stats.id,
                            actionName: stats.name,
                            evidenceUrl: ''
                          }}
                          color="blue"
                          clickable={true}
                        />
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <div class="text-sm text-blue-800">
                      {stats.description || 'No description available'}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-bold text-blue-900">
                      {#if stats.min_points != null && stats.max_points != null && stats.current_multiplier != null}
                        {#if stats.min_points === stats.max_points}
                          {Math.round(stats.min_points * stats.current_multiplier)}
                        {:else}
                          {Math.round(stats.min_points * stats.current_multiplier)} - {Math.round(stats.max_points * stats.current_multiplier)}
                        {/if}
                      {:else}
                        0
                      {/if}
                      <span class="text-xs font-normal ml-1">global points</span>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}

  <div class="bg-white shadow overflow-hidden rounded-lg mb-6">
    <div class="px-4 py-5 sm:px-6">
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        Contribution Types Overview
      </h3>
      <p class="mt-1 max-w-2xl text-sm text-gray-500">
        Summary of contribution types, counts, and statistics
      </p>
    </div>
    
    {#if loading}
      <div class="flex justify-center items-center p-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    {:else if error}
      <div class="p-6 text-center text-red-500">
        Failed to load contribution type statistics: {error}
      </div>
    {:else if typeStats.length === 0}
      <div class="p-6 text-center text-gray-500">
        No contribution types found.
      </div>
    {:else if activeTypes.length === 0}
      <div class="p-6 text-center text-gray-500">
        No contributions have been made yet. Be the first to contribute!
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Count
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Points
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Participants
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Earned
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each activeTypes as stats, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-900">
                      <Badge
                        badge={{
                          id: stats.id,
                          name: stats.name,
                          description: stats.description || '',
                          points: 0,
                          actionId: stats.id,
                          actionName: stats.name,
                          evidenceUrl: ''
                        }}
                        color="green"
                        clickable={true}
                      />
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="text-sm text-gray-600">
                    {stats.description || ''}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {stats.count}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {#if stats.min_points != null && stats.max_points != null && stats.current_multiplier != null}
                    {#if stats.min_points === stats.max_points}
                      {Math.round(stats.min_points * stats.current_multiplier)}
                    {:else}
                      {Math.round(stats.min_points * stats.current_multiplier)} - {Math.round(stats.max_points * stats.current_multiplier)}
                    {/if}
                  {:else}
                    0
                  {/if}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {stats.participants_count}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(stats.last_earned)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>