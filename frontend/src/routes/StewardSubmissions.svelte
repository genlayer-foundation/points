<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI, contributionsAPI, leaderboardAPI } from '../lib/api.js';
  import { format } from 'date-fns';
  import PaginationEnhanced from '../components/PaginationEnhanced.svelte';
  import SubmissionCard from '../components/SubmissionCard.svelte';
  import { showSuccess, showError } from '../lib/toastStore';
  
  let submissions = $state([]);
  let contributionTypes = $state([]);
  let users = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = $state(10);
  
  // Filters
  let stateFilter = $state('pending');
  let typeFilter = $state('');
  let assignedToFilter = $state('');  // '' = all, 'me' = assigned to me, steward_id = specific steward
  let usernameSearch = $state('');
  let searchTimeout = null;
  let stewardsList = $state([]);
  let assigningSubmissions = $state(new Set());  // Track which submissions are being assigned

  // Review states
  let processingSubmissions = $state(new Set());
  let multipliers = $state({});
  let reviewData = $state({});
  
  onMount(async () => {
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }

    await loadContributionTypes();
    await loadUsers();
    await loadStewards();
    await loadSubmissions();
  });
  
  async function loadUsers() {
    try {
      const response = await stewardAPI.getUsers();
      users = response.data;
    } catch (err) {
      // Error loading users silently handled
    }
  }

  async function loadStewards() {
    try {
      const response = await stewardAPI.getStewards();
      // Response is array with: { id, user_id, name, address, user_details }
      stewardsList = response.data;
    } catch (err) {
      // Error loading stewards silently handled
    }
  }

  async function handleAssignment(submissionId, stewardId) {
    assigningSubmissions.add(submissionId);
    assigningSubmissions = new Set(assigningSubmissions);

    try {
      await stewardAPI.assignSubmission(submissionId, {
        steward_id: stewardId === 'unassigned' ? null : stewardId
      });
      showSuccess('Assignment updated successfully');

      // Reload submissions to get updated data
      await loadSubmissions();
    } catch (err) {
      showError('Failed to update assignment: ' + (err.response?.data?.error || err.message));
    } finally {
      assigningSubmissions.delete(submissionId);
      assigningSubmissions = new Set(assigningSubmissions);
    }
  }

  async function loadContributionTypes() {
    try {
      // Fetch all contribution types by setting a high page_size
      const response = await contributionsAPI.getContributionTypes({ page_size: 100 });
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
        // Default all to 1 if error
        contributionTypes.forEach(type => {
          multipliers[type.id] = 1;
        });
      }
    } catch (err) {
      // Error loading contribution types silently handled
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

      if (usernameSearch) {
        params.username_search = usernameSearch;
      }

      // Handle assigned_to filter
      if (assignedToFilter === 'unassigned') {
        params.assigned_to = 'unassigned';
      } else if (assignedToFilter) {
        params.assigned_to = assignedToFilter;
      }

      const response = await stewardAPI.getSubmissions(params);
      submissions = response.data.results || [];
      totalCount = response.data.count || 0;
      
      // If we got no results and we're not on page 1, it means this page doesn't exist anymore
      // Try going to the previous page
      if (submissions.length === 0 && currentPage > 1 && totalCount > 0) {
        currentPage = currentPage - 1;
        // Recursively call loadSubmissions with the new page
        return loadSubmissions();
      }
      
      // Initialize review data for each submission
      submissions.forEach(sub => {
        if (!reviewData[sub.id]) {
          reviewData[sub.id] = {
            action: 'accept',
            user: sub.user,
            contribution_type: sub.contribution_type,
            points: sub.suggested_points || sub.contribution_type_details?.min_points || 0,
            staff_reply: '',
            create_highlight: false,
            highlight_title: '',
            highlight_description: ''
          };
        }
      });
    } catch (err) {
      // If we get a 404 error and we're not on page 1, it might mean the page doesn't exist
      // Try going to the previous page
      if (err.response?.status === 404 && currentPage > 1) {
        currentPage = currentPage - 1;
        // Recursively call loadSubmissions with the new page
        return loadSubmissions();
      }
      
      // For other errors, show appropriate message
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
      showSuccess(getSuccessMessage(data.action));

      // Reload submissions
      await loadSubmissions();
    } catch (err) {
      showError('Failed to review submission: ' + (err.response?.data?.detail || err.message));
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
  
  function handlePageChange(event) {
    currentPage = event.detail;
    loadSubmissions();
  }
  
  function handlePageSizeChange(event) {
    pageSize = event.detail;
    currentPage = 1; // Reset to first page
    loadSubmissions();
  }
  
  function handleFilterChange() {
    currentPage = 1;
    loadSubmissions();
  }

  function handleSearchChange() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentPage = 1;
      loadSubmissions();
    }, 500);
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
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Status Filter -->
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

      <!-- Contribution Type Filter -->
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

      <!-- Assigned To Filter -->
      <div>
        <label for="assigned-filter" class="block text-sm font-medium text-gray-700 mb-1">
          Assigned To
        </label>
        <select
          id="assigned-filter"
          bind:value={assignedToFilter}
          onchange={handleFilterChange}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="">All</option>
          <option value="unassigned">Unassigned</option>
          {#each stewardsList as steward}
            <option value={steward.user_id}>
              {steward.name || steward.address?.slice(0, 10) + '...'}
            </option>
          {/each}
        </select>
      </div>

      <!-- Username Search -->
      <div>
        <label for="username-search" class="block text-sm font-medium text-gray-700 mb-1">
          Search User
        </label>
        <input
          id="username-search"
          type="text"
          bind:value={usernameSearch}
          oninput={handleSearchChange}
          placeholder="Name or address..."
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
    </div>

    <div class="mt-3 text-sm text-gray-600">
      Total: <span class="font-semibold text-gray-900">{totalCount}</span> submissions
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
    <!-- Top Pagination -->
    {#if totalCount > 10}
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
    
    <div class="space-y-4">
      {#each submissions as submission}
        <div class="relative">
          <!-- Assignment Dropdown - Only for pending/more_info_needed -->
          {#if submission.state === 'pending' || submission.state === 'more_info_needed'}
            <div class="absolute top-4 right-4 z-10">
              <select
                value={submission.assigned_to || 'unassigned'}
                onchange={(e) => handleAssignment(submission.id, e.target.value)}
                disabled={assigningSubmissions.has(submission.id)}
                class="px-3 py-1 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                title="Assign to steward"
              >
                <option value="unassigned">Unassigned</option>
                {#each stewardsList as steward}
                  <option value={steward.user_id}>
                    {steward.name || steward.address?.slice(0, 10) + '...'}
                  </option>
                {/each}
              </select>
            </div>
          {/if}

          <!-- Existing SubmissionCard -->
          <SubmissionCard
            {submission}
            showReviewForm={true}
            onReview={handleReview}
            reviewData={reviewData[submission.id]}
            isProcessing={processingSubmissions.has(submission.id)}
            successMessage={''}
            {contributionTypes}
            {users}
            {multipliers}
            isOwnSubmission={false}
          />
        </div>
      {/each}
    </div>
    
    <!-- Bottom Pagination -->
    {#if totalCount > 10}
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