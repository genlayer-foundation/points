<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  import Pagination from '../components/Pagination.svelte';
  import SubmissionCard from '../components/SubmissionCard.svelte';
  
  let submissions = $state([]);
  let loading = $state(true);
  let error = $state('');
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = 20;
  let stateFilter = $state('');
  let successMessage = $state('');
  
  onMount(async () => {
    // Check for success message from edit submission
    const updateSuccess = sessionStorage.getItem('submissionUpdateSuccess');
    if (updateSuccess) {
      successMessage = updateSuccess;
      sessionStorage.removeItem('submissionUpdateSuccess');
      // Clear the message after 5 seconds
      setTimeout(() => {
        successMessage = '';
      }, 5000);
    }
    
    // Wait a moment for auth state to be verified
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Check authentication
    if (!$authState.isAuthenticated) {
      console.log('Not authenticated, redirecting to home');
      console.log('Auth state:', $authState);
      push('/');
      return;
    }
    
    console.log('Authenticated as:', $authState.address);
    loadSubmissions();
  });
  
  async function loadSubmissions() {
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
    }
  }
  
  function handlePageChange(newPage) {
    currentPage = newPage;
    loadSubmissions();
  }
  
  function handleFilterChange() {
    currentPage = 1;
    loadSubmissions();
  }
</script>

<div class="container mx-auto px-4 py-8">
  {#if successMessage}
    <div class="mb-6 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded flex items-center justify-between">
      <div class="flex items-center">
        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
        </svg>
        <span>{successMessage}</span>
      </div>
      <button onclick={() => successMessage = ''} class="text-green-700 hover:text-green-900">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
  {/if}
  
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
  
  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
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
    <div class="space-y-4">
      {#each submissions as submission}
        <SubmissionCard 
          {submission}
          isOwnSubmission={true}
        />
      {/each}
    </div>
    
    {#if totalCount > pageSize}
      <div class="mt-8">
        <Pagination
          currentPage={currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          onPageChange={handlePageChange}
        />
      </div>
    {/if}
  {/if}
</div>