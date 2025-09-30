<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Avatar from '../components/Avatar.svelte';
  import { usersAPI } from '../lib/api';
  import Icons from '../components/Icons.svelte';

  // State management
  let referralData = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let searchQuery = $state('');

  // Filter referrals based on search
  let filteredReferrals = $derived(
    !searchQuery || !referralData?.referrals ? (referralData?.referrals || []) :
    referralData.referrals.filter(entry => {
      const query = searchQuery.toLowerCase();
      const name = entry.name?.toLowerCase() || '';
      const address = entry.address?.toLowerCase() || '';
      return name.includes(query) || address.includes(query);
    })
  );

  // Fetch referral data
  async function fetchReferrals() {
    try {
      loading = true;
      error = null;
      const response = await usersAPI.getReferrals();
      referralData = response.data;
    } catch (err) {
      error = err.message || 'Failed to load referrals';
    } finally {
      loading = false;
    }
  }

  // Helper function to format date
  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  // Helper to get badge type
  function getBadgeType(referral) {
    if (referral.is_validator) return 'Validator';
    if (referral.is_builder) return 'Builder';
    if (referral.is_steward) return 'Steward';
    return 'Undetermined';
  }

  // Helper for badge styling
  function getBadgeClass(referral) {
    if (referral.is_validator) return 'bg-blue-100 text-blue-800';
    if (referral.is_builder) return 'bg-orange-100 text-orange-800';
    if (referral.is_steward) return 'bg-green-100 text-green-800';
    return 'bg-gray-100 text-gray-800';
  }

  // Fetch on mount
  onMount(() => {
    fetchReferrals();
  });
</script>

<div class="space-y-6 sm:space-y-8">
  <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
    <div>
      <h1 class="text-2xl font-bold text-gray-900">My Referrals</h1>
      <p class="mt-1 text-sm text-gray-500">
        People you've brought to the GenLayer ecosystem
      </p>
    </div>

    {#if !loading && !error && referralData?.referrals?.length > 0}
      <div class="w-full sm:w-64">
        <label for="search" class="sr-only">Search referrals</label>
        <div class="relative">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
          </div>
          <input
            id="search"
            bind:value={searchQuery}
            type="search"
            class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-purple-500 focus:border-purple-500 sm:text-sm"
            placeholder="Search by name or address"
          />
        </div>
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="flex justify-center items-center p-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border-l-4 border-red-400 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">Error loading referrals</h3>
          <p class="mt-1 text-sm text-red-700">{error}</p>
        </div>
      </div>
    </div>
  {:else if !referralData || referralData.referrals.length === 0}
    <div class="bg-white shadow rounded-lg p-12 text-center">
      <div class="mx-auto w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mb-4">
        <svg class="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-gray-900 mb-2">No Referrals Yet</h3>
      <p class="text-gray-600">Start inviting people to the GenLayer ecosystem to see them here!</p>
    </div>
  {:else}
    <!-- Summary Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
      <div class="bg-white shadow rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-2.5 rounded-lg bg-purple-100 text-purple-600 mr-3">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
          </div>
          <div class="flex-1">
            <p class="text-sm text-gray-500">Total Referrals</p>
            <p class="text-xl font-bold text-gray-900">{referralData.total_referrals}</p>
          </div>
        </div>
      </div>

      <div class="bg-white shadow rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-2.5 rounded-lg bg-purple-100 text-purple-600 mr-3">
            <Icons name="lightning" size="md" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-gray-500">Total Referral Points</p>
            <p class="text-xl font-bold text-gray-900">{referralData.total_bonus_points}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Referrals Table -->
    <div class="bg-white shadow rounded-lg">
      {#if searchQuery && filteredReferrals.length === 0}
        <div class="p-6 text-center text-gray-500">
          No referrals found matching "{searchQuery}"
        </div>
      {:else}
        <div class="px-4 py-3 border-b border-gray-200">
          <p class="text-sm text-gray-700">
            Showing {searchQuery ? `${filteredReferrals.length} of` : ''} {referralData.referrals.length} referrals
          </p>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Participant
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contributions
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Points Earned
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Your Points
                </th>
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Joined Date
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each filteredReferrals as referral, i}
                <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                      <div class="flex-shrink-0 mr-3">
                        <Avatar
                          user={referral}
                          size="sm"
                          clickable={true}
                        />
                      </div>
                      <div>
                        <button
                          onclick={() => push(`/participant/${referral.address}`)}
                          class="text-sm font-medium text-gray-900 hover:text-purple-600 transition-colors"
                        >
                          {referral.name || 'Anonymous'}
                        </button>
                        <div class="text-sm text-gray-500">
                          {referral.address.slice(0, 6)}...{referral.address.slice(-4)}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getBadgeClass(referral)}`}>
                      {getBadgeType(referral)}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">{referral.contributions_count || 0}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900 font-medium">{(referral.total_points ?? 0).toLocaleString()}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center text-sm font-medium text-purple-600">
                      <Icons name="lightning" size="xs" className="mr-1" />
                      {(referral.bonus_points ?? 0).toLocaleString()}
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(referral.created_at)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
</div>