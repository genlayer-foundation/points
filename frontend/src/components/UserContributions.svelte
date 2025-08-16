<script>
  import ContributionsList from './ContributionsList.svelte';

  let {
    userAddress,
    userName = 'Participant',
    title = null,
    showTitle = true,
    className = '',
    category = null,
    compact = false,
    limit = null
  } = $props();

  // Derive the title if not provided
  let displayTitle = $derived(title || `${userName}'s Contributions`);
</script>

{#if showTitle}
  <div class={className}>
    <h2 class="text-xl font-semibold text-gray-900 mb-4">{displayTitle}</h2>
    <ContributionsList
      {userAddress}
      showUser={false}
      {category}
      {compact}
      {limit}
    />
  </div>
{:else}
  <div class={className}>
    <ContributionsList
      {userAddress}
      showUser={false}
      {category}
      {compact}
      {limit}
    />
  </div>
{/if}