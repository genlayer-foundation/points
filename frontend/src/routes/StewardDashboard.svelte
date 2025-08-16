<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI } from '../lib/api.js';
  import { format, formatDistanceToNow } from 'date-fns';
  
  let stats = $state({
    pending_count: 0,
    total_reviewed: 0,
    last_review: null,
    acceptance_rate: 0,
    total_accepted: 0,
    total_rejected: 0,
    total_info_requested: 0
  });
  
  let loading = $state(true);
  let error = $state(null);
  
  onMount(async () => {
    // Check if user is authenticated and is a steward
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }
    
    await loadStats();
  });
  
  async function loadStats() {
    try {
      loading = true;
      error = null;
      const response = await stewardAPI.getStats();
      stats = response.data;
    } catch (err) {
      console.error('Error loading steward stats:', err);
      error = 'Failed to load dashboard statistics';
      // Check if it's a permission error
      if (err.response?.status === 403) {
        error = 'You do not have permission to access steward tools';
      }
    } finally {
      loading = false;
    }
  }
  
  function formatDate(dateString) {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      return formatDistanceToNow(date, { addSuffix: true });
    } catch (e) {
      return dateString;
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <div class="mb-6">
    <h1 class="text-2xl font-bold text-gray-900">Steward Dashboard</h1>
    <p class="mt-1 text-sm text-gray-500">
      Review and manage contribution submissions
    </p>
  </div>
  
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border-l-4 border-red-400 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-700">{error}</p>
        </div>
      </div>
    </div>
  {:else}
    <!-- Statistics Cards -->
    <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
      <div class="px-4 py-5 sm:px-6">
        <h3 class="text-lg leading-6 font-medium text-gray-900">
          Review Statistics
        </h3>
      </div>
      <div class="border-t border-gray-200">
        <dl>
          <!-- Pending Submissions -->
          <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
            <dt class="text-sm font-medium text-gray-500">
              Pending Submissions
            </dt>
            <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
              <span class="text-2xl font-bold text-yellow-600">{stats.pending_count}</span>
              {#if stats.pending_count > 0}
                <span class="ml-2 text-sm text-gray-500">awaiting review</span>
              {/if}
            </dd>
          </div>
          
          <!-- Last Review -->
          <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
            <dt class="text-sm font-medium text-gray-500">
              Last Review
            </dt>
            <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
              {formatDate(stats.last_review)}
            </dd>
          </div>
          
          <!-- Total Reviewed -->
          <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
            <dt class="text-sm font-medium text-gray-500">
              Total Reviewed
            </dt>
            <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
              <span class="font-semibold">{stats.total_reviewed}</span> submissions
            </dd>
          </div>
          
          <!-- Acceptance Rate -->
          <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
            <dt class="text-sm font-medium text-gray-500">
              Acceptance Rate
            </dt>
            <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
              <div class="flex items-center">
                <span class="text-lg font-semibold">{stats.acceptance_rate}%</span>
                <div class="ml-4 flex-1 max-w-xs">
                  <div class="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      class="bg-green-600 h-2 rounded-full" 
                      style="width: {stats.acceptance_rate}%"
                    ></div>
                  </div>
                </div>
              </div>
            </dd>
          </div>
          
          <!-- Breakdown -->
          <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
            <dt class="text-sm font-medium text-gray-500">
              Review Breakdown
            </dt>
            <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
              <div class="flex space-x-6">
                <div class="flex items-center">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Accepted
                  </span>
                  <span class="ml-2 font-semibold">{stats.total_accepted}</span>
                </div>
                <div class="flex items-center">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    Rejected
                  </span>
                  <span class="ml-2 font-semibold">{stats.total_rejected}</span>
                </div>
                <div class="flex items-center">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Info Requested
                  </span>
                  <span class="ml-2 font-semibold">{stats.total_info_requested}</span>
                </div>
              </div>
            </dd>
          </div>
        </dl>
      </div>
    </div>
    
    <!-- Action Button -->
    <div class="flex justify-center">
      <button
        onclick={() => push('/stewards/submissions')}
        class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
      >
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path>
        </svg>
        Review Submissions
        {#if stats.pending_count > 0}
          <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            {stats.pending_count}
          </span>
        {/if}
      </button>
    </div>
  {/if}
</div>