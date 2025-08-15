<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import LeaderboardTable from './LeaderboardTable.svelte';
  import { leaderboardAPI } from '../lib/api';

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

  onMount(async () => {
    try {
      loading = true;
      const response = await leaderboardAPI.getLeaderboard();
      leaderboard = response.data || [];
      if (limit && leaderboard.length > limit) {
        leaderboard = leaderboard.slice(0, limit);
      }
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load leaderboard';
      loading = false;
    }
  });
</script>

<div class="space-y-4 {className}">
  <div class="flex justify-between items-center">
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
  
  <LeaderboardTable
    entries={leaderboard}
    {loading}
    {error}
    {compact}
    {hideAddress}
    {showHeader}
  />
</div>