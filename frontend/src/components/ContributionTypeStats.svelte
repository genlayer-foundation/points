<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { getPioneerContributionsColors } from '../lib/categoryColors.js';

  let typeStats = $state(/** @type {any[]} */ ([]));
  let loading = $state(true);
  let error = $state(/** @type {string | null} */ (null));

  // Derived state: include submittable types plus non-submittable types explicitly marked
  // to show in contributions (e.g. informational / mission-host types). Sort by points desc.
  let submittableTypes = $derived(
    typeStats
      .filter((stats) => stats.is_submittable || stats.show_in_contributions)
      .sort((a, b) => {
        const aMaxPoints = (a.max_points || 0) * (a.current_multiplier || 1);
        const bMaxPoints = (b.max_points || 0) * (b.current_multiplier || 1);
        return bMaxPoints - aMaxPoints;
      })
  );

  onMount(async () => {
    await fetchTypeStatistics();
  });

  $effect(() => {
    if ($currentCategory) {
      fetchTypeStatistics();
    }
  });

  async function fetchTypeStatistics() {
    try {
      loading = true;
      error = null;

      /** @type {Record<string, string>} */
      const params = {};
      if ($currentCategory !== 'global') {
        params.category = $currentCategory;
      }

      const res = await contributionsAPI.getContributionTypeStatistics(params);
      typeStats = res.data || [];
      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load contribution type statistics';
      loading = false;
    }
  }
</script>

<div class="space-y-6">
  {#if submittableTypes.length > 0}
    {@const colors = getPioneerContributionsColors($currentCategory)}

    <!-- Card container with dividers -->
    <div class="bg-white border border-gray-200 border-l-4 {colors.containerBorderLeft} shadow-sm overflow-hidden rounded-lg mb-6">
      <!-- Header -->
      <div class="px-4 py-5 sm:px-6 bg-white border-b border-gray-200">
        <div class="flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 {colors.headerIcon} mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h2 class="text-xl font-bold text-gray-900">Contributions (open call)</h2>
        </div>
        <p class="mt-1 text-sm text-gray-600 leading-snug">
          Contribute to the GenLayer Ecosystem in multiple ways and be rewarded. <br>
          These are open-ended contributions, both small and large, from indie developers and startups alike, allowing you to choose your own path.
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
            <div class="mb-2 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div class="flex min-w-0 flex-wrap items-center gap-2 sm:flex-1">
                <button
                  onclick={() => push(`/contribution-type/${stats.id}`)}
                  class="min-w-0 max-w-full truncate text-left text-base font-bold font-heading {colors.titleText} {colors.titleTextHover} transition-colors"
                >
                  {stats.name}
                </button>

                <!-- Points available as badge -->
                <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-normal {colors.badgeBg} {colors.badgeText}">
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
                  <span class="hidden text-xs text-gray-600 sm:inline">
                    {stats.total_points_given.toLocaleString()} pts earned • {stats.count} {stats.count === 1 ? 'contribution' : 'contributions'} • {stats.participants_count} {stats.participants_count === 1 ? 'builder' : 'builders'}
                  </span>
                  <span class="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 sm:hidden">
                    {stats.count} accepted
                  </span>
                {/if}
              </div>

              <!-- Submit button (hidden for non-submittable types; those are accessed via their missions) -->
              {#if stats.is_submittable}
                <button
                  onclick={() => push(`/submit-contribution?type=${stats.id}`)}
                  class="inline-flex min-h-11 w-full flex-shrink-0 items-center justify-center rounded-[8px] border border-gray-200 px-3 text-sm font-normal {colors.titleText} {colors.titleTextHover} transition-colors sm:min-h-0 sm:w-auto sm:border-0 sm:p-0"
                >
                  Submit →
                </button>
              {/if}
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
