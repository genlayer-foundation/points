<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import Badge from './Badge.svelte';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { getPioneerContributionsColors } from '../lib/categoryColors.js';

  // State management
  let typeStats = $state([]);
  let loading = $state(true);
  let error = $state(null);

  // Derived state to filter only submittable types and sort by points (highest first)
  let submittableTypes = $derived(
    typeStats
      .filter(stats => stats.is_submittable)
      .sort((a, b) => {
        // Sort by max_points descending
        const aMaxPoints = (a.max_points || 0) * (a.current_multiplier || 1);
        const bMaxPoints = (b.max_points || 0) * (b.current_multiplier || 1);
        return bMaxPoints - aMaxPoints;
      })
  );

  // Get colors based on current category
  let pioneerColors = $derived(getPioneerContributionsColors($currentCategory));

  onMount(async () => {
    await fetchTypeStatistics();
  });
  
  // Re-fetch when category changes
  $effect(() => {
    if ($currentCategory) {
      fetchTypeStatistics();
    }
  });
  
  async function fetchTypeStatistics() {
    try {
      loading = true;
      error = null;
      
      // Pass category parameter if not global
      const params = {};
      if ($currentCategory !== 'global') {
        params.category = $currentCategory;
      }
      
      const res = await contributionsAPI.getContributionTypeStatistics(params);
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
  {#if submittableTypes.length > 0}
    <div class="bg-white border border-gray-200 border-l-4 border-l-orange-500 shadow overflow-hidden rounded-lg mb-6">
      <div class="px-4 py-5 sm:px-6 bg-white border-b border-gray-200">
        <div class="flex items-center flex-wrap gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 sm:h-6 sm:w-6 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h3 class="text-base sm:text-lg leading-6 font-medium text-orange-900">
            Contribution Opportunities
          </h3>
        </div>
        <p class="mt-1 max-w-2xl text-xs sm:text-sm text-gray-600">
          Earn points by making these contributions to the GenLayer ecosystem
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
                  Points
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Points Earned
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Earned
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each submittableTypes as stats, i}
                <tr class="hover:bg-orange-50 transition-colors duration-150">
                  <td class="px-6 py-4">
                    <div class="flex items-center">
                      <div class="text-sm font-medium">
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
                          color="orange"
                          clickable={true}
                        />
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <div class="text-sm text-gray-600">
                      {stats.description || 'No description available'}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-bold text-gray-900">
                      {#if stats.min_points != null && stats.max_points != null && stats.current_multiplier != null}
                        {#if stats.min_points === stats.max_points}
                          {Math.round(stats.min_points * stats.current_multiplier)}
                        {:else}
                          {Math.round(stats.min_points * stats.current_multiplier)} - {Math.round(stats.max_points * stats.current_multiplier)}
                        {/if}
                      {:else}
                        0
                      {/if}
                    </div>
                  </td>
                  {#if stats.count === 0}
                    <td class="px-6 py-4" colspan="2">
                      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Pioneer Opportunity
                      </span>
                    </td>
                  {:else}
                    <td class="px-6 py-4">
                      <div class="text-lg font-bold text-gray-900">{stats.total_points_given.toLocaleString()}</div>
                      <div class="text-xs text-gray-500 mt-1">{stats.count} {stats.count === 1 ? 'contribution' : 'contributions'}</div>
                      <div class="text-xs text-gray-500">{stats.participants_count} {stats.participants_count === 1 ? 'builder' : 'builders'}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {formatDate(stats.last_earned)}
                    </td>
                  {/if}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {:else if loading}
    <!-- Loading state -->
    <div class="bg-white border border-gray-200 border-l-4 border-l-orange-500 shadow overflow-hidden rounded-lg mb-6">
      <div class="px-4 py-5 sm:px-6 bg-white border-b border-gray-200">
        <div class="flex items-center">
          <div class="h-6 w-6 bg-gray-300 rounded animate-pulse mr-2"></div>
          <div class="h-6 w-48 bg-gray-300 rounded animate-pulse"></div>
        </div>
        <div class="mt-2 h-4 w-64 bg-gray-200 rounded animate-pulse"></div>
      </div>
      <div class="bg-white p-6">
        <div class="space-y-3">
          <div class="h-4 bg-gray-200 rounded animate-pulse"></div>
          <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
        </div>
      </div>
    </div>
  {/if}
</div>