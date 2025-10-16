<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import ContributionsList from './ContributionsList.svelte';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';

  let {
    title = 'Recent Contributions',
    limit = 5,
    contributionTypeId = null,
    userId = null,
    category = null,
    showHeader = true,
    showViewAll = true,
    viewAllPath = '/contributions',
    viewAllText = 'View All →',
    className = ''
  } = $props();

  let contributions = $state([]);
  let loading = $state(true);
  let error = $state(null);

  // Determine effective category to use (explicit prop or global store)
  let effectiveCategory = $derived(category !== null ? category : $currentCategory);

  async function fetchContributions() {
    try {
      loading = true;

      // Build query parameters
      const params = {
        limit,
        ordering: '-created_at',
        // Don't group if filtering by specific contribution type
        group_consecutive: !contributionTypeId
      };

      if (contributionTypeId) {
        params.contribution_type = contributionTypeId;
      }

      if (userId) {
        params.user_address = userId;
      }

      // Add category filter if not global
      if (effectiveCategory !== 'global') {
        params.category = effectiveCategory;
      }

      const response = await contributionsAPI.getContributions(params);
      contributions = response.data.results || [];
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load recent contributions';
      loading = false;
    }
  }
  
  // Fetch contributions when category changes (including initial mount)
  // If explicit category prop is provided, only fetch once; otherwise react to global category changes
  let previousCategory = $state(null);

  $effect(() => {
    // If explicit category is provided, fetch once on mount
    if (category !== null) {
      if (previousCategory === null) {
        previousCategory = category;
        fetchContributions();
      }
    } else {
      // Otherwise, react to global category changes
      if ($currentCategory && $currentCategory !== previousCategory) {
        previousCategory = $currentCategory;
        fetchContributions();
      }
    }
  });
</script>

<div class="{showHeader ? 'space-y-4' : ''} {className}">
  {#if showHeader}
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
      {#if showViewAll}
        <button
          onclick={() => push(viewAllPath)}
          class="text-sm text-gray-600 hover:text-gray-900 font-medium"
        >
          {viewAllText}
        </button>
      {/if}
    </div>
  {/if}
  
  <ContributionsList
    {contributions}
    {loading}
    {error}
    showUser={!userId}
    category={effectiveCategory}
    disableGrouping={!!contributionTypeId}
  />
</div>