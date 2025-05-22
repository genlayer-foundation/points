<script>
  import { onMount } from 'svelte';
  import ContributionsList from '../components/ContributionsList.svelte';
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
  
  $effect(() => {
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
      loading = true;
      error = null;
      
      const params = {
        page,
        limit,
        ordering: sortOrder
      };
      
      if (selectedType) {
        params.contribution_type = selectedType;
      }
      
      const res = await contributionsAPI.getContributions(params);
      contributions = res.data.results || [];
      totalCount = res.data.count || 0;
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load contributions';
      loading = false;
    }
  }
  
  function handlePageChange(newPage) {
    page = newPage;
  }
  
  function handleTypeChange(event) {
    selectedType = event.target.value;
    page = 1; // Reset to first page when filtering
  }
  
  function handleSortChange(event) {
    sortOrder = event.target.value;
    page = 1; // Reset to first page when sorting
  }
  
  // Calculate total pages with reactive derived value
  let totalPages = $derived(Math.ceil(totalCount / limit));
</script>

<div class="space-y-6">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">Contributions</h1>
    <div class="text-sm text-gray-500">
      Showing {Math.min((page - 1) * limit + 1, totalCount)} - {Math.min(page * limit, totalCount)} of {totalCount} contributions
    </div>
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
  
  <!-- Filters -->
  <div class="bg-white shadow px-4 py-5 sm:rounded-lg sm:p-6">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div>
        <label for="type-filter" class="block text-sm font-medium text-gray-700">Contribution Type</label>
        <select
          id="type-filter"
          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          value={selectedType}
          onchange={handleTypeChange}
        >
          <option value="">All Types</option>
          {#each contributionTypes as type}
            <option value={type.id}>{type.name}</option>
          {/each}
        </select>
      </div>
      
      <div>
        <label for="sort-order" class="block text-sm font-medium text-gray-700">Sort By</label>
        <select
          id="sort-order"
          class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
          value={sortOrder}
          onchange={handleSortChange}
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
  
  <!-- Contributions List -->
  <ContributionsList
    {contributions}
    {loading}
    {error}
    showUser={true}
  />
  
  <!-- Pagination -->
  {#if totalPages > 1}
    <div class="flex justify-center mt-4">
      <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
        <button
          class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          disabled={page === 1}
          onclick={() => handlePageChange(page - 1)}
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
            onclick={() => handlePageChange(pageNum)}
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
            onclick={() => handlePageChange(totalPages)}
          >
            {totalPages}
          </button>
        {/if}
        
        <button
          class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          disabled={page === totalPages}
          onclick={() => handlePageChange(page + 1)}
        >
          <span class="sr-only">Next</span>
          <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </nav>
    </div>
  {/if}
</div>