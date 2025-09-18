<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI } from '../lib/api.js';
  import { unbanValidator as blockchainUnbanValidator, unbanAllValidators as blockchainUnbanAllValidators } from '../lib/blockchain.js';
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

  // Modal state
  let showModal = $state(false);
  let modalData = $state({ type: '', address: '', validator: null });
  let modalLoading = $state(false);
  let transactionState = $state(''); // 'confirming', 'pending', 'confirmed', 'failed'
  let transactionHash = $state('');

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

  // Show confirmation modal for individual unban
  function showUnbanModal(address) {
    const validator = bannedValidators.find(v => v.address === address);
    modalData = {
      type: 'single',
      address,
      validator
    };
    showModal = true;
    transactionState = '';
    transactionHash = '';
  }

  // Show confirmation modal for unban all
  function showUnbanAllModal() {
    modalData = {
      type: 'all',
      address: '',
      validator: null
    };
    showModal = true;
    transactionState = '';
    transactionHash = '';
  }

  // Close modal
  function closeModal() {
    showModal = false;
    modalData = { type: '', address: '', validator: null };
    modalLoading = false;
    transactionState = '';
    transactionHash = '';
  }

  // Execute the unban operation with wallet signing
  async function executeUnban() {
    modalLoading = true;
    transactionState = 'confirming';

    try {
      let result;

      if (modalData.type === 'single') {
        transactionState = 'confirming';
        result = await blockchainUnbanValidator(modalData.address);
      } else if (modalData.type === 'all') {
        transactionState = 'confirming';
        result = await blockchainUnbanAllValidators();
      }

      if (result?.success) {
        transactionState = 'confirmed';
        transactionHash = result.transaction_hash;

        // Show success message
        const messageKey = modalData.type === 'single' ? modalData.address : 'all';
        unbanMessages[messageKey] = {
          type: 'success',
          text: result.message || 'Transaction successful'
        };

        // Reload the banned validators list after a short delay to allow blockchain to update
        setTimeout(async () => {
          await loadBannedValidators();
        }, 3000);

        // Close modal after a delay to show success
        setTimeout(() => {
          closeModal();
        }, 5000);
      } else {
        transactionState = 'failed';

        // Show error message
        const messageKey = modalData.type === 'single' ? modalData.address : 'all';
        unbanMessages[messageKey] = {
          type: 'error',
          text: result?.error || 'Transaction failed'
        };

        modalLoading = false;
      }

      // Clear message after 5 seconds
      setTimeout(() => {
        const messageKey = modalData.type === 'single' ? modalData.address : 'all';
        delete unbanMessages[messageKey];
        unbanMessages = { ...unbanMessages };
      }, 5000);

    } catch (error) {
      console.error('Error executing unban:', error);
      transactionState = 'failed';
      modalLoading = false;

      let errorMessage = 'Failed to process transaction';
      if (error.code === 4001 || error.message?.includes('rejected')) {
        errorMessage = 'Transaction was rejected by user';
      } else if (error.message) {
        errorMessage = error.message;
      }

      // Show error message
      const messageKey = modalData.type === 'single' ? modalData.address : 'all';
      unbanMessages[messageKey] = {
        type: 'error',
        text: errorMessage
      };

      // Clear message after 5 seconds
      setTimeout(() => {
        delete unbanMessages[messageKey];
        unbanMessages = { ...unbanMessages };
      }, 5000);
    }
  }

  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }

</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold text-gray-900 mb-6">Manage Users</h1>

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
    <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-8">
      <div class="px-4 py-5 sm:px-6 flex justify-between items-center">
        <div>
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            Banned Validators ({totalCount})
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            Manage validators that have been banned from the network
          </p>
        </div>
        {#if totalCount > 0}
          <button
            onclick={showUnbanAllModal}
            disabled={unbanningValidators.has('all')}
            class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {#if unbanningValidators.has('all')}
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
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

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Address
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Ban Date
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each paginatedValidators as validator, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <!-- Status Column -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    <svg class="mr-1 h-3 w-3 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                    </svg>
                    Banned
                  </span>
                </td>

                <!-- Address Column -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <a
                      href={`/participant/${validator.address}`}
                      onclick={(e) => { e.preventDefault(); push(`/participant/${validator.address}`); }}
                      class="text-primary-600 hover:text-primary-800 font-mono"
                    >
                      {truncateAddress(validator.address)}
                    </a>
                    <a
                      href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${validator.address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-gray-400 hover:text-gray-600"
                      title="View in Explorer"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                      </svg>
                    </a>
                  </div>
                </td>

                <!-- Name Column -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    {#if validator.user}
                      <Avatar
                        address={validator.address}
                        name={validator.user.name}
                        size="sm"
                      />
                      <span class="text-gray-900">{validator.user.name || 'Unnamed'}</span>
                    {:else}
                      <span class="text-gray-400">—</span>
                    {/if}
                  </div>
                </td>

                <!-- Ban Date Column -->
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {#if validator.ban_timestamp}
                    {format(new Date(validator.ban_timestamp), 'MMM d, yyyy')}
                  {:else}
                    <span class="text-gray-400">—</span>
                  {/if}
                </td>

                <!-- Action Column -->
                <td class="px-6 py-4 whitespace-nowrap">
                  <button
                    onclick={() => showUnbanModal(validator.address)}
                    disabled={unbanningValidators.has(validator.address)}
                    class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {#if unbanningValidators.has(validator.address)}
                      <svg class="animate-spin -ml-1 mr-1 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Unbanning...
                    {:else}
                      Unban
                    {/if}
                  </button>
                </td>
              </tr>

              <!-- Individual validator messages row -->
              {#if unbanMessages[validator.address]}
                <tr class="bg-gray-50">
                  <td colspan="5" class="px-6 py-3">
                    <div class="rounded-md p-3 {unbanMessages[validator.address].type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}">
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
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
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

<!-- Confirmation Modal -->
{#if showModal}
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
      <div class="mt-3">
        <!-- Modal Header -->
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-medium text-gray-900">
            {#if modalData.type === 'single'}
              Confirm Unban Validator
            {:else}
              Confirm Unban All Validators
            {/if}
          </h3>
          <button
            onclick={closeModal}
            class="text-gray-400 hover:text-gray-600"
          >
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Modal Content -->
        <div class="mb-6">
          {#if modalData.type === 'single'}
            <p class="text-sm text-gray-700 mb-2">
              Are you sure you want to unban this validator?
            </p>
            <div class="bg-gray-50 p-3 rounded-md">
              <div class="flex items-center space-x-3">
                <Avatar
                  address={modalData.address}
                  name={modalData.validator?.user?.name}
                  size="sm"
                />
                <div class="flex-1">
                  {#if modalData.validator?.user?.name}
                    <p class="font-medium text-gray-900">{modalData.validator.user.name}</p>
                    <div class="flex items-center space-x-2">
                      <p class="text-sm text-gray-500 font-mono" title={modalData.address}>
                        {truncateAddress(modalData.address)}
                      </p>
                      <a
                        href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${modalData.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-gray-400 hover:text-blue-600 transition-colors"
                        title="View in Explorer"
                      >
                        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </div>
                  {:else}
                    <div class="flex items-center space-x-2">
                      <p class="font-medium text-gray-900 font-mono" title={modalData.address}>
                        {truncateAddress(modalData.address)}
                      </p>
                      <a
                        href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${modalData.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-gray-400 hover:text-blue-600 transition-colors"
                        title="View in Explorer"
                      >
                        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          {:else}
            <p class="text-sm text-gray-700 mb-2">
              Are you sure you want to unban <strong>ALL {bannedValidators.length} validators</strong>?
            </p>
            <div class="bg-red-50 border border-red-200 rounded-md p-3">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-red-800">
                    This action cannot be undone.
                  </p>
                </div>
              </div>
            </div>
          {/if}
        </div>

        <!-- Transaction Status -->
        {#if transactionState}
          <div class="mb-6">
            <div class="bg-blue-50 border border-blue-200 rounded-md p-4">
              <div class="flex items-center">
                <div class="flex-shrink-0">
                  {#if transactionState === 'confirming'}
                    <svg class="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  {:else if transactionState === 'confirmed'}
                    <svg class="h-5 w-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                  {:else if transactionState === 'failed'}
                    <svg class="h-5 w-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  {/if}
                </div>
                <div class="ml-3">
                  <p class="text-sm font-medium text-gray-800">
                    {#if transactionState === 'confirming'}
                      Please confirm the transaction in your wallet...
                    {:else if transactionState === 'confirmed'}
                      Transaction confirmed!
                    {:else if transactionState === 'failed'}
                      Transaction failed
                    {/if}
                  </p>
                  {#if transactionHash}
                    <p class="text-xs text-gray-600 mt-1 font-mono">
                      TX: {transactionHash}
                    </p>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        {:else}
          <!-- Transaction Instructions -->
          <div class="mb-6">
            <div class="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-yellow-800">
                    You'll be prompted to sign this transaction using your connected wallet. Ensure you have sufficient gas fees to complete the transaction.
                  </p>
                </div>
              </div>
            </div>
          </div>
        {/if}

        <!-- Modal Actions -->
        <div class="flex justify-end space-x-3">
          <button
            onclick={closeModal}
            disabled={modalLoading}
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {#if transactionState === 'confirmed'}
              Close
            {:else}
              Cancel
            {/if}
          </button>
          {#if transactionState !== 'confirmed'}
            <button
              onclick={executeUnban}
              disabled={modalLoading}
              class="px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {#if modalLoading}
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {#if transactionState === 'confirming'}
                  Awaiting Wallet...
                {:else}
                  Processing...
                {/if}
              {:else}
                {#if modalData.type === 'single'}
                  Sign & Unban Validator
                {:else}
                  Sign & Unban All Validators
                {/if}
              {/if}
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}