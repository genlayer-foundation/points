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
    <!-- Card container with dividers -->
    <div class="bg-white border border-gray-200 border-l-4 border-l-orange-500 shadow-sm overflow-hidden rounded-lg mb-6">
      <!-- Header -->
      <div class="px-4 py-5 sm:px-6 bg-white border-b border-gray-200">
        <div class="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-orange-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h2 class="text-xl font-bold text-gray-900">Contribution Opportunities</h2>
        </div>
        <p class="mt-1 text-sm text-gray-600 leading-snug">
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
        <!-- Contribution types with dividers -->
        {#each submittableTypes as stats}
          <div class="px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 transition-colors">
            <!-- Title row with badges and stats -->
            <div class="flex items-center gap-3 mb-2 flex-wrap">
              <button
                onclick={() => push(`/contribution-type/${stats.id}`)}
                class="text-base font-bold font-heading text-gray-900 hover:text-orange-600 transition-colors"
              >
                {stats.name}
              </button>

              <!-- Points available as badge -->
              <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-normal bg-orange-100 text-orange-800">
                {#if stats.min_points != null && stats.max_points != null && stats.current_multiplier != null}
                  {#if stats.min_points === stats.max_points}
                    {Math.round(stats.min_points * stats.current_multiplier)} pts
                  {:else}
                    {Math.round(stats.min_points * stats.current_multiplier)}-{Math.round(stats.max_points * stats.current_multiplier)} pts
                  {/if}
                {:else}
                  0 pts
                {/if}
              </span>

              <!-- Pioneer or Stats -->
              {#if stats.count === 0}
                <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Pioneer Opportunity
                </span>
              {:else}
                <span class="text-xs text-gray-600">
                  {stats.total_points_given.toLocaleString()} pts earned • {stats.count} {stats.count === 1 ? 'contribution' : 'contributions'} • {stats.participants_count} {stats.participants_count === 1 ? 'builder' : 'builders'}
                </span>
              {/if}

              <!-- Submit button -->
              <button
                onclick={() => push(`/submit-contribution?type=${stats.id}`)}
                class="ml-auto flex-shrink-0 text-sm font-medium text-orange-600 hover:text-orange-700 transition-colors"
              >
                Submit →
              </button>
            </div>

            <!-- Description -->
            {#if stats.description}
              <div class="text-sm text-gray-600 max-w-3xl">
                {stats.description}
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  {:else if loading}
    <!-- Loading state -->
    <div class="mb-4">
      <div class="flex items-center">
        <div class="h-6 w-6 bg-gray-300 rounded animate-pulse mr-2"></div>
        <div class="h-6 w-48 bg-gray-300 rounded animate-pulse"></div>
      </div>
      <div class="mt-2 h-4 w-64 bg-gray-200 rounded animate-pulse"></div>
    </div>
    <div class="space-y-3">
      <div class="bg-white border border-gray-200 rounded-lg p-4">
        <div class="h-4 bg-gray-200 rounded animate-pulse mb-2"></div>
        <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
      </div>
    </div>
  {/if}
</div>