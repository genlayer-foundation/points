<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import ContributionsList from '../components/ContributionsList.svelte';
  import Pagination from '../components/Pagination.svelte';
  import { contributionsAPI, usersAPI } from '../lib/api';

  // === FILTER STATE ===
  let participantFilter = $state(''); // Name or address
  let selectedCategory = $state(''); // '', 'validator', 'builder'
  let selectedTypeId = $state(''); // Single type ID (not multi-select)
  let sortBy = $state('-contribution_date'); // Sorting

  // === APPLIED FILTERS (what's actually being used) ===
  let appliedTypeId = $state(''); // Track which type filter is actually applied

  // === DATA STATE ===
  let contributions = $state([]);
  let loading = $state(false);
  let error = $state(null);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let pageSize = 20;

  // === TYPES FOR DROPDOWN ===
  let contributionTypes = $state([]);
  let loadingTypes = $state(false);

  // === USER DETAILS (if filtering by address) ===
  let userDetails = $state(null);

  // Helper to check if string looks like address
  function looksLikeAddress(str) {
    return str && str.trim().startsWith('0x');
  }

  // === FETCH FUNCTIONS ===
  async function loadContributions() {
    loading = true;
    error = null;

    try {
      const params = {
        page: currentPage,
        page_size: pageSize,
        ordering: sortBy,
        // Only group if no specific type is applied
        group_consecutive: !appliedTypeId
      };

      // Participant filter
      if (participantFilter?.trim()) {
        const filter = participantFilter.trim();
        if (looksLikeAddress(filter)) {
          params.user_address = filter;
        } else {
          params.search = filter;
        }
      }

      // Category filter
      if (selectedCategory) params.category = selectedCategory;

      // Type filter - use the applied type, not the selected one
      if (appliedTypeId) params.contribution_type = appliedTypeId;

      // Fetch contributions
      const response = await contributionsAPI.getContributions(params);
      contributions = response.data.results || [];
      totalCount = response.data.count || 0;
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load contributions';
      loading = false;
    }
  }

  async function loadContributionTypes() {
    if (!selectedCategory) {
      contributionTypes = [];
      return;
    }

    loadingTypes = true;
    try {
      const response = await contributionsAPI.getContributionTypes({ category: selectedCategory });
      contributionTypes = response.data.results || response.data || [];
    } catch (err) {
      contributionTypes = [];
    } finally {
      loadingTypes = false;
    }
  }

  async function loadUserDetails(address) {
    if (!address || !looksLikeAddress(address)) {
      userDetails = null;
      return;
    }
    try {
      const response = await usersAPI.getUserByAddress(address.trim());
      userDetails = response.data;
    } catch {
      userDetails = null;
    }
  }

  // === FILTER HANDLERS ===
  function applyFilters() {
    currentPage = 1;
    // Store the applied type filter
    appliedTypeId = selectedTypeId;
    if (participantFilter && looksLikeAddress(participantFilter)) {
      loadUserDetails(participantFilter);
    } else {
      userDetails = null;
    }
    updateUrl();
    loadContributions();
  }

  function clearFilters() {
    participantFilter = '';
    selectedCategory = '';
    selectedTypeId = '';
    appliedTypeId = '';
    sortBy = '-contribution_date';
    userDetails = null;
    currentPage = 1;
    contributionTypes = [];
    updateUrl();
    loadContributions();
  }

  async function handleCategoryChange() {
    selectedTypeId = '';
    await loadContributionTypes();
  }

  function handlePageChange(event) {
    currentPage = event.detail;
    updateUrl();
    loadContributions();
  }

  // === URL MANAGEMENT ===
  function parseUrlParams() {
    const queryString = window.location.hash.includes('?')
      ? window.location.hash.split('?')[1]
      : '';
    const params = new URLSearchParams(queryString);

    if (params.get('user')) participantFilter = params.get('user');
    if (params.get('category')) selectedCategory = params.get('category');
    if (params.get('type')) {
      // Keep as string to match HTML select value type
      selectedTypeId = params.get('type');
      appliedTypeId = params.get('type'); // URL params are implicitly applied
    }
    if (params.get('sort')) sortBy = params.get('sort');
    if (params.get('page')) currentPage = Number(params.get('page'));
  }

  function updateUrl() {
    const params = new URLSearchParams();
    if (participantFilter) params.set('user', participantFilter);
    if (selectedCategory) params.set('category', selectedCategory);
    if (selectedTypeId) params.set('type', selectedTypeId);
    if (sortBy !== '-contribution_date') params.set('sort', sortBy);
    if (currentPage > 1) params.set('page', String(currentPage));

    const queryString = params.toString();
    const newUrl = queryString ? `/all-contributions?${queryString}` : '/all-contributions';
    window.history.replaceState({}, '', `#${newUrl}`);
  }

  // === LIFECYCLE ===
  onMount(async () => {
    parseUrlParams();
    if (selectedCategory) await loadContributionTypes();
    if (participantFilter && looksLikeAddress(participantFilter)) {
      await loadUserDetails(participantFilter);
    }
    await loadContributions();
  });
</script>

<div class="space-y-6">
  <!-- HEADER -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">
        {#if userDetails}
          {userDetails.name || 'Participant'}'s Contributions
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
  </div>

  <!-- FILTERS -->
  <div class="bg-white shadow rounded-lg p-4 space-y-4">
    <!-- Row 1: Participant, Category, Contribution Type -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Participant</label>
        <input
          type="text"
          bind:value={participantFilter}
          placeholder="Name or address (0x...)"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Category</label>
        <select
          bind:value={selectedCategory}
          onchange={handleCategoryChange}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
        >
          <option value="">All Categories</option>
          <option value="validator">Validator</option>
          <option value="builder">Builder</option>
        </select>
      </div>

      {#if selectedCategory}
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Contribution Type</label>
          <select
            bind:value={selectedTypeId}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">All Types</option>
            {#if loadingTypes}
              <option disabled>Loading...</option>
            {:else}
              {#each contributionTypes as type}
                <option value={String(type.id)}>{type.name}</option>
              {/each}
            {/if}
          </select>
        </div>
      {/if}
    </div>

    <!-- Row 2: Action buttons -->
    <div class="flex justify-end gap-2">
      <button
        onclick={applyFilters}
        class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors font-medium"
      >
        Apply Filters
      </button>
      <button
        onclick={clearFilters}
        class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors font-medium"
      >
        Clear Filters
      </button>
    </div>
  </div>

  <!-- SORT BY (outside filters, on the right) -->
  <div class="flex justify-end">
    <div class="flex items-center gap-2">
      <label for="sort-select" class="text-sm font-medium text-gray-700">Sort By:</label>
      <select
        id="sort-select"
        bind:value={sortBy}
        onchange={applyFilters}
        class="px-3 py-1.5 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500 text-sm"
      >
        <option value="-contribution_date">Newest First</option>
        <option value="contribution_date">Oldest First</option>
        <option value="-frozen_global_points">Highest Points</option>
        <option value="frozen_global_points">Lowest Points</option>
      </select>
    </div>
  </div>

  <!-- RESULTS -->
  <ContributionsList
    {contributions}
    {loading}
    {error}
    showUser={true}
    category={selectedCategory}
    disableGrouping={!!appliedTypeId}
  />

  <!-- PAGINATION -->
  {#if totalCount > pageSize && !loading}
    <Pagination
      page={currentPage}
      limit={pageSize}
      {totalCount}
      on:pageChange={handlePageChange}
    />
  {/if}
</div>
