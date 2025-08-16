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
    className = ''
  } = $props();

  let leaderboard = $state([]);
  let loading = $state(true);
  let error = $state(null);

  async function fetchLeaderboard() {
    try {
      loading = true;
      
      let response;
      if ($currentCategory === 'global') {
        response = await leaderboardAPI.getLeaderboard();
        leaderboard = response.data || [];
      } else {
        // Use category-specific endpoint
        response = await leaderboardAPI.getCategoryLeaderboard($currentCategory);
        // Transform the entries to match the expected format
        leaderboard = (response.data.entries || []).map(entry => ({
          rank: entry.rank,
          total_points: entry.total_points,
          user_details: {
            id: entry.user.id,
            name: entry.user.name,
            address: entry.user.address,
          }
        }));
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
    if ($currentCategory && $currentCategory !== previousCategory) {
      previousCategory = $currentCategory;
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