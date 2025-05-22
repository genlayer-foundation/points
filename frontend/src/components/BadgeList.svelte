<script>
  import Badge from './Badge.svelte';
  
  export let badges = [];
  export let loading = false;
  export let error = null;
  export let title = 'Badges';
  export let description = 'Recent badges and achievements';
  export let emptyMessage = 'No badges found.';
</script>

<div class="bg-white shadow overflow-hidden rounded-lg">
  <div class="px-4 py-5 sm:px-6">
    <h3 class="text-lg leading-6 font-medium text-gray-900">
      {title}
    </h3>
    <p class="mt-1 max-w-2xl text-sm text-gray-500">
      {description}
    </p>
  </div>
  
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="p-6 text-center text-red-500">
      Failed to load badges: {error}
    </div>
  {:else if badges.length === 0}
    <div class="p-6 text-center text-gray-500">
      {emptyMessage}
    </div>
  {:else}
    <div class="border-t border-gray-200 p-4">
      <div class="flex flex-wrap gap-2">
        {#each badges as badge}
          <Badge {badge} />
        {/each}
      </div>
    </div>
  {/if}
</div>