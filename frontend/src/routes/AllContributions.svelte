<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import ContributionsList from '../components/ContributionsList.svelte';
  import Pagination from '../components/Pagination.svelte';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';
  import { contributionsAPI, usersAPI } from '../lib/api';

  // === FILTER STATE ===
  let participantFilter = $state(''); // Name or address
  let selectedCategory = $state('validator'); // 'validator' or 'builder' (no "all" option)
  let selectedContributionType = $state(null); // Full contribution type object
  let sortBy = $state('-contribution_date'); // Sorting

  // === APPLIED FILTERS (what's actually being used) ===
  let appliedCategory = $state('validator');
  let appliedTypeId = $state(''); // Track which type filter is actually applied

  // === DATA STATE ===
  let contributions = $state([]);
  let loading = $state(false);
  let error = $state(null);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let pageSize = 20;

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

      // Category filter - use applied category
      if (appliedCategory) params.category = appliedCategory;

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
    // Store the applied filters
    appliedCategory = selectedCategory;
    appliedTypeId = selectedContributionType?.id || '';

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
    selectedCategory = 'validator'; // Reset to default
    selectedContributionType = null;
    appliedCategory = 'validator';
    appliedTypeId = '';
    sortBy = '-contribution_date';
    userDetails = null;
    currentPage = 1;
    updateUrl();
    loadContributions();
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

    // Category defaults to 'validator' if not provided
    const urlCategory = params.get('category');
    if (urlCategory === 'validator' || urlCategory === 'builder') {
      selectedCategory = urlCategory;
      appliedCategory = urlCategory;
    }

    if (params.get('type')) {
      // Store the type ID to be selected after types load
      const typeId = params.get('type');
      appliedTypeId = typeId;
      // selectedContributionType will be set by ContributionSelection when it loads
    }
    if (params.get('sort')) sortBy = params.get('sort');
    if (params.get('page')) currentPage = Number(params.get('page'));
  }

  function updateUrl() {
    const params = new URLSearchParams();
    if (participantFilter) params.set('user', participantFilter);
    if (appliedCategory) params.set('category', appliedCategory);
    if (appliedTypeId) params.set('type', String(appliedTypeId));
    if (sortBy !== '-contribution_date') params.set('sort', sortBy);
    if (currentPage > 1) params.set('page', String(currentPage));

    const queryString = params.toString();
    const newUrl = queryString ? `/all-contributions?${queryString}` : '/all-contributions';
    window.history.replaceState({}, '', `#${newUrl}`);
  }

  // === LIFECYCLE ===
  onMount(async () => {
    parseUrlParams();
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
  <div class="bg-white shadow rounded-lg p-4 space-y-4 filters-container">
    <!-- Category and Contribution Type Selection -->
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">Contribution Type</label>
      <ContributionSelection
        bind:selectedCategory
        bind:selectedContributionType
        defaultContributionType={appliedTypeId ? Number(appliedTypeId) : null}
        onlySubmittable={false}
      />
    </div>

    <!-- Participant Filter and Action buttons on same row -->
    <div class="flex flex-col sm:flex-row gap-4 items-end">
      <!-- Participant Filter -->
      <div class="flex-1">
        <label class="block text-sm font-medium text-gray-700 mb-1">Participant</label>
        <input
          type="text"
          bind:value={participantFilter}
          placeholder="Name or address (0x...)"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      <!-- Action buttons -->
      <div class="flex gap-2 flex-shrink-0">
        <button
          onclick={applyFilters}
          class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors font-medium whitespace-nowrap"
        >
          Apply Filters
        </button>
        <button
          onclick={clearFilters}
          class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors font-medium whitespace-nowrap"
        >
          Clear Filters
        </button>
      </div>
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
    category={appliedCategory}
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

<style>
  /* Hide the selection info box from ContributionSelection component */
  .filters-container :global(.selection-info) {
    display: none;
  }
</style>
