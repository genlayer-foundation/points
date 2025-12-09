<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI, usersAPI, leaderboardAPI } from '../lib/api.js';
  import { format, formatDistanceToNow } from 'date-fns';
  import { categoryTheme } from '../stores/category.js';
  import Avatar from '../components/Avatar.svelte';
  
  let stats = $state({
    pending_count: 0,
    total_reviewed: 0,
    last_review: null,
    acceptance_rate: 0,
    total_accepted: 0,
    total_rejected: 0,
    total_info_requested: 0
  });
  
  let stewards = $state([]);
  let stewardCategory = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let stewardsLoading = $state(true);
  let isSteward = $derived($userStore.user?.steward ? true : false);
  
  onMount(async () => {
    // Load both stats and stewards for everyone
    await Promise.all([
      loadStats(),
      loadStewards()
    ]);
  });
  
  async function loadStats() {
    try {
      loading = true;
      error = null;
      const response = await stewardAPI.getStats();
      stats = response.data;
    } catch (err) {
      error = 'Failed to load dashboard statistics';
      // Check if it's a permission error
      if (err.response?.status === 403) {
        error = 'You do not have permission to access steward tools';
      }
    } finally {
      loading = false;
    }
  }
  
  async function loadStewards() {
    try {
      stewardsLoading = true;
      
      // Get list of stewards directly
      const stewardsRes = await stewardAPI.getStewards();
      
      // Ensure stewards is always an array
      stewards = stewardsRes.data || [];
    } catch (err) {
      // Keep stewards as empty array on error
      stewards = [];
    } finally {
      stewardsLoading = false;
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

<div class="container mx-auto px-4 py-8 min-h-screen {$categoryTheme.bg}" style="margin: -2rem -1rem; padding: 2rem 3rem;">
  <!-- Header -->
  <h1 class="text-2xl font-bold text-gray-900 mb-6">Steward Dashboard</h1>
  
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {:else if error && isSteward}
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
    <div class="space-y-6">
      <!-- Submission Statistics Cards - Show for everyone -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 {$categoryTheme.badge.split(' ')[0]} rounded-lg">
              <svg class="w-4 h-4 {$categoryTheme.text}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Contribution Submissions</h2>
          </div>
          {#if isSteward}
            <button
              onclick={() => push('/stewards/submissions')}
              class="text-sm text-gray-500 hover:{$categoryTheme.text} transition-colors"
            >
              Manage submissions
              <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
              </svg>
            </button>
          {/if}
        </div>
        
        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- Pending Submissions -->
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center">
              <div class="flex-shrink-0 p-3 rounded-lg mr-4 bg-yellow-50 text-yellow-500">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div class="flex-1 flex items-end justify-between">
                <div>
                  <p class="text-sm text-gray-500">Pending Review</p>
                  <p class="text-2xl font-bold text-gray-900">{stats.pending_count}</p>
                </div>
                {#if stats.pending_count > 0 && isSteward}
                  <button
                    onclick={() => push('/stewards/submissions')}
                    class="text-xs {$categoryTheme.text} hover:text-green-700 font-medium pb-1"
                  >
                    Review Now →
                  </button>
                {/if}
              </div>
            </div>
          </div>
          
          <!-- Total Reviewed -->
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center">
              <div class="flex-shrink-0 p-3 rounded-lg mr-4 bg-green-50 text-green-500">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div>
                <p class="text-sm text-gray-500">Total Reviewed</p>
                <p class="text-2xl font-bold text-gray-900">{stats.total_reviewed}</p>
              </div>
            </div>
          </div>
          
          <!-- Acceptance Rate -->
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center mb-3">
              <div class="flex-shrink-0 p-3 rounded-lg mr-4 bg-blue-50 text-blue-500">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                </svg>
              </div>
              <div>
                <p class="text-sm text-gray-500">Acceptance Rate</p>
                <p class="text-2xl font-bold text-gray-900">{stats.acceptance_rate}%</p>
              </div>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-1.5">
              <div class="bg-green-600 h-1.5 rounded-full" style="width: {stats.acceptance_rate}%"></div>
            </div>
          </div>
          
          <!-- Last Review -->
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center">
              <div class="flex-shrink-0 p-3 rounded-lg mr-4 bg-purple-50 text-purple-500">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div>
                <p class="text-sm text-gray-500">Last Review</p>
                <p class="text-xl font-semibold text-gray-900">{formatDate(stats.last_review)}</p>
              </div>
            </div>
          </div>
        </div>
        
      </div>
      
      <div class="space-y-6">
        <!-- Active Stewards -->
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="p-1.5 {$categoryTheme.bgSecondary} rounded-lg">
                <svg class="w-4 h-4 {$categoryTheme.text}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
              </div>
              <h2 class="text-lg font-semibold text-gray-900">Active Stewards</h2>
            </div>
          </div>
          
          {#if stewardsLoading}
            <div class="bg-white rounded-lg shadow-sm border {$categoryTheme.border} p-8">
              <div class="flex justify-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              </div>
            </div>
          {:else if stewards.length === 0}
            <div class="bg-white rounded-lg shadow-sm border {$categoryTheme.border} p-6">
              <div class="text-center text-gray-500">
                <svg class="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
                <p>No active stewards found</p>
              </div>
            </div>
          {:else}
            <div class="bg-white rounded-lg shadow-sm border {$categoryTheme.border} divide-y divide-gray-200">
              {#each stewards as steward, index}
                <div class="p-4 hover:bg-gray-50 transition-colors">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                      <Avatar 
                        user={steward}
                        size="sm"
                        clickable={true}
                      />
                      <div class="min-w-0">
                        <button
                          onclick={() => push(`/participant/${steward.address}`)}
                          class="text-sm font-medium text-gray-900 hover:{$categoryTheme.text} transition-colors truncate"
                        >
                          {steward.name || `${steward.address.slice(0, 6)}...${steward.address.slice(-4)}`}
                        </button>
                        <div class="text-xs text-gray-500">
                          Steward since {format(new Date(steward.created_at), 'MMM yyyy')}
                        </div>
                      </div>
                    </div>
                    <button
                      onclick={() => push(`/participant/${steward.address}`)}
                      class="text-xs {$categoryTheme.text} hover:text-green-700 font-medium"
                    >
                      View →
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
      </div>
      
      <!-- Working Groups Section -->
      <div class="space-y-4">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-gray-100 rounded-lg">
              <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Working Groups</h2>
          </div>
          
          <div class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            <div class="bg-teal-500 p-4">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="inline-flex items-center gap-2 px-3 py-1 bg-white/20 text-white rounded-full text-sm font-medium">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Coming Soon
                  </div>
                </div>
                <div class="flex -space-x-2">
                  <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white text-xs font-bold">👥</div>
                  <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white text-xs font-bold">🔧</div>
                  <div class="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-white text-xs font-bold">📊</div>
                </div>
              </div>
            </div>
            <div class="p-6">
              <p class="text-gray-700 mb-4">
                Join specialized teams focused on different aspects of the GenLayer ecosystem. 
                Collaborate on technical proposals, standards, and implementations.
              </p>
              <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <p class="text-sm text-gray-600 mb-2">💡 <strong>Interested in joining?</strong></p>
                <p class="text-sm text-gray-600">
                  Contact <span class="font-mono bg-teal-100 px-1.5 py-0.5 rounded text-teal-700 font-semibold">@ras</span> on <a href="https://discord.com/invite/qjCU4AWnKE" target="_blank" rel="noopener noreferrer" class="text-teal-600 hover:text-teal-700 underline font-semibold">Discord</a> to learn more about upcoming working groups.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>