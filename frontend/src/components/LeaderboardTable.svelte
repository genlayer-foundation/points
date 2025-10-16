<script>
  import { push } from 'svelte-spa-router';
  import Avatar from './Avatar.svelte';

  let {
    entries = [],
    loading = false,
    error = null,
    showHeader = true,
    title = 'Leaderboard',
    subtitle = 'Top contributors ranked by points',
    compact = false,
    hideAddress = false
  } = $props();

  // Helper for rank styling
  function getRankClass(rank) {
    if (rank === 1) return 'bg-amber-100 text-amber-800';
    if (rank === 2) return 'bg-gray-100 text-gray-800';
    if (rank === 3) return 'bg-amber-50 text-amber-700';
    return 'bg-gray-50 text-gray-600';
  }
</script>

{#if loading}
  <div class="flex justify-center items-center p-8">
    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
  </div>
{:else if error}
  <div class="p-6 text-center text-red-500">
    Failed to load leaderboard: {error}
  </div>
{:else if entries.length === 0}
  <div class="bg-gray-50 rounded-lg p-6 text-center">
    <p class="text-gray-500">No entries found on the leaderboard yet.</p>
  </div>
{:else}
  <div class="bg-white shadow overflow-hidden rounded-lg">
    {#if showHeader}
      <div class="px-4 py-5 sm:px-6">
        <h3 class="text-lg leading-6 font-medium text-gray-900">
          {title}
        </h3>
        <p class="mt-1 max-w-2xl text-sm text-gray-500">
          {subtitle}
        </p>
      </div>
    {/if}
    
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rank
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Participant
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Points
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#each entries as entry, i}
            <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              <td class="px-6 py-4 whitespace-nowrap">
                <span class={`inline-flex items-center justify-center h-8 w-8 rounded-full ${getRankClass(entry.rank)}`}>
                  {entry.rank}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  {#if !compact}
                    <div class="flex-shrink-0 mr-3">
                      <Avatar 
                        user={entry.user_details}
                        size="sm"
                        clickable={true}
                      />
                    </div>
                  {/if}
                  <div>
                    <button
                      onclick={() => push(`/participant/${entry.user_details?.address || ''}`)}
                      class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors"
                    >
                      {entry.user_details?.name || 'N/A'}
                    </button>
                    {#if !hideAddress}
                      <div class="text-sm text-gray-500">
                        {entry.user_details?.address || ''}
                      </div>
                    {/if}
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 font-medium">{entry.total_points}</div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
{/if}