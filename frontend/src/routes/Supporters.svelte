<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Avatar from '../components/Avatar.svelte';
  import Icon from '../components/Icons.svelte';
  import { leaderboardAPI, creatorAPI } from '../lib/api';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';

  // Get current user from store
  let user = $derived($userStore.user);

  // Check if user is already a supporter (has creator profile)
  let isSupporter = $derived(!!user?.creator);

  // State management
  let supporters = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let joiningSupporter = $state(false);

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

  async function joinAsSupporter() {
    if (!$authState.isAuthenticated || !user?.address) {
      return;
    }

    try {
      joiningSupporter = true;
      error = null;

      const response = await creatorAPI.joinAsCreator();

      if (response.status === 201 || response.status === 200) {
        // Reload user data
        await userStore.loadUser();

        // Redirect to user's profile
        push(`/participant/${user.address}`);
      }
    } catch (err) {
      console.error('Error joining as supporter:', err);
      error = err.response?.data?.message || 'Failed to join as supporter';
    } finally {
      joiningSupporter = false;
    }
  }

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

      <!-- Supporter Journey Card -->
      {#if $authState.isAuthenticated && user && !isSupporter}
        <div class="bg-purple-50 border-2 border-purple-200 rounded-xl p-6 space-y-4">
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
              </div>
            </div>
            <div class="flex-1 space-y-3">
              <div>
                <h3 class="text-lg font-semibold text-gray-900 mb-1">Become a Supporter</h3>
                <p class="text-sm text-gray-600">
                  Join the GenLayer community as a supporter and help grow the ecosystem by inviting others.
                  Earn referral points for every builder and validator you bring to the network.
                </p>
              </div>
              <div class="flex items-start gap-2 text-sm text-gray-700">
                <svg class="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                </svg>
                <span>Get your unique referral link and start earning points immediately</span>
              </div>
              {#if error}
                <div class="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
                  {error}
                </div>
              {/if}
              <button
                onclick={joinAsSupporter}
                disabled={joiningSupporter}
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {#if joiningSupporter}
                  <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Joining...
                {:else}
                  Become a Supporter
                {/if}
              </button>
            </div>
          </div>
        </div>
      {:else if !$authState.isAuthenticated}
        <div class="bg-purple-50 border-2 border-purple-200 rounded-xl p-6">
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center">
                <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
            </div>
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-gray-900 mb-1">Join as a Supporter</h3>
              <p class="text-sm text-gray-600">
                Connect your wallet to become a supporter and start earning referral points for growing the GenLayer community.
              </p>
            </div>
          </div>
        </div>
      {/if}
</div>
