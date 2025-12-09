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

  <!-- Become a Supporter Card (only show if NOT a supporter) -->
  {#if $authState.isAuthenticated && user && !isSupporter}
    <div class="bg-purple-50 border-2 border-purple-200 rounded-xl overflow-hidden hover:shadow-lg transition-all">
      <div class="p-6">
        <div class="flex items-center mb-4">
          <div class="flex items-center justify-center w-12 h-12 bg-purple-500 rounded-full mr-4 flex-shrink-0">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-bold text-purple-900 mb-1">Become a Top Supporter</h3>
            <p class="text-purple-700 text-sm">Grow the GenLayer community and earn rewards</p>
          </div>
        </div>

        <div class="space-y-4">
          <div>
            <p class="text-sm text-purple-700 mb-3">Supporters help grow the GenLayer ecosystem by inviting others to join as Builders or Validators. The more your referrals contribute, the more points you earn!</p>
            <ul class="space-y-2">
              <li class="flex items-center text-sm text-purple-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Earn points when your referrals complete contributions
              </li>
              <li class="flex items-center text-sm text-purple-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Track Builder and Validator referral points separately
              </li>
              <li class="flex items-center text-sm text-purple-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Climb the leaderboard by supporting the ecosystem
              </li>
            </ul>
          </div>

          {#if error}
            <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
              {error}
            </div>
          {/if}

          <button
            onclick={joinAsSupporter}
            disabled={joiningSupporter}
            class="w-full flex items-center justify-center px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold group-hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {#if joiningSupporter}
              <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Joining...
            {:else}
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
              </svg>
              Become a Supporter
            {/if}
          </button>
        </div>
      </div>
    </div>
  {:else if !$authState.isAuthenticated}
    <!-- Information Card (only shown when not authenticated) -->
    <div class="bg-purple-50 border border-purple-200 rounded-lg p-6">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-purple-900">About Supporters</h3>
          <div class="mt-2 text-sm text-purple-700">
            <p>Supporters help grow the GenLayer ecosystem by inviting others to join as Builders or Validators.</p>
            <ul class="list-disc list-inside mt-2 space-y-1">
              <li>Earn points when your referrals complete contributions</li>
              <li>Track Builder and Validator referral points separately</li>
              <li>Climb the leaderboard by supporting the ecosystem</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>
