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
  
  // Derived state to separate opportunities (zero contributions) from active types
  let opportunityTypes = $derived(
    typeStats
      .filter(stats => stats.count === 0)
      .sort((a, b) => {
        // Sort by max_points descending
        const aMaxPoints = (a.max_points || 0) * (a.current_multiplier || 1);
        const bMaxPoints = (b.max_points || 0) * (b.current_multiplier || 1);
        return bMaxPoints - aMaxPoints;
      })
  );
  let activeTypes = $derived(typeStats.filter(stats => stats.count > 0));

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
  {#if opportunityTypes.length > 0}
    <div class="{pioneerColors.containerBg} border {pioneerColors.containerBorder} shadow overflow-hidden rounded-lg mb-6">
      <div class="px-4 py-5 sm:px-6 {pioneerColors.headerBg} border-b {pioneerColors.headerBorder}">
        <div class="flex items-center flex-wrap gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 sm:h-6 sm:w-6 {pioneerColors.headerIcon}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h3 class="text-base sm:text-lg leading-6 font-medium {pioneerColors.headerText}">
            Pioneer Opportunities
          </h3>
        </div>
        <p class="mt-1 max-w-2xl text-xs sm:text-sm {pioneerColors.descriptionText}">
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
          <table class="min-w-full divide-y {pioneerColors.containerBorder}">
            <thead class="{pioneerColors.tableHeaderBg}">
              <tr>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium {pioneerColors.tableHeaderText} uppercase tracking-wider">
                  Type
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium {pioneerColors.tableHeaderText} uppercase tracking-wider">
                  Description
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium {pioneerColors.tableHeaderText} uppercase tracking-wider">
                  Points
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y {pioneerColors.tableBorder}">
              {#each opportunityTypes as stats, i}
                <tr class="{pioneerColors.tableRowBg} {pioneerColors.tableRowHover} transition-colors duration-150">
                  <td class="px-6 py-4">
                    <div class="flex items-center">
                      <div class="text-sm font-medium {pioneerColors.titleText}">
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
                          color={pioneerColors.badgeColor}
                          clickable={true}
                        />
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <div class="text-sm {pioneerColors.contentText}">
                      {stats.description || 'No description available'}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-bold {pioneerColors.pointsText}">
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