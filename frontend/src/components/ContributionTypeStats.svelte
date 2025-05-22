<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { contributionsAPI } from '../lib/api';
  
  // State management
  let typeStats = $state([]);
  let loading = $state(true);
  let error = $state(null);
  
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
  {:else}
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Count
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Points Multiplier
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
          {#each typeStats as stats, i}
            <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="text-sm font-medium text-gray-900">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                      {stats.name}
                    </span>
                  </div>
                </div>
                {#if stats.description}
                  <div class="text-xs text-gray-500 mt-1">{stats.description}</div>
                {/if}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {stats.count}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {stats.current_multiplier}x
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {stats.participants_count}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {stats.count > 0 ? formatDate(stats.last_earned) : 'Never'}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>