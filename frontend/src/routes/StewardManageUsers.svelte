<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI } from '../lib/api.js';
  import Avatar from '../components/Avatar.svelte';
  import PaginationEnhanced from '../components/PaginationEnhanced.svelte';
  import { format } from 'date-fns';

  let bannedValidators = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let currentPage = $state(1);
  let pageSize = $state(25);

  // Computed values
  let paginatedValidators = $state([]);
  let totalCount = $state(0);

  // Unban state
  let unbanningValidators = $state(new Set());
  let unbanMessages = $state({});

  // Update total count when banned validators change
  $effect(() => {
    totalCount = bannedValidators?.length || 0;
  });

  // Update paginated validators when banned validators or pagination changes
  $effect(() => {
    if (!bannedValidators || bannedValidators.length === 0) {
      paginatedValidators = [];
      return;
    }

    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    paginatedValidators = bannedValidators.slice(startIndex, endIndex);
  });

  onMount(async () => {
    // Check authentication and steward status
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }

    if (!$userStore.user?.steward) {
      push('/');
      return;
    }

    await loadBannedValidators();
  });

  async function loadBannedValidators() {
    loading = true;
    error = null;

    try {
      // Use the backend API to get banned validators
      const response = await stewardAPI.getBannedValidators();
      const data = response.data;

      // Set the banned validators data
      bannedValidators = data.banned_validators || [];

      // Check for any errors from the backend
      if (data.error) {
        error = data.error;
      }

      loading = false;
    } catch (err) {
      console.error('Error loading banned validators:', err);

      // Handle different types of errors
      if (err.response?.status === 403) {
        error = 'You do not have permission to access this data';
        // Redirect non-stewards
        push('/');
      } else if (err.response?.status === 500) {
        error = 'Server error while fetching banned validators';
      } else {
        error = err.message || 'Failed to load banned validators';
      }

      loading = false;
    }
  }

  function handlePageChange(event) {
    currentPage = event.detail;
  }

  function handlePageSizeChange(event) {
    pageSize = event.detail;
    currentPage = 1; // Reset to first page
  }

  async function unbanValidator(address) {
    // Add to unbanning set
    unbanningValidators.add(address);
    unbanningValidators = new Set(unbanningValidators);

    try {
      const response = await stewardAPI.unbanValidator(address);
      const data = response.data;

      if (data.success) {
        // Show success message
        unbanMessages[address] = { type: 'success', text: 'Validator unbanned successfully' };

        // Reload the banned validators list
        await loadBannedValidators();
      } else {
        // Show error message
        unbanMessages[address] = {
          type: 'error',
          text: data.error || data.message || 'Failed to unban validator'
        };
      }

      // Clear message after 5 seconds
      setTimeout(() => {
        delete unbanMessages[address];
        unbanMessages = { ...unbanMessages };
      }, 5000);

    } catch (err) {
      console.error('Error unbanning validator:', err);

      let errorMessage = 'Failed to unban validator';
      if (err.response?.status === 501) {
        errorMessage = 'Unban functionality not yet implemented';
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      }

      unbanMessages[address] = { type: 'error', text: errorMessage };

      // Clear message after 5 seconds
      setTimeout(() => {
        delete unbanMessages[address];
        unbanMessages = { ...unbanMessages };
      }, 5000);
    } finally {
      // Remove from unbanning set
      unbanningValidators.delete(address);
      unbanningValidators = new Set(unbanningValidators);
    }
  }

  async function unbanAllValidators() {
    if (!confirm('Are you sure you want to unban ALL validators? This action cannot be undone.')) {
      return;
    }

    // Add special key for unban all
    unbanningValidators.add('all');
    unbanningValidators = new Set(unbanningValidators);

    try {
      const response = await stewardAPI.unbanAllValidators();
      const data = response.data;

      if (data.success) {
        // Show success message
        unbanMessages['all'] = { type: 'success', text: 'All validators unbanned successfully' };

        // Reload the banned validators list
        await loadBannedValidators();
      } else {
        // Show error message
        unbanMessages['all'] = {
          type: 'error',
          text: data.error || data.message || 'Failed to unban all validators'
        };
      }

      // Clear message after 5 seconds
      setTimeout(() => {
        delete unbanMessages['all'];
        unbanMessages = { ...unbanMessages };
      }, 5000);

    } catch (err) {
      console.error('Error unbanning all validators:', err);

      let errorMessage = 'Failed to unban all validators';
      if (err.response?.status === 501) {
        errorMessage = 'Unban all functionality not yet implemented';
      } else if (err.response?.data?.error) {
        errorMessage = err.response.data.error;
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      }

      unbanMessages['all'] = { type: 'error', text: errorMessage };

      // Clear message after 5 seconds
      setTimeout(() => {
        delete unbanMessages['all'];
        unbanMessages = { ...unbanMessages };
      }, 5000);
    } finally {
      // Remove from unbanning set
      unbanningValidators.delete('all');
      unbanningValidators = new Set(unbanningValidators);
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-2xl font-bold">Manage Users</h1>
      <p class="text-sm text-gray-600 mt-1">View and manage banned validators</p>
    </div>
    <div class="flex items-center space-x-3">
      {#if totalCount > 0}
        <button
          onclick={unbanAllValidators}
          disabled={unbanningValidators.has('all')}
          class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm font-medium"
        >
          {#if unbanningValidators.has('all')}
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Unbanning All...
          {:else}
            Unban All Validators
          {/if}
        </button>
      {/if}
    </div>
  </div>

  <!-- Global Messages -->
  {#if unbanMessages['all']}
    <div class="mb-6">
      <div class="rounded-md p-4 {unbanMessages['all'].type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}">
        <div class="flex">
          <div class="flex-shrink-0">
            {#if unbanMessages['all'].type === 'success'}
              <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            {:else}
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            {/if}
          </div>
          <div class="ml-3">
            <p class="text-sm font-medium {unbanMessages['all'].type === 'success' ? 'text-green-800' : 'text-red-800'}">
              {unbanMessages['all'].text}
            </p>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Total Banned Count -->
  <div class="bg-white shadow rounded-lg p-6 mb-6">
    <div class="text-left">
      <h2 class="text-lg font-medium text-gray-900 mb-2">Total Banned Validators</h2>
      <div class="text-3xl font-bold text-red-600">{totalCount}</div>
    </div>
  </div>

  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if bannedValidators.length === 0}
    <div class="text-center py-12 bg-white rounded-lg shadow">
      <div class="mx-auto h-12 w-12 text-gray-400 mb-4">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
      </div>
      <p class="text-gray-600">No banned validators found.</p>
      <p class="text-sm text-gray-500 mt-1">All validators are currently active or not whitelisted.</p>
    </div>
  {:else}
    <!-- Top Pagination -->
    {#if totalCount > pageSize}
      <div class="mb-4">
        <PaginationEnhanced
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 25, 50, 100]}
          showPageSize={true}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      </div>
    {/if}

    <!-- Banned Validators List -->
    <div class="space-y-4">
      {#each paginatedValidators as validator}
        <div class="bg-white shadow rounded-lg p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-4 flex-1">
              <!-- Avatar -->
              <Avatar
                address={validator.address}
                name={validator.user?.name}
                size="md"
              />

              <!-- Validator Info -->
              <div class="flex-1">
                <div class="flex items-center space-x-3">
                  <div>
                    <!-- Name or Address -->
                    {#if validator.user?.name}
                      <h3 class="text-lg font-medium text-gray-900">
                        {validator.user.name}
                      </h3>
                      <p class="text-sm text-gray-500 font-mono">
                        {validator.address}
                      </p>
                    {:else}
                      <h3 class="text-lg font-medium text-gray-900 font-mono">
                        {validator.address}
                      </h3>
                      <p class="text-sm text-gray-500">
                        No profile
                      </p>
                    {/if}
                  </div>
                </div>

                <!-- Additional Info -->
                <div class="flex items-center space-x-4 mt-2">
                  <!-- Ban Timestamp if available -->
                  {#if validator.ban_timestamp}
                    <div class="text-sm text-gray-600">
                      Banned: {format(new Date(validator.ban_timestamp), 'MMM d, yyyy')}
                    </div>
                  {/if}

                  <!-- Points if available from user profile -->
                  {#if validator.user?.total_points !== undefined}
                    <div class="text-sm text-gray-600">
                      <span class="font-medium">{validator.user.total_points || 0}</span> points
                    </div>
                  {/if}

                  <!-- User ID if available -->
                  {#if validator.user?.id}
                    <div class="text-sm text-gray-600">
                      ID: {validator.user.id}
                    </div>
                  {/if}
                </div>
              </div>
            </div>

            <!-- Status Badge and Actions -->
            <div class="flex items-center space-x-3">
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                <svg class="mr-1 h-3 w-3 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                </svg>
                Banned
              </span>

              <!-- Unban button -->
              <button
                onclick={() => unbanValidator(validator.address)}
                disabled={unbanningValidators.has(validator.address)}
                class="px-3 py-1 text-xs font-medium text-green-600 bg-green-50 border border-green-200 rounded-md hover:bg-green-100 hover:text-green-700 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed"
                title="Unban this validator"
              >
                {#if unbanningValidators.has(validator.address)}
                  <svg class="animate-spin -ml-0.5 mr-1 h-3 w-3 text-gray-400 inline" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Unbanning...
                {:else}
                  Unban
                {/if}
              </button>
            </div>
          </div>

          <!-- Individual validator messages -->
          {#if unbanMessages[validator.address]}
            <div class="mt-3 rounded-md p-3 {unbanMessages[validator.address].type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}">
              <div class="flex">
                <div class="flex-shrink-0">
                  {#if unbanMessages[validator.address].type === 'success'}
                    <svg class="h-4 w-4 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                  {:else}
                    <svg class="h-4 w-4 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  {/if}
                </div>
                <div class="ml-2">
                  <p class="text-xs font-medium {unbanMessages[validator.address].type === 'success' ? 'text-green-800' : 'text-red-800'}">
                    {unbanMessages[validator.address].text}
                  </p>
                </div>
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <!-- Bottom Pagination -->
    {#if totalCount > pageSize}
      <div class="mt-6">
        <PaginationEnhanced
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 25, 50, 100]}
          showPageSize={false}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      </div>
    {/if}
  {/if}
</div>