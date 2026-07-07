<script>
  import Pagination from './Pagination.svelte';
  import ContributionCard from './ContributionCard.svelte';
  import { contributionsAPI } from '../lib/api';
  import { m } from '../lib/paraglide/messages.js';

  const {
    contributions = [],
    loading: externalLoading = false,
    error: externalError = null,
    showUser = true,
    userAddress = null,
    category = null,
    compact = false,
    limit: maxLimit = null,
  } = $props();

  let page = $state(1);
  let limit = $state(maxLimit || (compact ? 5 : 10));
  let totalCount = $state(0);
  let localContributions = $state(contributions || []);
  let localLoading = $state(externalLoading);
  let localError = $state(externalError);

  // Normalize each contribution into the shape ContributionCard expects.
  // No grouping — every contribution is its own card.
  let processedContributions = $derived(
    (localContributions || []).map(contrib => ({
      ...contrib,
      typeId: typeof contrib.contribution_type === 'object'
        ? contrib.contribution_type.id
        : contrib.contribution_type,
      users: contrib.user_details ? [contrib.user_details] : [],
      category: category || contrib.contribution_type_details?.category,
    }))
  );

  $effect(() => { localContributions = contributions || []; });
  $effect(() => { localLoading = externalLoading; });
  $effect(() => { localError = externalError; });

  $effect(() => {
    if (userAddress) fetchContributions();
  });

  async function fetchContributions() {
    if (!userAddress) return;
    try {
      localLoading = true;
      localError = null;
      const params = { page, limit, user_address: userAddress };
      if (category) params.category = category;
      const res = await contributionsAPI.getContributions(params);
      totalCount = res.data.count || 0;
      localContributions = res.data.results || [];
    } catch (err) {
      localError = err.message || m.clist_failed_load_generic();
    } finally {
      localLoading = false;
    }
  }

  function handlePageChange(event) {
    page = event.detail;
  }
</script>

<div>
  {#if localLoading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if localError}
    <div class="p-6 text-center text-red-500">
      {m.clist_failed_load({ error: localError })}
    </div>
  {:else if localContributions.length === 0}
    <div class="p-6 text-center text-gray-500">
      {m.clist_no_contributions()}
    </div>
  {:else}
    <div class="space-y-3">
      {#each processedContributions as contribution (contribution.id)}
        <ContributionCard
          {contribution}
          {showUser}
          submission={{
            notes: contribution.notes,
            evidence_items: contribution.evidence_items
          }}
          showExpand={contribution.evidence_items?.length > 0 || !!contribution.notes}
        />
      {/each}
    </div>

    {#if userAddress}
      <div class="mt-4">
        <Pagination
          page={page}
          limit={limit}
          totalCount={totalCount}
          on:pageChange={handlePageChange}
        />
      </div>
    {/if}
  {/if}
</div>
