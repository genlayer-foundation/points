<script>
  import LeaderboardTable from './LeaderboardTable.svelte';
  import { leaderboardAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';

  let {
    title = 'Top Validators',
    limit = 5,
    showViewAll = true,
    viewAllPath = '/leaderboard',
    viewAllText = 'View All →',
    compact = false,
    hideAddress = true,
    showHeader = false,
    className = '',
    category = null,
    entries = null,  // Optional: pass pre-fetched leaderboard data
    loading: loadingProp = null  // Optional: pass loading state from parent
  } = $props();

  let leaderboard = $state([]);
  let internalLoading = $state(true);
  let error = $state(null);

  // Use prop loading if provided, otherwise use internal state
  let loading = $derived(loadingProp !== null ? loadingProp : internalLoading);

  async function fetchLeaderboard() {
    try {
      internalLoading = true;

      // Use prop category if provided, otherwise use store category
      const categoryToUse = category || $currentCategory;

      let response;
      if (categoryToUse === 'global') {
        response = await leaderboardAPI.getLeaderboard();
        leaderboard = response.data || [];
      } else {
        // Use type-specific endpoint
        response = await leaderboardAPI.getLeaderboardByType(categoryToUse);
        leaderboard = response.data || [];
      }

      if (limit && leaderboard.length > limit) {
        leaderboard = leaderboard.slice(0, limit);
      }
      internalLoading = false;
    } catch (err) {
      error = err.message || 'Failed to load leaderboard';
      internalLoading = false;
    }
  }

  // If entries are provided as prop, use them instead of fetching
  $effect(() => {
    if (entries !== null) {
      leaderboard = limit && entries.length > limit ? entries.slice(0, limit) : entries;
      // Don't set loading here - parent controls it via loadingProp
      error = null;
    }
  });

  // Fetch leaderboard when category changes (only if entries not provided)
  let previousCategory = $state(null);

  $effect(() => {
    // Skip fetching if entries are provided as prop
    if (entries !== null) return;

    // Use prop category if provided, otherwise use store category
    const categoryToUse = category || $currentCategory;
    if (categoryToUse && categoryToUse !== previousCategory) {
      previousCategory = categoryToUse;
      fetchLeaderboard();
    }
  });
</script>

<div class="{className}">
  {#if showHeader !== false}
    <div class="flex items-center gap-2 mb-4">
      <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
      {#if showViewAll}
        <button
          onclick={() => push(viewAllPath)}
          class="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          {viewAllText}
        </button>
      {/if}
    </div>
  {/if}
  
  <LeaderboardTable
    entries={leaderboard}
    {loading}
    {error}
    {compact}
    {hideAddress}
    {showHeader}
  />
</div>