<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI, contributionsAPI, leaderboardAPI } from '../lib/api.js';
  import { format } from 'date-fns';
  import Pagination from '../components/Pagination.svelte';
  import SubmissionCard from '../components/SubmissionCard.svelte';
  
  let submissions = $state([]);
  let contributionTypes = $state([]);
  let users = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = 10;
  
  // Filters
  let stateFilter = $state('pending');
  let typeFilter = $state('');
  
  // Review states
  let processingSubmissions = $state(new Set());
  let successMessages = $state({});
  let multipliers = $state({});
  let reviewData = $state({});
  
  onMount(async () => {
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }
    
    await loadContributionTypes();
    await loadUsers();
    await loadSubmissions();
  });
  
  async function loadUsers() {
    try {
      const response = await stewardAPI.getUsers();
      users = response.data;
    } catch (err) {
      console.error('Error loading users:', err);
    }
  }
  
  async function loadContributionTypes() {
    try {
      const response = await contributionsAPI.getContributionTypes();
      contributionTypes = response.data.results || response.data;
      
      // Load active multipliers
      try {
        const multipliersRes = await leaderboardAPI.getActiveMultipliers();
        const activeMultipliers = multipliersRes.data;
        
        // Build multipliers map
        contributionTypes.forEach(type => {
          const multiplier = activeMultipliers.find(m => m.contribution_type === type.id);
          multipliers[type.id] = multiplier ? multiplier.multiplier_value : 1;
        });
      } catch (err) {
        console.error('Error loading multipliers:', err);
        // Default all to 1 if error
        contributionTypes.forEach(type => {
          multipliers[type.id] = 1;
        });
      }
    } catch (err) {
      console.error('Error loading contribution types:', err);
    }
  }
  
  async function loadSubmissions() {
    loading = true;
    error = null;
    
    try {
      const params = {
        page: currentPage,
        page_size: pageSize
      };
      
      if (stateFilter) {
        params.state = stateFilter;
      }
      
      if (typeFilter) {
        params.contribution_type = typeFilter;
      }
      
      const response = await stewardAPI.getSubmissions(params);
      submissions = response.data.results || [];
      totalCount = response.data.count || 0;
      
      // Initialize review data for each submission
      submissions.forEach(sub => {
        if (!reviewData[sub.id]) {
          reviewData[sub.id] = {
            action: 'accept',
            user: sub.user,
            contribution_type: sub.contribution_type,
            points: sub.contribution_type_details?.min_points || 0,
            staff_reply: '',
            create_highlight: false,
            highlight_title: '',
            highlight_description: ''
          };
        }
      });
    } catch (err) {
      console.error('Error loading submissions:', err);
      error = err.response?.status === 403 
        ? 'You do not have permission to access steward tools'
        : 'Failed to load submissions';
    } finally {
      loading = false;
    }
  }
  
  async function handleReview(submissionId, data) {
    processingSubmissions.add(submissionId);
    processingSubmissions = new Set(processingSubmissions);
    
    try {
      const apiData = {
        action: data.action,
        staff_reply: data.staff_reply
      };
      
      if (data.action === 'accept') {
        apiData.points = parseInt(data.points);
        apiData.contribution_type = data.contribution_type;
        apiData.user = parseInt(data.user);
        
        if (data.create_highlight) {
          apiData.create_highlight = true;
          apiData.highlight_title = data.highlight_title;
          apiData.highlight_description = data.highlight_description;
        }
      }
      
      await stewardAPI.reviewSubmission(submissionId, apiData);
      
      // Show success message
      successMessages[submissionId] = getSuccessMessage(data.action);
      successMessages = { ...successMessages };
      
      // Clear after 3 seconds
      setTimeout(() => {
        delete successMessages[submissionId];
        successMessages = { ...successMessages };
      }, 3000);
      
      // Reload submissions
      await loadSubmissions();
    } catch (err) {
      console.error('Error reviewing submission:', err);
      alert('Failed to review submission: ' + (err.response?.data?.detail || err.message));
    } finally {
      processingSubmissions.delete(submissionId);
      processingSubmissions = new Set(processingSubmissions);
    }
  }
  
  function getSuccessMessage(action) {
    switch(action) {
      case 'accept': return '✓ Submission accepted successfully';
      case 'reject': return 'Submission rejected';
      case 'more_info': return 'Information request sent';
      default: return 'Action completed';
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
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-2xl font-bold">Review Submissions</h1>
      <p class="text-sm text-gray-600 mt-1">Review and manage user contribution submissions</p>
    </div>
  </div>
  
  <!-- Filters -->
  <div class="bg-white shadow rounded-lg p-4 mb-6">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div>
        <label for="state-filter" class="block text-sm font-medium text-gray-700 mb-1">
          Status
        </label>
        <select
          id="state-filter"
          bind:value={stateFilter}
          onchange={handleFilterChange}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All</option>
          <option value="pending">Pending Review</option>
          <option value="accepted">Accepted</option>
          <option value="rejected">Rejected</option>
          <option value="more_info_needed">More Info Needed</option>
        </select>
      </div>
      
      <div>
        <label for="type-filter" class="block text-sm font-medium text-gray-700 mb-1">
          Contribution Type
        </label>
        <select
          id="type-filter"
          bind:value={typeFilter}
          onchange={handleFilterChange}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All Types</option>
          {#each contributionTypes as type}
            <option value={type.id}>{type.name}</option>
          {/each}
        </select>
      </div>
      
      <div class="flex items-end">
        <div class="text-sm text-gray-500">
          Showing {submissions.length} of {totalCount} submissions
        </div>
      </div>
    </div>
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
    <div class="text-center py-12 bg-white rounded-lg shadow">
      <p class="text-gray-600">No submissions found matching your filters.</p>
    </div>
  {:else}
    <div class="space-y-4">
      {#each submissions as submission}
        <SubmissionCard 
          {submission}
          showReviewForm={true}
          onReview={handleReview}
          reviewData={reviewData[submission.id]}
          isProcessing={processingSubmissions.has(submission.id)}
          successMessage={successMessages[submission.id] || ''}
          {contributionTypes}
          {users}
          {multipliers}
          isOwnSubmission={false}
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