<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';
  import Avatar from '../components/Avatar.svelte';
  
  // State management
  let highlights = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let selectedType = $state('all');
  let contributionTypes = $state([]);
  
  // Format date helper
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };
  
  // Fetch highlights
  async function fetchHighlights() {
    try {
      loading = true;
      error = null;

      const params = {};

      // Filter by current category
      if ($currentCategory && $currentCategory !== 'global') {
        params.category = $currentCategory;
      }

      const response = await contributionsAPI.getAllHighlights(params);
      highlights = response.data || [];
      
      // Extract unique contribution types from highlights
      const types = new Set();
      highlights.forEach(h => {
        if (h.contribution_type_name) {
          types.add(h.contribution_type_name);
        }
      });
      contributionTypes = Array.from(types).sort();
      
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load highlights';
      loading = false;
    }
  }
  
  // Filtered highlights based on selected type
  let filteredHighlights = $derived(
    selectedType === 'all' 
      ? highlights 
      : highlights.filter(h => h.contribution_type_name === selectedType)
  );
  
  onMount(() => {
    fetchHighlights();
  });

  // Re-fetch when category changes
  $effect(() => {
    if ($currentCategory) {
      fetchHighlights();
    }
  });
</script>

<div class="space-y-6 sm:space-y-8">
  <!-- Header -->
  <div class="flex justify-between items-center">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">Contributions > Highlights</h1>
      <p class="mt-1 text-sm text-gray-500">
        Exceptional contributions from our community members
      </p>
    </div>
  </div>
  
  <!-- Filter by Type -->
  {#if contributionTypes.length > 0}
    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-sm font-medium text-gray-700">Filter by type:</span>
      <button
        onclick={() => selectedType = 'all'}
        class="px-3 py-1 rounded-full text-sm font-medium transition-colors {selectedType === 'all' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}"
      >
        All ({highlights.length})
      </button>
      {#each contributionTypes as type}
        <button
          onclick={() => selectedType = type}
          class="px-3 py-1 rounded-full text-sm font-medium transition-colors {selectedType === type ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}"
        >
          {type} ({highlights.filter(h => h.contribution_type_name === type).length})
        </button>
      {/each}
    </div>
  {/if}
  
  <!-- Highlights Grid -->
  {#if loading}
    <div class="flex justify-center items-center p-12">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if filteredHighlights.length === 0}
    <div class="bg-gray-50 rounded-lg p-12 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
      </svg>
      <h3 class="mt-2 text-sm font-medium text-gray-900">No highlights found</h3>
      <p class="mt-1 text-sm text-gray-500">
        {selectedType === 'all' ? 'No highlighted contributions yet.' : `No highlights for ${selectedType}.`}
      </p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      {#each filteredHighlights as highlight}
        {@const hasEvidence = highlight.contribution_details?.evidence_items?.length > 0}
        {#snippet highlightCard()}
          <div class="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
            <div class="flex items-start justify-between mb-4">
              <div class="flex items-center gap-2">
                <svg class="w-5 h-5 text-yellow-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                </svg>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  {highlight.contribution_type_name}
                </span>
                {#if hasEvidence}
                  <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" title="{highlight.contribution_details.evidence_items.length} evidence item{highlight.contribution_details.evidence_items.length > 1 ? 's' : ''}">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                {/if}
              </div>
              <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                {highlight.contribution_points} pts
              </span>
            </div>

            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {highlight.title}
            </h3>

            <div class="markdown-content text-sm text-gray-600 mb-4">
              {@html parseMarkdown(highlight.description)}
            </div>

            {#if hasEvidence}
              <div class="mb-4 pt-3 border-t border-gray-200">
                <h5 class="text-xs font-medium text-gray-700 mb-1">Evidence</h5>
                <ul class="space-y-1">
                  {#each highlight.contribution_details.evidence_items as evidence}
                    <li class="text-xs text-gray-600">
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

            <div class="flex items-center justify-between text-sm">
              <div class="flex items-center gap-3">
                <Avatar
                  user={{
                    name: highlight.user_name,
                    address: highlight.user_address,
                    profile_image_url: highlight.user_profile_image_url,
                    validator: highlight.user_validator,
                    builder: highlight.user_builder,
                    steward: highlight.user_steward,
                    has_validator_waitlist: highlight.user_has_validator_waitlist,
                    has_builder_welcome: highlight.user_has_builder_welcome
                  }}
                  size="xs"
                  clickable={true}
                />
                <button
                  class="text-primary-600 hover:text-primary-700 font-medium"
                  onclick={() => push(`/participant/${highlight.user_address}`)}
                >
                  {highlight.user_name || `${highlight.user_address.slice(0, 6)}...${highlight.user_address.slice(-4)}`}
                </button>
                <span class="text-gray-400">•</span>
                <span class="text-gray-500">{formatDate(highlight.contribution_date)}</span>
              </div>

              <button
                onclick={() => push(`/contribution-type/${highlight.contribution_type_id}`)}
                class="text-xs text-gray-500 hover:text-gray-700"
              >
                View Type →
              </button>
            </div>
          </div>
        {/snippet}
        {@render highlightCard()}
      {/each}
    </div>
  {/if}
</div>