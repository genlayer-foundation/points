<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import ContributionsList from './ContributionsList.svelte';
  import { contributionsAPI } from '../lib/api';

  let {
    title = 'Recent Contributions',
    limit = 5,
    contributionTypeId = null,
    userId = null,
    showViewAll = true,
    viewAllPath = '/contributions',
    viewAllText = 'View All →',
    className = ''
  } = $props();

  let contributions = $state([]);
  let loading = $state(true);
  let error = $state(null);

  onMount(async () => {
    try {
      loading = true;
      
      // Build query parameters
      const params = {
        limit,
        ordering: '-created_at'
      };
      
      if (contributionTypeId) {
        params.contribution_type = contributionTypeId;
      }
      
      if (userId) {
        params.user = userId;
      }
      
      const response = await contributionsAPI.getContributions(params);
      contributions = response.data.results || [];
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load recent contributions';
      loading = false;
    }
  });
</script>

<div class="space-y-4 {className}">
  <div class="flex justify-between items-center">
    <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
    {#if showViewAll}
      <button
        onclick={() => push(viewAllPath)}
        class="text-sm text-primary-600 hover:text-primary-700 font-medium"
      >
        {viewAllText}
      </button>
    {/if}
  </div>
  
  <ContributionsList
    {contributions}
    {loading}
    {error}
    showUser={!userId}
  />
</div>