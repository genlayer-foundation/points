<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { leaderboardAPI, usersAPI, contributionsAPI } from '../lib/api';
  import Avatar from '../components/Avatar.svelte';
  import Icon from '../components/Icons.svelte';

  // State variables
  let waitlistUsers = $state([]);
  let loading = $state(true);
  let error = $state(null);

  onMount(async () => {
    await fetchWaitlistData();
  });

  // Format date helper
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };

  async function fetchWaitlistData() {
    try {
      loading = true;
      error = null;

      // Fetch waitlist-only users
      const [waitlistResponse, usersRes] = await Promise.all([
        leaderboardAPI.getLeaderboardByType('validator-waitlist'),
        usersAPI.getUsers()
      ]);

      if (waitlistResponse.data) {
        const rawEntries = Array.isArray(waitlistResponse.data) ? waitlistResponse.data : [];
        const allUsers = usersRes.data.results || [];

        // Get contributions for waitlist users to find their join dates
        const waitlistContributions = await contributionsAPI.getContributions({
          contribution_type_slug: 'validator-waitlist',
          limit: 100
        });

        // Process and enrich waitlist user data
        waitlistUsers = rawEntries.map(entry => {
          const userDetails = entry.user_details || {};

          // Find full user data
          const fullUser = allUsers.find(u =>
            u.address && userDetails.address &&
            u.address.toLowerCase() === userDetails.address.toLowerCase()
          );

          // Find when they joined the waitlist
          const waitlistContribution = waitlistContributions.data?.results?.find(c =>
            c.user_details?.address?.toLowerCase() === userDetails.address?.toLowerCase()
          );

          return {
            address: userDetails.address || '',
            isWaitlisted: true,
            user: fullUser || userDetails,
            score: entry.total_points,
            waitlistRank: entry.rank,
            nodeVersion: fullUser?.validator?.node_version || null,
            matchesTarget: fullUser?.validator?.matches_target || false,
            targetVersion: fullUser?.validator?.target_version || null,
            joinedWaitlist: waitlistContribution?.contribution_date || fullUser?.created_at,
            referral_points: entry.referral_points || null
          };
        });

        // Sort by waitlist rank
        waitlistUsers.sort((a, b) => {
          if (a.waitlistRank && b.waitlistRank) {
            return a.waitlistRank - b.waitlistRank;
          }
          return 0;
        });
      }

      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load waitlist data';
      loading = false;
    }
  }

  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }
</script>

<div class="space-y-6 sm:space-y-8">
  <!-- Header with back button -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-4">
      <button
        onclick={() => push('/validators/waitlist')}
        class="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
        </svg>
        Back to Waitlist
      </button>
    </div>
  </div>

  <div class="flex items-center gap-2">
    <div class="p-1.5 bg-gray-100 rounded-lg">
      <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
      </svg>
    </div>
    <h1 class="text-2xl font-bold text-gray-900">All Waitlist Participants</h1>
    {#if !loading}
      <span class="text-sm text-gray-500 ml-auto">
        {waitlistUsers.length} participants in the journey
      </span>
    {/if}
  </div>

  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center items-center p-16">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if waitlistUsers.length === 0}
    <div class="bg-white shadow rounded-lg p-8 text-center">
      <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p class="text-lg font-medium text-gray-900 mb-2">No participants on the journey</p>
      <p class="text-sm text-gray-500">All waitlisted users have graduated as validators</p>
    </div>
  {:else}
    <div class="bg-white shadow overflow-hidden sm:rounded-lg">
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
                Address
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Node Version
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Points
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Journey Status
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each waitlistUsers as user, i}
              {@const referralTotal = user.referral_points ? user.referral_points.builder_points + user.referral_points.validator_points : 0}
              {@const contributionPoints = Math.max(0, user.score - referralTotal)}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                    #{user.waitlistRank}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    <Avatar
                      user={user.user}
                      size="sm"
                      clickable={true}
                    />
                    <div>
                      <div class="text-sm font-medium text-gray-900">
                        {user.user?.name || 'Unnamed'}
                      </div>
                      {#if user.joinedWaitlist}
                        <div class="text-xs text-gray-500">
                          Joined {formatDate(user.joinedWaitlist)}
                        </div>
                      {/if}
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <code class="text-xs font-mono text-gray-600">
                      {truncateAddress(user.address)}
                    </code>
                    <a
                      href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${user.address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-gray-400 hover:text-gray-600"
                      title="View in Explorer"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                      </svg>
                    </a>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  {#if user.nodeVersion}
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-sm">{user.nodeVersion}</span>
                      {#if user.matchesTarget}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          ✓ Ready
                        </span>
                      {:else if user.targetVersion}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                          Update needed
                        </span>
                      {/if}
                    </div>
                  {:else}
                    <span class="text-gray-400 text-sm">Not set</span>
                  {/if}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    <div class="flex items-center gap-1">
                      <Icon name="lightning" size="sm" className="text-amber-600" />
                      <span class="text-sm font-medium text-gray-900">{contributionPoints}</span>
                    </div>
                    {#if referralTotal > 0}
                      <div class="flex items-center gap-1">
                        <Icon name="users" size="sm" className="text-purple-600" />
                        <span class="text-sm font-medium text-purple-600">{referralTotal}</span>
                      </div>
                    {/if}
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    On Journey
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <button
                    onclick={() => push(`/participant/${user.address}`)}
                    class="text-sm text-primary-600 hover:text-primary-900 font-medium"
                  >
                    View Profile →
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>
