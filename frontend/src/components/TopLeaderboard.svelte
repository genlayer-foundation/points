<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import LeaderboardTable from './LeaderboardTable.svelte';
  import { leaderboardAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';

  let {
    title = 'Top Validators',
    limit = 5,
    showViewAll = true,
    viewAllPath = '/leaderboard',
    viewAllText = 'View All →',
    compact = true,
    hideAddress = true,
    showHeader = false,
    className = '',
    category = null  // Add optional category prop
  } = $props();

  let leaderboard = $state([]);
  let loading = $state(true);
  let error = $state(null);

  async function fetchLeaderboard() {
    try {
      loading = true;
      
      // Use prop category if provided, otherwise use store category
      const categoryToUse = category || $currentCategory;
      
      let response;
      if (categoryToUse === 'global') {
        response = await leaderboardAPI.getLeaderboard();
        leaderboard = response.data || [];
      } else {
        // Use type-specific endpoint
        response = await leaderboardAPI.getLeaderboardByType(categoryToUse);
        // API now returns array directly, not wrapped in entries
        leaderboard = response.data || [];
      }
      
      if (limit && leaderboard.length > limit) {
        leaderboard = leaderboard.slice(0, limit);
      }
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load leaderboard';
      loading = false;
    }
  }
  
  // Fetch leaderboard when category changes (including initial mount)
  let previousCategory = $state(null);
  
  $effect(() => {
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