<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Avatar from '../components/Avatar.svelte';
  import Icon from '../components/Icons.svelte';
  import { leaderboardAPI } from '../lib/api';

  // State management
  let supporters = $state([]);
  let loading = $state(true);
  let error = $state(null);

  // Fetch supporters data
  async function fetchSupporters() {
    try {
      loading = true;
      error = null;

      const response = await leaderboardAPI.getSupporters();
      const data = response.data;

      supporters = data.top_supporters || [];
      loading = false;
    } catch (err) {
      console.error('Error fetching supporters:', err);
      error = err.message || 'Failed to load supporters';
      loading = false;
    }
  }

  onMount(() => {
    fetchSupporters();
  });

  function getRankClass(rank) {
    if (rank === 1) return 'bg-amber-100 text-amber-800';
    if (rank === 2) return 'bg-gray-100 text-gray-800';
    if (rank === 3) return 'bg-amber-50 text-amber-700';
    return 'bg-gray-50 text-gray-600';
  }
</script>

<div class="space-y-6 sm:space-y-8">
      <!-- Main Title -->
      <h1 class="text-2xl font-bold text-gray-900">Supporters</h1>

      <!-- Top Supporters Section -->
      <div class="space-y-4">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-purple-100 rounded-lg">
            <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Top Supporters</h2>
        </div>

      {#if loading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if error}
        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{error}</p>
        </div>
      {:else if supporters.length === 0}
        <div class="bg-white shadow overflow-hidden rounded-lg p-12 text-center">
          <div class="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-gray-900 mb-2">No Supporters Yet</h3>
          <p class="text-gray-600">Be the first to earn referral points by inviting people to the GenLayer ecosystem!</p>
        </div>
      {:else}
        <div class="bg-white shadow overflow-hidden rounded-lg">
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
                  <th scope="col" class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Referral Points
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each supporters as supporter, i}
                  <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class={`inline-flex items-center justify-center h-8 w-8 rounded-full ${getRankClass(i + 1)}`}>
                        {i + 1}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div class="flex-shrink-0 mr-3">
                          <Avatar
                            user={supporter}
                            size="sm"
                            clickable={true}
                          />
                        </div>
                        <button
                          onclick={() => push(`/participant/${supporter.address}`)}
                          class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors"
                        >
                          {supporter.name || `${supporter.address.slice(0, 6)}...${supporter.address.slice(-4)}`}
                        </button>
                      </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center justify-center gap-2">
                        <span class="text-lg font-bold text-gray-900">{supporter.total_points}</span>
                        <div class="flex items-center gap-2">
                          <div class="flex items-center text-xs text-orange-600" title="Builder Referral Points">
                            <Icon name="builder" size="xs" className="mr-0.5" />
                            {supporter.builder_points}
                          </div>
                          <div class="flex items-center text-xs text-sky-600" title="Validator Referral Points">
                            <Icon name="validator" size="xs" className="mr-0.5" />
                            {supporter.validator_points}
                          </div>
                        </div>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
      </div>
</div>
