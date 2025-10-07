<script>
  import { onMount } from 'svelte';
  import { location, push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Badge from '../components/Badge.svelte';
  import Avatar from '../components/Avatar.svelte';
  import Pagination from '../components/Pagination.svelte';
  import { contributionsAPI, usersAPI } from '../lib/api';

  // Core state
  let contributions = $state([]);
  let loading = $state(false);
  let error = $state(null);
  let totalCount = $state(0);

  // Pagination
  let currentPage = $state(1);
  let pageSize = 20;

  // Filters - all start empty/default
  let userAddress = $state('');
  let selectedCategory = $state(''); // empty string means all
  let selectedTypeIds = $state(new Set()); // Multi-select for types
  let sortBy = $state('-contribution_date'); // default to newest first

  // Contribution types for the selected category
  let contributionTypes = $state([]);
  let loadingTypes = $state(false);
  let typeSearchText = $state(''); // Search text for filtering types

  // User details if filtering by user
  let userDetails = $state(null);

  // Track expanded rows
  let expandedRows = $state(new Set());

  // Toggle row expansion
  function toggleRowExpansion(contributionId) {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(contributionId)) {
      newExpanded.delete(contributionId);
    } else {
      newExpanded.add(contributionId);
    }
    expandedRows = newExpanded;
  }

  // Check if we have any active filters
  let hasActiveFilters = $derived(() => {
    return userAddress || selectedCategory || selectedTypeIds.size > 0;
  });

  // Filter contribution types based on search text
  let filteredTypes = $derived(() => {
    if (!typeSearchText || typeSearchText.trim() === '') {
      return contributionTypes;
    }

    const searchLower = typeSearchText.toLowerCase().trim();
    return contributionTypes.filter(type =>
      type.name.toLowerCase().includes(searchLower)
    );
  });

  // Fetch contributions from API
  async function loadContributions() {
    loading = true;
    error = null;

    try {
      let allContributions = [];

      if (selectedTypeIds.size === 0) {
        // No specific types selected - fetch normally
        const params = {
          page: currentPage,
          page_size: pageSize,
          ordering: sortBy,
          group_consecutive: false
        };

        if (userAddress?.trim()) {
          params.user_address = userAddress.trim();
        }
        if (selectedCategory) {
          params.category = selectedCategory;
        }

        const response = await contributionsAPI.getContributions(params);
        contributions = response.data.results || [];
        totalCount = response.data.count || 0;

      } else {
        // One or more types selected - use OR logic
        const typeIds = Array.from(selectedTypeIds);
        const allResults = [];

        // Fetch contributions for each selected type
        for (const typeId of typeIds) {

          const params = {
            page: 1, // Always get from page 1 to get all results
            page_size: 1000, // Get plenty of results
            ordering: sortBy,
            group_consecutive: false,
            contribution_type: typeId
          };

          if (userAddress?.trim()) {
            params.user_address = userAddress.trim();
          }
          if (selectedCategory) {
            params.category = selectedCategory;
          }

          try {
            const response = await contributionsAPI.getContributions(params);
            const results = response.data.results || [];
            allResults.push(...results);
          } catch (err) {
            // Silently continue if one type fails
          }
        }

        // Remove duplicates by contribution ID (in case of overlaps)
        const uniqueContributions = [];
        const seenIds = new Set();

        for (const contrib of allResults) {
          if (!seenIds.has(contrib.id)) {
            seenIds.add(contrib.id);
            uniqueContributions.push(contrib); // Use push, not add
          }
        }

        // Sort the combined results
        uniqueContributions.sort((a, b) => {
          if (sortBy === '-contribution_date' || sortBy === 'contribution_date') {
            const dateA = new Date(a.contribution_date);
            const dateB = new Date(b.contribution_date);
            return sortBy.startsWith('-') ? dateB - dateA : dateA - dateB;
          } else if (sortBy === '-frozen_global_points' || sortBy === 'frozen_global_points') {
            const pointsA = a.frozen_global_points || a.points || 0;
            const pointsB = b.frozen_global_points || b.points || 0;
            return sortBy.startsWith('-') ? pointsB - pointsA : pointsA - pointsB;
          }
          return 0;
        });

        // Apply client-side pagination
        const startIndex = (currentPage - 1) * pageSize;
        const endIndex = startIndex + pageSize;
        contributions = uniqueContributions.slice(startIndex, endIndex);
        totalCount = uniqueContributions.length;
      }
    } catch (err) {
      error = err.message || 'Failed to load contributions';
      contributions = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  // Fetch contribution types for a category
  async function loadContributionTypes(category) {
    if (!category || category === '') {
      contributionTypes = [];
      return;
    }

    loadingTypes = true;

    try {
      const params = { category };
      const response = await contributionsAPI.getContributionTypes(params);

      // The API returns an axios response with data property
      if (response && response.data) {
        // Handle paginated response
        contributionTypes = response.data.results || response.data || [];
      } else {
        contributionTypes = [];
      }

      // Clear selected types that are not in the new list
      const validTypeIds = new Set(contributionTypes.map(t => t.id));
      const newSelectedIds = new Set();
      for (const id of selectedTypeIds) {
        if (validTypeIds.has(id)) {
          newSelectedIds.add(id);
        }
      }
      selectedTypeIds = newSelectedIds;
    } catch (err) {
      contributionTypes = [];
    } finally {
      loadingTypes = false;
    }
  }

  // Fetch user details
  async function loadUserDetails(address) {
    if (!address || !address.trim()) {
      userDetails = null;
      return;
    }

    try {
      const response = await usersAPI.getUserByAddress(address.trim());
      userDetails = response.data;
    } catch (err) {
      userDetails = null;
    }
  }

  // Handle user address input
  function handleUserAddressChange(e) {
    userAddress = e.target.value;
  }

  // Handle category selection
  async function handleCategoryChange(e) {
    const newCategory = e.target.value;

    selectedCategory = newCategory;
    selectedTypeIds = new Set(); // Reset types when category changes
    contributionTypes = []; // Clear current types immediately
    typeSearchText = ''; // Clear search text when category changes

    // Load types for the new category
    if (newCategory && newCategory !== '') {
      await loadContributionTypes(newCategory);
    } else {
      contributionTypes = [];
    }
  }

  // Handle type selection (multi-select)
  function handleTypeSelect(typeId) {
    // Ensure we're working with integers for consistency
    const intTypeId = parseInt(typeId, 10);

    // Multi-select behavior: toggle selection
    const newSelectedIds = new Set(selectedTypeIds);
    if (newSelectedIds.has(intTypeId)) {
      newSelectedIds.delete(intTypeId);
    } else {
      newSelectedIds.add(intTypeId);
    }
    selectedTypeIds = newSelectedIds;
  }

  // Handle sorting
  function handleSort(field) {
    // Toggle between ascending and descending
    if (sortBy === field) {
      sortBy = `-${field}`;
    } else if (sortBy === `-${field}`) {
      sortBy = field;
    } else {
      // New field, default to descending
      sortBy = `-${field}`;
    }

    // Reset to page 1 and reload
    currentPage = 1;
    updateUrl();
    loadContributions();
  }

  // Apply filters
  async function applyFilters() {
    currentPage = 1; // Reset to first page

    // Update URL to reflect current filters
    updateUrl();

    // Load user details if we have an address
    if (userAddress) {
      await loadUserDetails(userAddress);
    } else {
      userDetails = null;
    }

    // Load contributions with current filters
    await loadContributions();
  }

  // Clear all filters
  function clearFilters() {
    userAddress = '';
    selectedCategory = '';
    selectedTypeIds = new Set();
    sortBy = '-contribution_date';
    contributionTypes = [];
    userDetails = null;
    currentPage = 1;

    // Update URL to remove all params
    updateUrl();

    // Reload with no filters
    loadContributions();
  }

  // Handle page change
  function handlePageChange(event) {
    currentPage = event.detail;
    updateUrl();
    loadContributions();
  }

  // Format date for display
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }

  // Get sort icon for a field
  function getSortIcon(field) {
    if (sortBy === `-${field}`) {
      // Descending - active
      return `<svg class="w-4 h-4 ml-1 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>`;
    } else if (sortBy === field) {
      // Ascending - active
      return `<svg class="w-4 h-4 ml-1 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>`;
    } else {
      // Not sorted by this field - show both arrows with opacity
      return `<svg class="w-4 h-4 ml-1 inline-block opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>`;
    }
  }

  // Parse URL parameters
  function parseUrlParams() {
    // Get the query string from the current location
    const queryString = window.location.hash.includes('?')
      ? window.location.hash.split('?')[1]
      : '';
    const params = new URLSearchParams(queryString);

    const user = params.get('user');
    if (user) userAddress = user;

    const category = params.get('category');
    if (category) selectedCategory = category;

    // Parse multiple type IDs
    const types = params.get('types');
    if (types) {
      selectedTypeIds = new Set(types.split(',').map(id => parseInt(id, 10)));
    }

    const sort = params.get('sort');
    if (sort) sortBy = sort;

    const page = params.get('page');
    if (page) currentPage = parseInt(page, 10);
  }

  // Update URL with current filters
  function updateUrl() {
    const params = new URLSearchParams();

    if (userAddress) params.set('user', userAddress);
    if (selectedCategory) params.set('category', selectedCategory);
    if (selectedTypeIds.size > 0) {
      params.set('types', Array.from(selectedTypeIds).join(','));
    }
    if (sortBy && sortBy !== '-contribution_date') params.set('sort', sortBy);
    if (currentPage > 1) params.set('page', currentPage.toString());

    const queryString = params.toString();
    const newUrl = queryString ? `/all-contributions?${queryString}` : '/all-contributions';

    // Update URL without triggering navigation
    window.history.replaceState({}, '', `#${newUrl}`);
  }

  // Initialize on mount
  onMount(async () => {
    // Parse URL params first
    parseUrlParams();

    // Load types if category is selected
    if (selectedCategory) {
      await loadContributionTypes(selectedCategory);
    }

    // Load user details if address is provided
    if (userAddress) {
      await loadUserDetails(userAddress);
    }

    // Load contributions with initial filters
    await loadContributions();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">
        {#if userDetails}
          {userDetails.name || userDetails.address}'s Contributions
        {:else}
          All Contributions
        {/if}
      </h1>
      <p class="mt-1 text-sm text-gray-600">
        {#if loading}
          Loading...
        {:else}
          {totalCount} total contributions
        {/if}
      </p>
    </div>

    {#if hasActiveFilters()}
      <button
        onclick={clearFilters}
        class="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
      >
        Clear Filters
      </button>
    {/if}
  </div>

  <!-- Filters -->
  <div class="bg-white shadow rounded-lg p-4">
    <div class="space-y-4">
      <!-- Row 1: Participant Address, Category, and Type Search -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <!-- Participant Address -->
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Participant Address
          </label>
          <input
            type="text"
            value={userAddress}
            onchange={handleUserAddressChange}
            placeholder="0x..."
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>

        <!-- Category -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            value={selectedCategory}
            onchange={handleCategoryChange}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">All Categories</option>
            <option value="validator">Validator</option>
            <option value="builder">Builder</option>
          </select>
        </div>

        <!-- Type Search (only show when category is selected) -->
        {#if selectedCategory && selectedCategory !== ''}
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Search Contribution Types
            </label>
            <div class="relative">
              <input
                type="text"
                bind:value={typeSearchText}
                placeholder="Filter types..."
                class="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              {#if typeSearchText}
                <button
                  onclick={() => typeSearchText = ''}
                  class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  title="Clear search"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              {/if}
            </div>
          </div>
        {/if}
      </div>

      <!-- Row 2: Contribution Types (only show if category selected) -->
      {#if selectedCategory && selectedCategory !== ''}
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Contribution Type
            {#if typeSearchText && filteredTypes().length < contributionTypes.length}
              <span class="text-xs text-gray-500 font-normal ml-2">
                (Showing {filteredTypes().length} of {contributionTypes.length})
              </span>
            {/if}
          </label>
          {#if loadingTypes}
            <div class="text-sm text-gray-500">Loading types...</div>
          {:else if contributionTypes.length > 0}
            {#if filteredTypes().length > 0}
              <div class="flex flex-wrap gap-2">
                {#each filteredTypes() as type}
                <button
                  onclick={() => handleTypeSelect(type.id)}
                  class="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-full transition-colors
                    {selectedTypeIds.has(type.id)
                      ? 'bg-primary-600 text-white hover:bg-primary-700'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'}"
                >
                  {#if selectedTypeIds.has(type.id)}
                    <svg class="w-3 h-3 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                    </svg>
                  {/if}
                  {type.name}
                </button>
                {/each}
              </div>
              {#if selectedTypeIds.size > 1}
                <p class="mt-2 text-xs text-blue-600">
                  <svg class="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                  </svg>
                  {selectedTypeIds.size} types selected - results will be filtered to show contributions matching any of these types
                </p>
              {/if}
            {:else}
              <div class="text-sm text-gray-500">
                {#if typeSearchText}
                  No types matching "{typeSearchText}"
                {:else}
                  No contribution types found
                {/if}
              </div>
            {/if}
          {:else}
            <div class="text-sm text-gray-500">No contribution types found for this category</div>
          {/if}
        </div>
      {/if}

      <!-- Apply Button -->
      <div class="flex justify-end">
        
        <button
          onclick={applyFilters}
          disabled={loading}
          class="px-6 py-2 text-sm font-medium text-white bg-primary-600 rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Apply Filters
        </button>
      </div>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white shadow rounded-lg overflow-hidden">
    {#if loading}
      <div class="p-8 text-center">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        <p class="mt-2 text-sm text-gray-600">Loading contributions...</p>
      </div>
    {:else if error}
      <div class="p-8 text-center">
        <p class="text-red-600">{error}</p>
      </div>
    {:else if contributions.length === 0}
      <div class="p-8 text-center">
        <p class="text-gray-600">No contributions found</p>
        {#if hasActiveFilters()}
          <button
            onclick={clearFilters}
            class="mt-4 px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            Clear filters and try again
          </button>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              {#if !userAddress}
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Participant
                </th>
              {/if}
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Type
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onclick={() => handleSort('contribution_date')}
                  class="group inline-flex items-center hover:text-gray-900 transition-colors"
                >
                  Date
                  {@html getSortIcon('contribution_date')}
                </button>
              </th>
              <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button
                  onclick={() => handleSort('frozen_global_points')}
                  class="group inline-flex items-center hover:text-gray-900 transition-colors"
                >
                  Points
                  {@html getSortIcon('frozen_global_points')}
                </button>
              </th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                <span class="mr-4">Evidence</span>
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each contributions as contribution, i}
              <tr class="{i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-50 transition-colors">
                {#if !userAddress}
                  <td class="px-6 py-4 whitespace-nowrap">
                    {#if contribution.user_details}
                      <div class="flex items-center">
                        <div class="flex-shrink-0 mr-3">
                          <Avatar
                            user={contribution.user_details}
                            size="sm"
                            clickable={true}
                          />
                        </div>
                        <div>
                          <button
                            onclick={() => push(`/participant/${contribution.user_details.address}`)}
                            class="text-left hover:opacity-80 transition-opacity"
                          >
                            <div class="text-sm font-medium text-gray-900">
                              {contribution.user_details.name || 'Participant'}
                            </div>
                            <div class="text-xs text-gray-500">
                              {`${contribution.user_details.address.substring(0, 6)}...${contribution.user_details.address.substring(contribution.user_details.address.length - 4)}`}
                            </div>
                          </button>
                        </div>
                      </div>
                    {:else}
                      <span class="text-gray-500 text-sm">Unknown</span>
                    {/if}
                  </td>
                {/if}
                <td class="px-6 py-4 whitespace-nowrap">
                  <Badge
                    badge={{
                      id: contribution.contribution_type?.id || contribution.contribution_type,
                      name: contribution.contribution_type_name || contribution.contribution_type?.name || 'Unknown',
                      description: '',
                      points: 0,
                      actionId: contribution.contribution_type?.id || contribution.contribution_type,
                      actionName: contribution.contribution_type_name || contribution.contribution_type?.name || 'Unknown',
                      evidenceUrl: ''
                    }}
                    color='green'
                    clickable={true}
                  />
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(contribution.contribution_date)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-center">
                  <div class="text-sm font-medium text-gray-900">
                    {contribution.frozen_global_points || contribution.points || 0}
                  </div>
                </td>
                <td class="px-6 py-4 text-right">
                  {#if (contribution.evidence_items && contribution.evidence_items.length > 0) || contribution.notes}
                    <button
                      onclick={() => toggleRowExpansion(contribution.id)}
                      class="flex items-center justify-end gap-2 w-full hover:opacity-80 transition-opacity"
                    >
                      <div class="flex items-center gap-2">
                        {#if contribution.evidence_items && contribution.evidence_items.length > 0}
                          <span class="inline-flex items-center px-2.5 py-1 text-xs font-medium text-primary-700 bg-primary-50 rounded-full">
                            {contribution.evidence_items.length} {contribution.evidence_items.length === 1 ? 'item' : 'items'}
                          </span>
                        {/if}
                        {#if contribution.notes}
                          <span class="inline-flex items-center px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded-full">
                            Notes
                          </span>
                        {/if}
                      </div>
                      <svg
                        class="w-4 h-4 text-gray-500 transition-transform {expandedRows.has(contribution.id) ? 'rotate-90' : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  {:else}
                    <span class="text-gray-400 text-sm">—</span>
                  {/if}
                </td>
              </tr>
              {#if expandedRows.has(contribution.id)}
                <tr class="{i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}">
                  <td colspan="{userAddress ? 4 : 5}" class="px-8 py-4">
                    <div class="space-y-4">
                      {#if contribution.notes}
                        <div>
                          <h4 class="text-sm font-semibold text-gray-700 mb-2">Notes</h4>
                          <p class="text-sm text-gray-600 whitespace-pre-wrap">{contribution.notes}</p>
                        </div>
                      {/if}

                      {#if contribution.evidence_items && contribution.evidence_items.length > 0}
                        <div>
                          <h4 class="text-sm font-semibold text-gray-700 mb-2">Evidence</h4>
                          <div class="flex flex-wrap gap-3">
                            {#each contribution.evidence_items as evidence}
                              {#if evidence.url || evidence.file_url}
                                <!-- Clickable evidence with URL or file -->
                                <a
                                  href={evidence.url || evidence.file_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class="group flex items-center gap-2 bg-gray-50 hover:bg-gray-100 rounded border border-gray-200 hover:border-primary-300 p-3 max-w-sm transition-all duration-200 cursor-pointer"
                                >
                                  <div class="flex-shrink-0">
                                    {#if evidence.url}
                                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-primary-600 group-hover:text-primary-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                      </svg>
                                    {:else}
                                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-600 group-hover:text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                      </svg>
                                    {/if}
                                  </div>
                                  <div class="flex-1 min-w-0">
                                    <p class="text-xs text-gray-700 group-hover:text-gray-900 line-clamp-2 transition-colors">
                                      {evidence.description || (evidence.url ? 'External Link' : 'Download File')}
                                    </p>
                                  </div>
                                  <div class="flex-shrink-0">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-gray-400 group-hover:text-gray-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                    </svg>
                                  </div>
                                </a>
                              {:else}
                                <!-- Text-only evidence -->
                                <div class="flex items-center gap-2 bg-gray-50 rounded border border-gray-200 p-3 max-w-sm">
                                  <div class="flex-shrink-0">
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                  </div>
                                  <div class="flex-1 min-w-0">
                                    <p class="text-xs text-gray-700 line-clamp-2">{evidence.description}</p>
                                  </div>
                                </div>
                              {/if}
                            {/each}
                          </div>
                        </div>
                      {/if}

                      {#if !contribution.notes && (!contribution.evidence_items || contribution.evidence_items.length === 0)}
                        <p class="text-sm text-gray-500 italic">No additional details available</p>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {#if totalCount > pageSize}
        <div class="border-t border-gray-200">
          <Pagination
            page={currentPage}
            limit={pageSize}
            totalCount={totalCount}
            on:pageChange={handlePageChange}
          />
        </div>
      {/if}
    {/if}
  </div>
</div>