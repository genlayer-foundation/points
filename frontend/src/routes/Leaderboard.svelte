<script>
  import { onMount } from 'svelte';
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import { leaderboardAPI } from '../lib/api';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  
  // State management
  let leaderboard = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let searchQuery = $state('');
  
  // Filter leaderboard based on search
  let filteredLeaderboard = $derived(
    !searchQuery ? leaderboard : leaderboard.filter(entry => {
      const query = searchQuery.toLowerCase();
      const name = entry.user_details?.name?.toLowerCase() || '';
      const address = entry.user_details?.address?.toLowerCase() || '';
      return name.includes(query) || address.includes(query);
    })
  );
  
  // Fetch data based on category
  async function fetchLeaderboard() {
    try {
      loading = true;
      error = null;
      
      let response;
      if ($currentCategory === 'global') {
        response = await leaderboardAPI.getLeaderboard();
        leaderboard = response.data || [];
      } else {
        // Fetch category-specific leaderboard using the category endpoint
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
      
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load leaderboard';
      loading = false;
    }
  }
  
  // Fetch on mount and when category changes
  onMount(() => {
    fetchLeaderboard();
  });
  
  // Re-fetch when category changes
  $effect(() => {
    if ($currentCategory) {
      fetchLeaderboard();
    }
  });
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">
        {$currentCategory === 'global' ? 'Global' : 
         $currentCategory === 'builders' ? 'Builders' : 'Validators'} Leaderboard
      </h1>
      <p class="mt-1 text-sm text-gray-500">
        Complete rankings of {$currentCategory === 'global' ? 'all participants' : $currentCategory}
      </p>
    </div>
    
    {#if !loading && !error && leaderboard.length > 0}
      <div class="w-full sm:w-64">
        <label for="search" class="sr-only">Search participants</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
          </div>
          <input
            id="search"
            bind:value={searchQuery}
            type="search"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            placeholder="Search by name or address"
          />
        </div>
      </div>
    {/if}
  </div>
  
  {#if loading}
    <div class="flex justify-center items-center p-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border-l-4 border-red-400 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">Error loading leaderboard</h3>
          <p class="mt-1 text-sm text-red-700">{error}</p>
        </div>
      </div>
    </div>
  {:else}
    <div class="{$categoryTheme.bg === 'bg-white' ? 'bg-white' : 'bg-white/90'} shadow rounded-lg">
      {#if searchQuery && filteredLeaderboard.length === 0}
        <div class="p-6 text-center text-gray-500">
          No participants found matching "{searchQuery}"
        </div>
      {:else}
        <div class="px-4 py-3 border-b border-gray-200">
          <p class="text-sm text-gray-700">
            Showing {searchQuery ? `${filteredLeaderboard.length} of` : ''} {leaderboard.length} participants
          </p>
        </div>
        <LeaderboardTable
          entries={filteredLeaderboard}
          loading={false}
          error={null}
          showHeader={false}
        />
      {/if}
    </div>
  {/if}
</div>

<style>
  /* Additional styles if needed */
</style>