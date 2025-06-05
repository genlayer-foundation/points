<script>
  import { push } from 'svelte-spa-router';
  
  export let entries = [];
  export let loading = false;
  export let error = null;
  
  // Helper for rank styling
  function getRankClass(rank) {
    if (rank === 1) return 'bg-amber-100 text-amber-800';
    if (rank === 2) return 'bg-gray-100 text-gray-800';
    if (rank === 3) return 'bg-amber-50 text-amber-700';
    return 'bg-gray-50 text-gray-600';
  }
</script>

<div class="bg-white shadow overflow-hidden rounded-lg">
  <div class="px-4 py-5 sm:px-6">
    <h3 class="text-lg leading-6 font-medium text-gray-900">
      Leaderboard
    </h3>
    <p class="mt-1 max-w-2xl text-sm text-gray-500">
      Top contributors ranked by points
    </p>
  </div>
  
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="p-6 text-center text-red-500">
      Failed to load leaderboard: {error}
    </div>
  {:else if entries.length === 0}
    <div class="p-6 text-center text-gray-500">
      No entries found on the leaderboard yet.
    </div>
  {:else}
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
            <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
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
                  <div class="flex-shrink-0 h-10 w-10">
                    <div class="h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center text-gray-500">
                      {entry.user_details?.name ? entry.user_details.name.charAt(0).toUpperCase() : '#'}
                    </div>
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-medium text-gray-900">
                      {entry.user_details?.name || 'N/A'}
                    </div>
                    <div class="text-sm text-gray-500">
                      {entry.user_details?.address || ''}
                    </div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 font-medium">{entry.total_points}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <a href={`/participant/${entry.user_details?.address || ''}`} onclick={(e) => { e.preventDefault(); push(`/participant/${entry.user_details?.address || ''}`); }} class="text-primary-600 hover:text-primary-900">View Profile</a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>