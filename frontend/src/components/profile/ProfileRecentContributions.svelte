<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../../lib/api.js';
  import PortalContributionCard from '../portal/PortalContributionCard.svelte';
  import { m } from '../../lib/paraglide/messages.js';

  let {
    userId = null,
    category = null,
    limit = 5,
    showViewAll = true,
    viewAllPath = '/contributions',
    viewAllText = m.prc_view_all_contributions(),
  } = $props();

  let contributions = $state([]);
  let loading = $state(true);
  let error = $state(null);
  const hiddenContributionTypeSlugs = new Set(['builder-welcome']);

  function contributionTypeSlug(contribution) {
    return contribution?.contribution_type_details?.slug || contribution?.contribution_type?.slug || '';
  }

  async function fetchContributions() {
    try {
      loading = true;
      const params = {
        limit: limit + hiddenContributionTypeSlugs.size,
        ordering: '-created_at',
      };
      if (userId) params.user_address = userId;
      if (category) params.category = category;
      const response = await contributionsAPI.getContributions(params);
      contributions = (response.data.results || [])
        .filter((contribution) => !hiddenContributionTypeSlugs.has(contributionTypeSlug(contribution)))
        .slice(0, limit);
    } catch (err) {
      error = err.message || m.prc_failed_load();
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
      <span class="text-[14px] text-[#999]">{m.phigh_no_contributions_yet()}</span>
      <span class="text-[14px] text-[#999]">{m.phigh_submit_first()}</span>
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
