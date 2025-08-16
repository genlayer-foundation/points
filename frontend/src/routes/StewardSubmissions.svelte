<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI, contributionsAPI, leaderboardAPI } from '../lib/api.js';
  import { format } from 'date-fns';
  import Pagination from '../components/Pagination.svelte';
  
  let submissions = $state([]);
  let contributionTypes = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = 10;
  
  // Filters
  let stateFilter = $state('pending');
  let typeFilter = $state('');
  
  // Form states for each submission
  let submissionForms = $state({});
  let processingSubmissions = $state(new Set());
  let successMessages = $state({});
  let multipliers = $state({});
  
  onMount(async () => {
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }
    
    await loadContributionTypes();
    await loadSubmissions();
  });
  
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
      
      // Initialize forms for each submission
      submissions.forEach(sub => {
        if (!submissionForms[sub.id]) {
          submissionForms[sub.id] = {
            action: 'accept', // Default to accept action
            contribution_type: sub.contribution_type,
            points: sub.contribution_type_details?.min_points || 0,
            create_highlight: false,
            highlight_title: '',
            highlight_description: '',
            staff_reply: ''
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
  
  async function handleReview(submissionId, action) {
    const form = submissionForms[submissionId];
    form.action = action;
    
    // Validate based on action
    if (action === 'accept' && !form.points) {
      alert('Please enter points for acceptance');
      return;
    }
    
    if ((action === 'reject' || action === 'more_info') && !form.staff_reply) {
      alert(`Please provide a reason for ${action === 'reject' ? 'rejection' : 'requesting more information'}`);
      return;
    }
    
    processingSubmissions.add(submissionId);
    processingSubmissions = new Set(processingSubmissions);
    
    try {
      const reviewData = {
        action: action,
        staff_reply: form.staff_reply
      };
      
      if (action === 'accept') {
        reviewData.points = parseInt(form.points);
        reviewData.contribution_type = form.contribution_type;
        
        if (form.create_highlight) {
          reviewData.create_highlight = true;
          reviewData.highlight_title = form.highlight_title || `Outstanding ${getTypeName(form.contribution_type)}`;
          reviewData.highlight_description = form.highlight_description || 'Exceptional contribution to the ecosystem';
        }
      }
      
      await stewardAPI.reviewSubmission(submissionId, reviewData);
      
      // Show success message
      successMessages[submissionId] = getSuccessMessage(action);
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
  
  function getTypeName(typeId) {
    const type = contributionTypes.find(t => t.id === typeId);
    return type?.name || 'Contribution';
  }
  
  function getSuccessMessage(action) {
    switch(action) {
      case 'accept': return '✓ Submission accepted successfully';
      case 'reject': return 'Submission rejected';
      case 'more_info': return 'Information request sent';
      default: return 'Action completed';
    }
  }
  
  function adjustPoints(submissionId, delta) {
    const form = submissionForms[submissionId];
    const type = contributionTypes.find(t => t.id === form.contribution_type);
    if (!type) return;
    
    const currentPoints = form.points;
    const newPoints = currentPoints + delta;
    
    // Apply constraints based on point value
    let minAllowed = type.min_points;
    let maxAllowed = type.max_points;
    
    // If points > 10, allow +-5 range
    if (currentPoints > 10) {
      const stepSize = 5;
      form.points = Math.max(minAllowed, Math.min(maxAllowed, newPoints));
    } else {
      // Normal increment/decrement
      form.points = Math.max(minAllowed, Math.min(maxAllowed, newPoints));
    }
  }
  
  function getFinalPoints(submissionId) {
    const form = submissionForms[submissionId];
    if (!form) return 0;
    const multiplier = multipliers[form.contribution_type] || 1;
    return Math.round(form.points * multiplier);
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
    return format(new Date(dateString), 'MMM d, yyyy HH:mm');
  }
</script>

<div class="container mx-auto px-4 py-8">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-2xl font-bold">Review Submissions</h1>
      <p class="text-sm text-gray-600 mt-1">Review and manage user contribution submissions</p>
    </div>
    <button
      onclick={() => push('/stewards')}
      class="px-4 py-2 text-gray-700 hover:text-gray-900"
    >
      ← Back to Dashboard
    </button>
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
    <div class="space-y-6">
      {#each submissions as submission}
        <div class="bg-white shadow-lg rounded-lg overflow-hidden border-l-4 {submission.state === 'pending' ? 'border-l-yellow-400' : submission.state === 'accepted' ? 'border-l-green-400' : submission.state === 'rejected' ? 'border-l-red-400' : 'border-l-blue-400'}">
          <!-- Success Message -->
          {#if successMessages[submission.id]}
            <div class="bg-green-50 border-l-4 border-green-400 p-4 animate-fade-in">
              <div class="flex items-center">
                <svg class="w-5 h-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
                <p class="text-green-700 font-medium">{successMessages[submission.id]}</p>
              </div>
            </div>
          {/if}
          
          <!-- Header -->
          <div class="px-6 py-4 border-b {submission.state === 'pending' ? 'bg-yellow-50' : submission.state === 'accepted' ? 'bg-green-50' : submission.state === 'rejected' ? 'bg-red-50' : 'bg-blue-50'}">
            <div class="flex justify-between items-start">
              <div>
                <h3 class="text-lg font-semibold">
                  {submission.user_details?.name || submission.user_details?.address?.slice(0, 8) + '...'}
                </h3>
                <p class="text-sm text-gray-600">
                  Submitted {formatDate(submission.created_at)}
                </p>
              </div>
              <span class="px-3 py-1 rounded-full text-sm font-medium {getStateClass(submission.state)}">
                {submission.state_display}
              </span>
            </div>
          </div>
          
          <!-- Content -->
          <div class="px-6 py-4">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:items-center">
              <!-- Left Column - Submission Details -->
              <div class="space-y-4">
                <div>
                  <h4 class="text-sm font-medium text-gray-700">Contribution Type</h4>
                  <p class="mt-1 text-sm text-gray-900">
                    {submission.contribution_type_details?.name}
                    <span class="text-xs text-gray-500 ml-2">
                      ({submission.contribution_type_details?.min_points}-{submission.contribution_type_details?.max_points} points)
                    </span>
                  </p>
                </div>
                
                {#if submission.notes}
                  <div>
                    <h4 class="text-sm font-medium text-gray-700">Notes</h4>
                    <p class="mt-1 text-sm text-gray-900">{submission.notes}</p>
                  </div>
                {/if}
                
                {#if submission.evidence_items?.length > 0}
                  <div>
                    <h4 class="text-sm font-medium text-gray-700">Evidence</h4>
                    <ul class="mt-1 space-y-1">
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
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}
              </div>
              
              <!-- Right Column - Action Forms -->
              <div>
                {#if submission.state === 'pending' || submission.state === 'more_info_needed'}
                  <div class="border {submissionForms[submission.id].action === 'accept' ? 'border-green-200' : submissionForms[submission.id].action === 'reject' ? 'border-red-200' : 'border-blue-200'} rounded-lg overflow-hidden">
                    <!-- Action Toggle Buttons -->
                    <div class="flex">
                      <button
                        type="button"
                        onclick={() => submissionForms[submission.id].action = 'accept'}
                        class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {submissionForms[submission.id].action === 'accept' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-700 hover:bg-green-100'} border-r border-gray-200"
                      >
                        Accept
                      </button>
                      <button
                        type="button"
                        onclick={() => submissionForms[submission.id].action = 'reject'}
                        class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {submissionForms[submission.id].action === 'reject' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-700 hover:bg-red-100'} border-r border-gray-200"
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        onclick={() => submissionForms[submission.id].action = 'more_info'}
                        class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {submissionForms[submission.id].action === 'more_info' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}"
                      >
                        Request Info
                      </button>
                    </div>
                    
                    <!-- Dynamic Form Content -->
                    {#if submissionForms[submission.id].action === 'accept'}
                      <div class="p-4 bg-green-50">
                      <div class="space-y-3">
                        <div>
                          <label class="block text-sm font-medium text-gray-700">
                            Contribution Type
                          </label>
                          <select
                            bind:value={submissionForms[submission.id].contribution_type}
                            class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
                          >
                            {#each contributionTypes as type}
                              <option value={type.id}>
                                {type.name} {multipliers[type.id] && multipliers[type.id] !== 1 ? `(×${multipliers[type.id]})` : ''}
                              </option>
                            {/each}
                          </select>
                        </div>
                        
                        <div class="grid grid-cols-2 gap-4">
                          <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">
                              Points
                            </label>
                            <div class="inline-flex items-center">
                              <button
                                onclick={() => adjustPoints(submission.id, submissionForms[submission.id].points > 10 ? -5 : -1)}
                                class="w-7 h-8 flex items-center justify-center bg-white hover:bg-gray-50 rounded-l-lg text-gray-600 hover:text-gray-800 font-bold transition-colors border border-r-0 border-gray-300"
                                type="button"
                              >
                                −
                              </button>
                              <input
                                type="number"
                                bind:value={submissionForms[submission.id].points}
                                min={contributionTypes.find(t => t.id === submissionForms[submission.id].contribution_type)?.min_points || 0}
                                max={contributionTypes.find(t => t.id === submissionForms[submission.id].contribution_type)?.max_points || 100}
                                class="w-12 h-8 px-1 border-y border-gray-300 text-sm text-center font-semibold bg-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent focus:z-10 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                              />
                              <button
                                onclick={() => adjustPoints(submission.id, submissionForms[submission.id].points > 10 ? 5 : 1)}
                                class="w-7 h-8 flex items-center justify-center bg-white hover:bg-gray-50 rounded-r-lg text-gray-600 hover:text-gray-800 font-bold transition-colors border border-l-0 border-gray-300"
                                type="button"
                              >
                                +
                              </button>
                            </div>
                            <p class="text-xs text-gray-500 mt-1">
                              Range: {contributionTypes.find(t => t.id === submissionForms[submission.id].contribution_type)?.min_points || 0}-{contributionTypes.find(t => t.id === submissionForms[submission.id].contribution_type)?.max_points || 100}
                            </p>
                          </div>
                          
                          <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">
                              Final Points
                            </label>
                            <div class="text-2xl font-bold text-green-700">
                              {getFinalPoints(submission.id)}
                            </div>
                            <p class="text-xs text-gray-500 mt-1">
                              ×{multipliers[submissionForms[submission.id].contribution_type] || 1} multiplier
                            </p>
                          </div>
                        </div>
                        
                        <!-- Feature Highlight Card -->
                        <div class="border border-yellow-300 rounded-lg overflow-hidden">
                          <button
                            type="button"
                            onclick={() => submissionForms[submission.id].create_highlight = !submissionForms[submission.id].create_highlight}
                            class="w-full bg-yellow-100 hover:bg-yellow-200 px-4 py-2.5 flex items-center justify-between transition-colors"
                          >
                            <span class="flex items-center gap-2 text-sm font-medium text-yellow-900">
                              <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                              </svg>
                              Feature this contribution
                            </span>
                            <svg 
                              class="w-4 h-4 text-yellow-700 transition-transform duration-200 {submissionForms[submission.id].create_highlight ? 'rotate-180' : ''}" 
                              fill="none" 
                              stroke="currentColor" 
                              viewBox="0 0 24 24"
                            >
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                          </button>
                          
                          {#if submissionForms[submission.id].create_highlight}
                            <div class="bg-yellow-50 border-t border-yellow-200 p-3 space-y-2">
                              <div>
                                <label class="block text-xs font-medium text-yellow-800 mb-1">
                                  Highlight Title
                                </label>
                                <input
                                  type="text"
                                  bind:value={submissionForms[submission.id].highlight_title}
                                  placeholder="e.g., Outstanding Technical Achievement"
                                  class="w-full px-3 py-2 border border-yellow-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
                                />
                              </div>
                              <div>
                                <label class="block text-xs font-medium text-yellow-800 mb-1">
                                  Why is this noteworthy?
                                </label>
                                <textarea
                                  bind:value={submissionForms[submission.id].highlight_description}
                                  placeholder="Describe what makes this contribution exceptional..."
                                  rows="2"
                                  class="w-full px-3 py-2 border border-yellow-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
                                ></textarea>
                              </div>
                            </div>
                          {/if}
                        </div>
                        
                        <button
                          onclick={() => handleReview(submission.id, 'accept')}
                          disabled={processingSubmissions.has(submission.id)}
                          class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                        >
                          {processingSubmissions.has(submission.id) ? 'Processing...' : 'Accept & Create Contribution'}
                        </button>
                      </div>
                    </div>
                  {:else if submissionForms[submission.id].action === 'reject'}
                      <div class="p-4 bg-red-50">
                        <div class="space-y-3">
                        <div>
                          <label class="block text-sm font-medium text-gray-700 mb-1">
                            Rejection Reason
                          </label>
                          <textarea
                            bind:value={submissionForms[submission.id].staff_reply}
                            placeholder="Please provide a reason for rejection..."
                            rows="4"
                            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
                          ></textarea>
                        </div>
                        
                        <button
                          onclick={() => handleReview(submission.id, 'reject')}
                          disabled={processingSubmissions.has(submission.id)}
                          class="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                        >
                          {processingSubmissions.has(submission.id) ? 'Processing...' : 'Reject Submission'}
                        </button>
                      </div>
                    </div>
                  {:else if submissionForms[submission.id].action === 'more_info'}
                      <div class="p-4 bg-blue-50">
                        <div class="space-y-3">
                        <div>
                          <label class="block text-sm font-medium text-gray-700 mb-1">
                            Information Needed
                          </label>
                          <textarea
                            bind:value={submissionForms[submission.id].staff_reply}
                            placeholder="What additional information do you need from the submitter?"
                            rows="4"
                            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
                          ></textarea>
                        </div>
                        
                        <button
                          onclick={() => handleReview(submission.id, 'more_info')}
                          disabled={processingSubmissions.has(submission.id)}
                          class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                        >
                          {processingSubmissions.has(submission.id) ? 'Processing...' : 'Request Information'}
                        </button>
                      </div>
                    </div>
                  {:else}
                      <div class="p-8 bg-gray-50 text-center">
                        <p class="text-gray-500">Select an action above to review this submission</p>
                      </div>
                    {/if}
                  </div>
                {:else}
                  <div class="flex justify-center">
                    <!-- Show contribution details if accepted -->
                    {#if submission.state === 'accepted' && submission.contribution}
                      <!-- Contribution Card using validator dashboard style -->
                      <div class="bg-white shadow rounded-lg p-4 hover:shadow-lg transition-shadow border-2 border-green-400 inline-block">
                        <div class="flex items-start justify-between gap-4">
                          <div class="min-w-0">
                            <div class="flex items-center gap-2 mb-2">
                              <div class="w-4 h-4 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
                                <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 6v12m6-6H6"></path>
                                </svg>
                              </div>
                              <h3 class="text-base font-semibold text-gray-900 flex items-center gap-2">
                                <button
                                  class="hover:text-primary-600 transition-colors"
                                  onclick={() => push(`/contribution-type/${submission.contribution.contribution_type_details?.id}`)}
                                >
                                  {submission.contribution.contribution_type_details?.name || 'Contribution'}
                                </button>
                                {#if submission.contribution.is_highlighted}
                                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                    <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                                    </svg>
                                    Featured
                                  </span>
                                {/if}
                              </h3>
                            </div>
                            
                            <div class="flex items-center gap-3 text-xs">
                              <button 
                                class="text-primary-600 hover:text-primary-700 font-medium"
                                onclick={() => push(`/participant/${submission.user_details?.address || ''}`)}
                              >
                                {submission.user_details?.name || `${submission.user_details?.address?.slice(0, 6)}...${submission.user_details?.address?.slice(-4)}` || 'Anonymous'}
                              </button>
                              <span class="text-gray-400">•</span>
                              <span class="text-gray-500">
                                {formatDate(submission.contribution.contribution_date)}
                              </span>
                            </div>
                          </div>
                          
                          <div class="ml-3 flex-shrink-0">
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                              {submission.contribution.points} pts
                            </span>
                          </div>
                        </div>
                        
                        {#if submission.contribution.highlight}
                          <div class="mt-3 pt-3 border-t border-gray-200">
                            <div class="bg-yellow-50 rounded-md p-3">
                              <h6 class="text-sm font-medium text-yellow-900 mb-1">
                                {submission.contribution.highlight.title}
                              </h6>
                              {#if submission.contribution.highlight.description}
                                <p class="text-sm text-yellow-800">
                                  {submission.contribution.highlight.description}
                                </p>
                              {/if}
                            </div>
                          </div>
                        {/if}
                      </div>
                    {/if}
                    
                    <!-- Show rejection reason if rejected -->
                    {#if submission.state === 'rejected' && submission.staff_reply}
                      <div class="border border-red-200 rounded-lg p-4 bg-red-50 inline-block">
                        <h4 class="text-sm font-medium text-red-900 mb-2">Rejection Reason</h4>
                        <p class="text-sm text-red-700">{submission.staff_reply}</p>
                      </div>
                    {/if}
                    
                    <!-- Show info request if more info needed -->
                    {#if submission.state === 'more_info_needed' && submission.staff_reply}
                      <div class="border border-blue-200 rounded-lg p-4 bg-blue-50 inline-block">
                        <h4 class="text-sm font-medium text-blue-900 mb-2">Information Requested</h4>
                        <p class="text-sm text-blue-700">{submission.staff_reply}</p>
                      </div>
                    {/if}
                  </div>
                {/if}
              </div>
            </div>
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