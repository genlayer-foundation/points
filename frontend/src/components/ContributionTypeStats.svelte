<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import Icons from './Icons.svelte';
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
    <div class="{pioneerColors.containerBg} border {pioneerColors.containerBorder} shadow-sm rounded-xl p-6">
      <div class="flex items-center gap-3 mb-4">
        <div class="w-10 h-10 {pioneerColors.headerBg} rounded-lg flex items-center justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 {pioneerColors.headerIcon}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <h3 class="text-lg font-semibold {pioneerColors.headerText}">Pioneer Opportunities</h3>
          <p class="text-sm {pioneerColors.descriptionText}">Be the first to make these contributions and earn extra points!</p>
        </div>
      </div>

      {#if loading}
        <div class="flex justify-center items-center py-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if error}
        <div class="p-4 text-center text-red-600 bg-red-50 rounded-lg">
          Failed to load opportunities: {error}
        </div>
      {:else}
        <div class="space-y-3">
          {#each opportunityTypes as stats}
            <button
              onclick={() => push(`/contribution-type/${stats.id}`)}
              class="w-full bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200 hover:border-gray-300 text-left group"
            >
              <div class="flex items-start gap-4">
                {#if stats.icon}
                  <div class="flex-shrink-0 w-8 h-8 {pioneerColors.headerBg} rounded-lg flex items-center justify-center text-base">
                    {stats.icon}
                  </div>
                {/if}
                <div class="flex-1">
                  <h4 class="font-medium {pioneerColors.titleText} group-hover:{pioneerColors.headerText} transition-colors">{stats.name}</h4>
                  {#if stats.description}
                    <p class="text-sm {pioneerColors.contentText} mt-1 line-clamp-2">{stats.description}</p>
                  {/if}
                </div>
                <div class="flex items-center gap-1 px-3 py-1 {pioneerColors.headerBg} {pioneerColors.headerText} rounded-lg font-semibold text-sm whitespace-nowrap">
                  <Icons name="lightning" size="xs" className="{pioneerColors.headerIcon}" />
                  {#if stats.min_points != null && stats.max_points != null && stats.current_multiplier != null}
                    {#if stats.min_points === stats.max_points}
                      {Math.round(stats.min_points * stats.current_multiplier)}
                    {:else}
                      {Math.round(stats.min_points * stats.current_multiplier)}-{Math.round(stats.max_points * stats.current_multiplier)}
                    {/if}
                  {:else}
                    0
                  {/if}
                  pts
                </div>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <div class="bg-white shadow-sm border border-gray-200 rounded-xl overflow-hidden">
    <div class="{pioneerColors.containerBg} px-6 py-4 border-b {pioneerColors.containerBorder}">
      <h3 class="text-lg font-semibold {pioneerColors.headerText}">Contribution Types Overview</h3>
      <p class="text-sm {pioneerColors.descriptionText} mt-1">Summary of contribution types, counts, and statistics</p>
    </div>

    <div class="p-6">

    {#if loading}
      <div class="flex justify-center items-center py-8">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-400"></div>
      </div>
    {:else if error}
      <div class="p-4 text-center text-red-600 bg-red-50 rounded-lg">
        Failed to load statistics: {error}
      </div>
    {:else if typeStats.length === 0}
      <div class="p-8 text-center text-gray-500">
        <Icons name="database" size="lg" className="text-gray-300 mx-auto mb-3" />
        <p>No contribution types found.</p>
      </div>
    {:else if activeTypes.length === 0}
      <div class="p-8 text-center text-gray-500">
        <Icons name="sparkles" size="lg" className="text-gray-300 mx-auto mb-3" />
        <p>No contributions have been made yet. Be the first to contribute!</p>
      </div>
    {:else}
      <div class="space-y-4">
        {#each activeTypes as stats}
          <button
            onclick={() => push(`/contribution-type/${stats.id}`)}
            class="w-full bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all duration-200 text-left group"
          >
            <div class="flex items-center justify-between gap-6">
              <!-- Left side: Title and Description -->
              <div class="flex-1 min-w-0">
                <!-- Title in badge-like container with optional icon -->
                <div class="inline-flex items-center gap-2 mb-2">
                  {#if stats.icon}
                    <div class="w-9 h-9 {pioneerColors.headerBg} rounded-full flex items-center justify-center text-lg">
                      {stats.icon}
                    </div>
                  {/if}
                  <span class="inline-block px-3 py-1 {pioneerColors.headerBg} {pioneerColors.headerText} rounded-full text-sm font-semibold">
                    {stats.name}
                  </span>
                </div>

                {#if stats.description}
                  <p class="text-sm text-gray-600 line-clamp-2 mb-3">{stats.description}</p>
                {/if}

                <!-- Stats badges row with gray colors -->
                <div class="flex flex-wrap items-center gap-3">
                  <!-- Contributions count -->
                  <div class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 border border-gray-200 rounded-md">
                    <Icons name="document" size="xs" className="text-gray-500" />
                    <span class="text-gray-700 font-semibold text-sm">{stats.count}</span>
                    <span class="text-gray-500 text-sm">contributions</span>
                  </div>

                  <!-- Participants -->
                  <div class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 border border-gray-200 rounded-md">
                    <Icons name="users" size="xs" className="text-gray-500" />
                    <span class="text-gray-700 font-semibold text-sm">{stats.participants_count}</span>
                    <span class="text-gray-500 text-sm">participants</span>
                  </div>

                  <!-- Last earned -->
                  <div class="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-50 border border-gray-200 rounded-md">
                    <Icons name="clock" size="xs" className="text-gray-500" />
                    <span class="text-gray-500 text-sm">Last contribution:</span>
                    <span class="text-gray-700 font-medium text-sm">{formatDate(stats.last_earned)}</span>
                  </div>
                </div>
              </div>

              <!-- Right side: Points badge -->
              <div class="flex-shrink-0">
                <div class="px-4 py-2 {pioneerColors.headerBg} {pioneerColors.headerIcon} rounded-lg font-bold text-sm">
                  {#if stats.min_points != null && stats.max_points != null && stats.current_multiplier != null}
                    {#if stats.min_points === stats.max_points}
                      {Math.round(stats.min_points * stats.current_multiplier)}
                    {:else}
                      {Math.round(stats.min_points * stats.current_multiplier)}-{Math.round(stats.max_points * stats.current_multiplier)}
                    {/if}
                  {:else}
                    0
                  {/if}
                  pts
                </div>
              </div>
            </div>
          </button>
        {/each}
      </div>
    {/if}
    </div>
  </div>
</div>

<style>
  .line-clamp-1 {
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>