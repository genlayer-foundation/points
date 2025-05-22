<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import ContributionTypeStats from '../components/ContributionTypeStats.svelte';
  import { contributionsAPI, usersAPI } from '../lib/api';
  
  // State management
  let contributions = $state([]);
  let contributionTypes = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let typesError = $state(null);
  let totalCount = $state(0);
  
  // Pagination and filtering
  let page = $state(1);
  let limit = $state(20);
  let selectedType = $state('');
  let sortOrder = $state('-contribution_date');
  let showUser = $state(true);
  
  // Watch for changes in page, selectedType, or sortOrder to trigger data fetch
  $effect(() => {
    // This will automatically track dependencies (page, selectedType, sortOrder)
    fetchContributions();
  });
  
  onMount(async () => {
    try {
      typesError = null;
      const typesRes = await contributionsAPI.getContributionTypes();
      contributionTypes = typesRes.data.results || [];
    } catch (err) {
      typesError = err.message || 'Failed to load contribution types';
      console.error('Failed to load contribution types:', err);
    }
    
    await fetchContributions();
  });
  
  async function fetchContributions() {
    try {
      // Set loading state but keep existing data visible
      loading = true;
      error = null;
      
      // If we're filtering/sorting and have previous contributions, use them during loading
      if (previousContributions.length > 0) {
        // Keep showing the previous contributions during loading
        contributions = previousContributions;
      }
      
      const params = {
        page,
        limit,
        ordering: sortOrder
      };
      
      if (selectedType) {
        params.contribution_type = selectedType;
      }
      
      const res = await contributionsAPI.getContributions(params);
      // Only update the data after new data is received
      totalCount = res.data.count || 0;
      contributions = res.data.results || [];
      
      // Clear previous contributions after loading is complete
      previousContributions = [];
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load contributions';
      // If there's an error, keep the previous contributions visible
      if (previousContributions.length > 0) {
        contributions = previousContributions;
      }
      previousContributions = [];
      loading = false;
    }
  }
  
  // Page changes are now handled directly in the button click handlers
  
  // Keep track of the previous contributions when filtering/sorting
  let previousContributions = [];
  
  // Calculate total pages with reactive derived value
  let totalPages = $derived(Math.ceil(totalCount / limit));
  
  // Format date helper function
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
</script>

<div class="space-y-6">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">Contributions</h1>
  </div>
  
  <!-- Connection error message if needed -->
  {#if error || typesError}
    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-yellow-700">
            Having trouble connecting to the API. Some data might not display correctly.
          </p>
          {#if typesError && error}
            <p class="text-xs text-yellow-600 mt-1">
              Multiple errors occurred while loading data.
            </p>
          {:else if typesError}
            <p class="text-xs text-yellow-600 mt-1">
              {typesError}
            </p>
          {:else if error}
            <p class="text-xs text-yellow-600 mt-1">
              {error}
            </p>
          {/if}
        </div>
      </div>
    </div>
  {/if}
  
  <!-- Contribution Type Statistics -->
  <ContributionTypeStats />
  
  <!-- Contributions List with integrated filters -->
  <div class="bg-white shadow overflow-hidden rounded-lg relative">
    <div class="px-4 py-5 sm:px-6 flex justify-between items-center flex-wrap all-contributions-header">
      <div>
        <h3 class="text-lg leading-6 font-medium text-gray-900">
          All Contributions
        </h3>
        <p class="mt-1 max-w-2xl text-sm text-gray-500">
          Recent contributions with points and multipliers
        </p>
      </div>
      <div class="flex items-center gap-4 mt-2 sm:mt-0">
        <div class="flex items-center">
          <label for="type-filter" class="block text-sm font-medium text-gray-700 mr-2">Filter:</label>
          <select
            id="type-filter"
            class="block w-full min-w-[140px] rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm py-1.5 px-3"
            bind:value={selectedType}
            onchange={() => {
              previousContributions = [...contributions];
              page = 1; // Reset to first page when filtering
            }}
          >
            <option value="">All Types</option>
            {#each contributionTypes as type}
              <option value={type.id}>{type.name}</option>
            {/each}
          </select>
        </div>
        
        <div class="flex items-center">
          <label for="sort-order" class="block text-sm font-medium text-gray-700 mr-2">Sort:</label>
          <select
            id="sort-order"
            class="block w-full min-w-[140px] rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm py-1.5 px-3"
            bind:value={sortOrder}
            onchange={() => {
              previousContributions = [...contributions];
              page = 1; // Reset to first page when sorting
            }}
          >
            <option value="-contribution_date">Newest First</option>
            <option value="contribution_date">Oldest First</option>
            <option value="-points">Highest Points</option>
            <option value="points">Lowest Points</option>
            <option value="-frozen_global_points">Highest Global Points</option>
            <option value="frozen_global_points">Lowest Global Points</option>
          </select>
        </div>
      </div>
    </div>
    
    {#if error}
      <div class="p-6 text-center text-red-500">
        Failed to load contributions: {error}
      </div>
    {:else if contributions.length === 0}
      <div class="p-6 text-center text-gray-500">
        No contributions found.
      </div>
    {:else}
      <!-- Loading overlay -->
      {#if loading}
        <div class="absolute inset-0 bg-white bg-opacity-50 flex justify-center items-center z-10">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {/if}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              {#if showUser}
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contributor
                </th>
              {/if}
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Date
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Base Points
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Multiplier
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Global Points
              </th>
              <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Evidence
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each contributions as contribution, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                {#if showUser}
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                      <div class="text-sm font-medium text-gray-900">
                        <a href={`/participant/${contribution.user_details?.id || contribution.user?.id || contribution.user || 1}`} onclick={(e) => { e.preventDefault(); push(`/participant/${contribution.user_details?.id || contribution.user?.id || contribution.user || 1}`); }}>
                          {contribution.user_details?.name || contribution.user.name || contribution.user_details?.email || contribution.user.email}
                        </a>
                      </div>
                    </div>
                  </td>
                {/if}
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                    {contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type'}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(contribution.contribution_date)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {contribution.points}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {contribution.multiplier_at_creation}x
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="text-sm font-medium text-gray-900">{contribution.frozen_global_points}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  {#if contribution.evidence_url}
                    <a href={contribution.evidence_url} target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:text-primary-900">
                      View
                    </a>
                  {:else}
                    <span class="text-gray-400">None</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
    
    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="bg-white px-4 py-3 border-t border-gray-200">
        <div class="flex justify-between items-center">
          <div class="text-sm text-gray-500">
            Showing {Math.min((page - 1) * limit + 1, totalCount)} - {Math.min(page * limit, totalCount)} of {totalCount} contributions
          </div>
          <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
            <button
              class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
              disabled={page === 1}
              onclick={(e) => {
                e.preventDefault();
                previousContributions = [...contributions];
                page = page - 1;
              }}
            >
              <span class="sr-only">Previous</span>
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
            </button>
            
            {#each Array(Math.min(5, totalPages)) as _, i}
              {@const pageNum = i + 1}
              <button
                class={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${page === pageNum ? 'z-10 bg-primary-50 border-primary-500 text-primary-600' : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'}`}
                onclick={(e) => {
                  e.preventDefault();
                  previousContributions = [...contributions];
                  page = pageNum;
                }}
              >
                {pageNum}
              </button>
            {/each}
            
            {#if totalPages > 5}
              <span class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
                ...
              </span>
              <button
                class={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${page === totalPages ? 'z-10 bg-primary-50 border-primary-500 text-primary-600' : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'}`}
                onclick={(e) => {
                  e.preventDefault();
                  previousContributions = [...contributions];
                  page = totalPages;
                }}
              >
                {totalPages}
              </button>
            {/if}
            
            <button
              class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
              disabled={page === totalPages}
              onclick={(e) => {
                e.preventDefault();
                previousContributions = [...contributions];
                page = page + 1;
              }}
            >
              <span class="sr-only">Next</span>
              <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    {/if}
  </div>
</div>