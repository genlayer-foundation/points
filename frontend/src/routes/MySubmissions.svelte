<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  import Pagination from '../components/Pagination.svelte';
  
  let submissions = $state([]);
  let loading = $state(true);
  let error = $state('');
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = 20;
  let stateFilter = $state('');
  
  onMount(async () => {
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
  
  function getStateClass(state) {
    switch (state) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'accepted':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'more_info_needed':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }
  
  function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<div class="container mx-auto px-4 py-8">
  <div class="flex justify-between items-center mb-8">
    <h1 class="text-3xl font-bold">My Submissions</h1>
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
        <div class="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-semibold">{submission.contribution_type_name}</h3>
              <p class="text-sm text-gray-600">
                Contribution Date: {formatDate(submission.contribution_date)}
              </p>
              <p class="text-sm text-gray-600">
                Submitted: {formatDate(submission.created_at)}
              </p>
            </div>
            <span class="px-3 py-1 rounded-full text-sm font-medium {getStateClass(submission.state)}">
              {submission.state_display}
            </span>
          </div>
          
          {#if submission.notes}
            <div class="mb-4">
              <h4 class="font-medium text-sm text-gray-700 mb-1">Notes:</h4>
              <p class="text-gray-600">{submission.notes}</p>
            </div>
          {/if}
          
          {#if submission.staff_reply}
            <div class="mb-4 bg-gray-50 p-3 rounded">
              <h4 class="font-medium text-sm text-gray-700 mb-1">Staff Response:</h4>
              <p class="text-gray-600">{submission.staff_reply}</p>
            </div>
          {/if}
          
          {#if submission.evidence_items && submission.evidence_items.length > 0}
            <div class="mb-4">
              <h4 class="font-medium text-sm text-gray-700 mb-2">Evidence:</h4>
              <ul class="space-y-1">
                {#each submission.evidence_items as evidence}
                  <li class="text-sm text-gray-600">
                    {#if evidence.description}
                      • {evidence.description}
                    {/if}
                    {#if evidence.url}
                      <a href={evidence.url} target="_blank" class="text-primary-600 underline ml-1">
                        View URL
                      </a>
                    {/if}
                    {#if evidence.file_url}
                      <a href={evidence.file_url} target="_blank" class="text-primary-600 underline ml-1">
                        View File
                      </a>
                    {/if}
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
          
          <div class="flex justify-between items-center mt-4">
            <div class="text-sm text-gray-500">
              {#if submission.last_edited_at}
                Last edited: {formatDate(submission.last_edited_at)}
              {/if}
            </div>
            
            {#if submission.can_edit}
              <button
                onclick={() => push(`/contributions/${submission.id}`)}
                class="px-4 py-2 bg-primary-600 text-white text-sm rounded-md hover:bg-primary-700"
              >
                Edit & Resubmit
              </button>
            {/if}
          </div>
        </div>
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