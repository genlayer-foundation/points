<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../../lib/api.js';
  import { visibleContributions } from '../../lib/hiddenContributions.js';
  import PortalContributionCard from '../portal/PortalContributionCard.svelte';

  let {
    userId = null,
    category = null,
    limit = 5,
    showViewAll = true,
    viewAllPath = '/contributions',
    viewAllText = 'View All Contributions →',
  } = $props();

  let contributions = $state([]);
  let loading = $state(true);
  let error = $state(null);

  async function fetchContributions() {
    try {
      loading = true;
      const params = {
        limit: limit + 2,
        ordering: '-created_at',
        exclude_onboarding: 'true',
      };
      if (userId) params.user_address = userId;
      if (category) params.category = category;
      const response = await contributionsAPI.getContributions(params);
      contributions = visibleContributions(response.data.results || []).slice(0, limit);
    } catch (err) {
      error = err.message || 'Failed to load contributions';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchContributions();
  });
</script>

<div>
  {#if loading}
    <div class="flex gap-2.5 overflow-x-auto pb-2">
      {#each [1, 2, 3] as _}
        <div class="flex-shrink-0 w-[300px] h-[180px] rounded-[8px] bg-gray-100 animate-pulse"></div>
      {/each}
    </div>
  {:else if contributions.length === 0}
    <div class="w-full rounded-[12px] bg-white border border-[#e5e5e5] py-6 px-4 flex flex-col items-center justify-center gap-1">
      <span class="text-[14px] text-[#999]">No contributions yet.</span>
      <span class="text-[14px] text-[#999]">Submit your first to start earning points.</span>
    </div>
  {:else}
    <div class="flex gap-2.5 overflow-x-auto pb-2" style="-ms-overflow-style: none; scrollbar-width: none;">
      {#each contributions as contrib (contrib.id)}
        <div class="flex-shrink-0 w-[300px]">
          <PortalContributionCard contribution={contrib} {category} />
        </div>
      {/each}
    </div>

    {#if showViewAll}
      <div class="mt-3 flex justify-end">
        <button
          onclick={() => push(viewAllPath)}
          class="text-sm text-[#999] hover:text-black transition-colors"
        >
          {viewAllText}
        </button>
      </div>
    {/if}
  {/if}
</div>
