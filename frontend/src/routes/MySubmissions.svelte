<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  import PaginationEnhanced from '../components/PaginationEnhanced.svelte';
  import SubmissionCard from '../components/SubmissionCard.svelte';
  import { showSuccess } from '../lib/toastStore';

  let submissions = $state([]);
  let loading = $state(true);
  let error = $state('');
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = $state(20);
  let stateFilter = $state('');
  let authChecked = $state(false);
  
  // Load submissions when authenticated
  async function loadSubmissions() {
    if (!$authState.isAuthenticated) {
      loading = false;
      authChecked = true;
      return;
    }
    
    loading = true;
    error = '';
    
    try {
      const params = {
        page: currentPage,
        page_size: pageSize
      };
      
      if (stateFilter) {
        params.state = stateFilter;
      }
      
      console.log('Making API request to /submissions/my/ with params:', params);
      const response = await api.get('/submissions/my/', { params });
      console.log('Response received:', response);
      submissions = response.data.results || response.data;
      totalCount = response.data.count || submissions.length;
    } catch (err) {
      error = 'Failed to load submissions';
      console.error(err);
    } finally {
      loading = false;
      authChecked = true;
    }
  }
  
  // React to auth state changes
  $effect(() => {
    if ($authState.isAuthenticated) {
      loadSubmissions();
    } else {
      submissions = [];
      authChecked = true;
      loading = false;
    }
  });
  
  onMount(async () => {
    // Check for success message from edit submission
    const updateSuccess = sessionStorage.getItem('submissionUpdateSuccess');
    if (updateSuccess) {
      showSuccess(updateSuccess);
      sessionStorage.removeItem('submissionUpdateSuccess');
    }

    // Wait a moment for auth state to be verified
    await new Promise(resolve => setTimeout(resolve, 100));
    loadSubmissions();
  });
  
  function handlePageChange(event) {
    currentPage = event.detail;
    loadSubmissions();
  }
  
  function handlePageSizeChange(event) {
    pageSize = event.detail;
    currentPage = 1;
    loadSubmissions();
  }
  
  function handleFilterChange() {
    currentPage = 1;
    loadSubmissions();
  }
</script>

<div class="container mx-auto px-4 py-8">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-2xl font-bold">My Submissions</h1>
    <button
      onclick={() => push('/submit-contribution')}
      class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
    >
      Submit New Contribution
    </button>
  </div>
  
  <div class="mb-6">
    <label for="state-filter" class="block text-sm font-medium text-gray-700 mb-2">
      Filter by status:
    </label>
    <select
      id="state-filter"
      bind:value={stateFilter}
      onchange={handleFilterChange}
      class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
    >
      <option value="">All</option>
      <option value="pending">Pending Review</option>
      <option value="accepted">Accepted</option>
      <option value="rejected">Rejected</option>
      <option value="more_info_needed">More Info Needed</option>
    </select>
  </div>
  
  {#if !authChecked || loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if !$authState.isAuthenticated}
    <div class="bg-white shadow rounded-lg p-8">
      <div class="text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Authentication Required</h3>
        <p class="text-gray-500 mb-4">Please connect your wallet to view your submissions.</p>
        <button
          onclick={() => push('/')}
          class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  {:else if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if submissions.length === 0}
    <div class="text-center py-12">
      <p class="text-gray-600 mb-4">You haven't submitted any contributions yet.</p>
      <button
        onclick={() => push('/submit-contribution')}
        class="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
      >
        Submit Your First Contribution
      </button>
    </div>
  {:else}
    <!-- Top Pagination -->
    {#if totalCount > 10}
      <div class="mb-4">
        <PaginationEnhanced
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 20, 50, 100]}
          showPageSize={true}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      </div>
    {/if}
    
    <div class="space-y-4">
      {#each submissions as submission}
        <SubmissionCard
          {submission}
          isOwnSubmission={true}
        />
      {/each}
    </div>
    
    <!-- Bottom Pagination -->
    {#if totalCount > 10}
      <div class="mt-6">
        <PaginationEnhanced
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 20, 50, 100]}
          showPageSize={false}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      </div>
    {/if}
  {/if}
</div>