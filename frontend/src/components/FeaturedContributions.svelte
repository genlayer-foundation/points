<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { contributionsAPI, usersAPI } from '../lib/api';

  let {
    title = 'Featured Contributions',
    subtitle = 'Notable achievements and contributions',
    limit = 3,
    userId = null,
    contributionTypeId = null,
    showViewAll = true,
    viewAllPath = '/highlights',
    viewAllText = 'View All →',
    showHeader = true,
    cardStyle = 'default', // 'default', 'compact', 'highlight'
    className = ''
  } = $props();

  let highlights = $state([]);
  let loading = $state(true);
  let error = $state(null);

  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };

  onMount(async () => {
    try {
      loading = true;
      let response;
      
      if (userId) {
        // Fetch user-specific highlights
        response = await usersAPI.getUserHighlights(userId, { limit });
      } else if (contributionTypeId) {
        // Fetch contribution type specific highlights
        response = await contributionsAPI.getContributionTypeHighlights(contributionTypeId);
      } else {
        // Fetch all highlights
        response = await contributionsAPI.getAllHighlights();
      }
      
      highlights = response.data || [];
      if (limit && highlights.length > limit) {
        highlights = highlights.slice(0, limit);
      }
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load featured contributions';
      loading = false;
    }
  });
</script>

<div class={className}>
  {#if showHeader}
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
        {#if subtitle}
          <p class="mt-1 text-sm text-gray-500">{subtitle}</p>
        {/if}
      </div>
      {#if showViewAll && highlights.length > 0}
        <button
          onclick={() => push(viewAllPath)}
          class="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          {viewAllText}
        </button>
      {/if}
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      <p>{error}</p>
    </div>
  {:else if highlights.length === 0}
    <div class="bg-gray-50 rounded-lg p-6 text-center">
      <p class="text-gray-500">No featured contributions yet.</p>
    </div>
  {:else if cardStyle === 'default'}
    <!-- Default card style (used in Dashboard) -->
    <div class="space-y-3">
      {#each highlights as highlight}
        <div class="bg-white shadow rounded-lg p-4 hover:shadow-lg transition-shadow">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <svg class="w-4 h-4 text-yellow-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                </svg>
                <h3 class="text-base font-semibold text-gray-900 truncate">{highlight.title}</h3>
              </div>
              <p class="text-sm text-gray-600 mb-2 line-clamp-2">{highlight.description}</p>
              <div class="flex items-center gap-3 text-xs">
                <button 
                  class="text-primary-600 hover:text-primary-700 font-medium"
                  onclick={() => push(`/participant/${highlight.user_address}`)}
                >
                  {highlight.user_name || `${highlight.user_address.slice(0, 6)}...${highlight.user_address.slice(-4)}`}
                </button>
                <span class="text-gray-400">•</span>
                <span class="text-gray-500">{formatDate(highlight.contribution_date)}</span>
              </div>
            </div>
            <div class="ml-3 flex-shrink-0">
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                {highlight.contribution_points} pts
              </span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {:else if cardStyle === 'compact'}
    <!-- Compact style (used in ContributionTypeDetail) -->
    {#if highlights.length > 0}
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex items-center mb-4">
          <svg class="w-5 h-5 text-yellow-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
        </div>
        <div class="space-y-3">
          {#each highlights as highlight}
          <div class="border-l-4 border-yellow-400 pl-4 py-2">
          <h3 class="font-semibold text-gray-900">{highlight.title}</h3>
          <p class="text-sm text-gray-600 mt-1">{highlight.description}</p>
          <div class="flex items-center gap-3 mt-2 text-xs text-gray-500">
            <button 
              class="hover:text-purple-600"
              onclick={() => push(`/participant/${highlight.user_address}`)}
            >
              {highlight.user_name || `${highlight.user_address.slice(0, 6)}...${highlight.user_address.slice(-4)}`}
            </button>
            <span>•</span>
            <span>{formatDate(highlight.contribution_date)}</span>
            <span>•</span>
            <span class="font-semibold text-purple-600">{highlight.contribution_points} pts</span>
          </div>
        </div>
          {/each}
        </div>
      </div>
    {/if}
  {:else if cardStyle === 'highlight'}
    <!-- Highlight style (used in ParticipantProfile) -->
    <div class="space-y-4">
      {#each highlights as highlight}
        <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <h4 class="text-lg font-semibold text-gray-900">{highlight.title}</h4>
              <p class="mt-2 text-sm text-gray-700">{highlight.description}</p>
              <div class="mt-3 flex items-center gap-4 text-xs text-gray-600">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                  {highlight.contribution_type_name || 'Contribution'}
                </span>
                <span>{highlight.contribution_points} points</span>
                <span>{formatDate(highlight.contribution_date)}</span>
              </div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>