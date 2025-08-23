<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import api, { usersAPI, leaderboardAPI, contributionsAPI } from '../lib/api';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Avatar from '../components/Avatar.svelte';
  import StatCard from '../components/StatCard.svelte';
  import ContributionCard from '../components/ContributionCard.svelte';
  
  // State variables
  let waitlistUsers = $state([]);
  let newestWaitlistUsers = $state([]);
  let recentlyGraduated = $state([]);
  let featuredContributions = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let statistics = $state({
    total_waitlist_badges: 0,
    total_validators: 0,
    waitlist_only_count: 0
  });
  
  let stats = $state({
    totalParticipants: 0,
    totalContributions: 0,
    totalPoints: 0
  });
  
  let statsLoading = $state(true);
  let graduatesLoading = $state(true);
  let featuredLoading = $state(true);
  
  onMount(async () => {
    await Promise.all([
      fetchWaitlistData(),
      fetchRecentlyGraduated(),
      fetchFeaturedContributions()
    ]);
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
      statsLoading = true;
      error = null;
      
      // Fetch waitlist-only users
      const [waitlistResponse, statsResponse, usersRes] = await Promise.all([
        leaderboardAPI.getLeaderboardByType('validator-waitlist'),
        leaderboardAPI.getWaitlistStats(),
        usersAPI.getUsers()
      ]);
      
      if (waitlistResponse.data) {
        // API returns array directly now
        const rawEntries = Array.isArray(waitlistResponse.data) ? waitlistResponse.data : [];
        statistics = statsResponse.data || {};
        const allUsers = usersRes.data.results || [];
        
        // Get contributions for waitlist users to find their join dates
        const waitlistContributions = await contributionsAPI.getContributions({
          contribution_type_slug: 'validator-waitlist',
          limit: 100
        });
        
        // Process and enrich waitlist user data
        waitlistUsers = rawEntries.map(entry => {
          // API now returns user_details instead of user
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
            globalRank: null, // No global rank in new system
            nodeVersion: fullUser?.validator?.node_version || null,
            matchesTarget: fullUser?.validator?.matches_target || false,
            targetVersion: fullUser?.validator?.target_version || null,
            joinedWaitlist: waitlistContribution?.contribution_date || fullUser?.created_at
          };
        });
        
        // Sort by waitlist rank
        waitlistUsers.sort((a, b) => {
          if (a.waitlistRank && b.waitlistRank) {
            return a.waitlistRank - b.waitlistRank;
          }
          return 0;
        });
        
        // Get the 5 newest waitlist users
        newestWaitlistUsers = [...waitlistUsers]
          .sort((a, b) => {
            const dateA = new Date(a.joinedWaitlist || 0);
            const dateB = new Date(b.joinedWaitlist || 0);
            return dateB - dateA;
          })
          .slice(0, 5);
      }
      
      // Update stats from the stats response
      if (statsResponse.data) {
        stats = {
          totalParticipants: statsResponse.data.total_participants || 0,
          totalContributions: statsResponse.data.total_contributions || 0,
          totalPoints: statsResponse.data.total_points || 0
        };
      }
      
      loading = false;
      statsLoading = false;
    } catch (err) {
      error = err.message || 'Failed to load waitlist data';
      loading = false;
      statsLoading = false;
    }
  }
  
  async function fetchRecentlyGraduated() {
    try {
      graduatesLoading = true;
      // Fetch graduation leaderboard (sorted by date, most recent first)
      const response = await leaderboardAPI.getLeaderboardByType('validator-waitlist-graduation');
      
      if (response.data) {
        // Transform leaderboard entries to match the expected format
        recentlyGraduated = response.data.map(entry => ({
          user: entry.user_details || entry.user,
          graduated_date: entry.graduation_date,
          points_at_graduation: entry.total_points,
          rank: entry.rank
        }));
      }
      
      graduatesLoading = false;
    } catch (err) {
      console.error('Failed to load recently graduated:', err);
      recentlyGraduated = [];
      graduatesLoading = false;
    }
  }
  
  async function fetchFeaturedContributions() {
    try {
      featuredLoading = true;
      
      // Fetch featured contributions from waitlist users only
      const response = await contributionsAPI.getHighlights({
        waitlist_only: true,
        limit: 5
      });
      
      if (response.data) {
        featuredContributions = response.data;
      }
      
      featuredLoading = false;
    } catch (err) {
      console.error('Failed to load featured contributions:', err);
      featuredLoading = false;
    }
  }
  
  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }
  
  // Icons for stat cards
  const icons = {
    participants: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    contributions: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    points: 'M13 10V3L4 14h7v7l9-11h-7z'
  };
</script>

<div class="space-y-6 sm:space-y-8">
  <h1 class="text-2xl font-bold text-gray-900">
    Validator Waitlist Journey
  </h1>
  
  {#if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
      {error}
    </div>
  {/if}
  
  <!-- Stats Section -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <StatCard 
      title="Validator Waitlist Participants" 
      value={statsLoading ? '...' : stats.totalParticipants} 
      icon={icons.participants}
      color="amber"
    />
    <StatCard 
      title="Total Contributions" 
      value={statsLoading ? '...' : stats.totalContributions} 
      icon={icons.contributions}
      color="green"
    />
    <StatCard 
      title="Total Points" 
      value={statsLoading ? '...' : stats.totalPoints} 
      icon={icons.points}
      color="purple"
    />
  </div>
  
  <!-- First Row: Race to Testnet and Recently Graduated -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Race to Testnet Asimov -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-amber-100 rounded-lg">
            <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Race to Testnet Asimov</h2>
        </div>
      </div>
      
      {#if loading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if waitlistUsers.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No participants in the race yet.</p>
        </div>
      {:else}
        <div class="bg-white shadow rounded-lg divide-y divide-gray-200">
          {#each waitlistUsers.slice(0, 10) as user}
            <div class="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
              <div class="flex items-center gap-3">
                <div class="flex items-center justify-center w-8 h-8 rounded-full bg-amber-100 text-amber-700 font-semibold text-sm">
                  #{user.waitlistRank}
                </div>
                <Avatar 
                  user={user.user}
                  size="sm"
                  clickable={true}
                />
                <div class="min-w-0">
                  <button
                    class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors truncate"
                    onclick={() => push(`/participant/${user.address}`)}
                  >
                    {user.user?.name || truncateAddress(user.address)}
                  </button>
                  <div class="text-xs text-gray-500">
                    {user.score} points
                  </div>
                </div>
              </div>
              <button
                onclick={() => push(`/participant/${user.address}`)}
                class="text-xs text-primary-600 hover:text-primary-700 font-medium flex-shrink-0"
              >
                View →
              </button>
            </div>
          {/each}
        </div>
      {/if}
    </div>
    
    <!-- Recently Graduated -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-green-100 rounded-lg">
            <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Recently Graduated</h2>
        </div>
      </div>
      
      {#if graduatesLoading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if recentlyGraduated.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No recent graduations.</p>
        </div>
      {:else}
        <div class="bg-white shadow rounded-lg divide-y divide-gray-200">
          {#each recentlyGraduated.slice(0, 5) as graduate}
            <div class="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
              <div class="flex items-center gap-3">
                <Avatar 
                  user={graduate.user}
                  size="sm"
                  clickable={true}
                />
                <div class="min-w-0">
                  <button
                    class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors truncate"
                    onclick={() => push(`/participant/${graduate.user.address}`)}
                  >
                    {graduate.user.name || truncateAddress(graduate.user.address)}
                  </button>
                  <div class="text-xs text-gray-500">
                    Graduated with {graduate.points_at_graduation} points
                  </div>
                </div>
              </div>
              <div class="text-right">
                <div class="text-xs font-medium text-amber-600">
                  Rank #{graduate.rank}
                </div>
                <div class="text-xs text-gray-500">
                  {formatDate(graduate.graduated_date)}
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
  
  <!-- Second Row: Featured Contributions and Newest Participants -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Featured Contributions -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-yellow-100 rounded-lg">
            <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Featured Contributions</h2>
        </div>
        <button
          onclick={() => push('/validators/contributions/highlights')}
          class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          View all
          <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>
      
      {#if featuredLoading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if featuredContributions.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No featured contributions yet.</p>
        </div>
      {:else}
        <div class="space-y-3">
          {#each featuredContributions.slice(0, 3) as highlight}
            <ContributionCard 
              contribution={highlight.contribution}
              showUser={true}
              compact={true}
              highlighted={true}
            />
          {/each}
        </div>
      {/if}
    </div>
    
    <!-- Newest Waitlist Participants -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-blue-100 rounded-lg">
            <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Newest Waitlist Participants</h2>
        </div>
      </div>
      
      {#if loading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if newestWaitlistUsers.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No new participants.</p>
        </div>
      {:else}
        <div class="bg-white shadow rounded-lg divide-y divide-gray-200">
          {#each newestWaitlistUsers as user}
            <div class="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
              <div class="flex items-center gap-3">
                <Avatar 
                  user={user.user}
                  size="sm"
                  clickable={true}
                />
                <div class="min-w-0">
                  <button
                    class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors truncate"
                    onclick={() => push(`/participant/${user.address}`)}
                  >
                    {user.user?.name || truncateAddress(user.address)}
                  </button>
                  <div class="text-xs text-gray-500">
                    Joined {formatDate(user.joinedWaitlist)}
                  </div>
                </div>
              </div>
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                #{user.waitlistRank}
              </span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
  
  <!-- Full Waitlist Table -->
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="p-1.5 bg-gray-100 rounded-lg">
          <svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
        </div>
        <h2 class="text-lg font-semibold text-gray-900">All Waitlist Participants</h2>
      </div>
      <div class="text-sm text-gray-500">
        {waitlistUsers.length} participants in the journey
      </div>
    </div>
    
    {#if loading}
      <div class="flex justify-center items-center p-8">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
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
                    <span class="text-sm font-medium text-gray-900">{user.score || 0}</span>
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
  
  <!-- Information Card -->
  <div class="bg-blue-50 border border-blue-200 rounded-lg p-6">
    <div class="flex">
      <div class="flex-shrink-0">
        <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
        </svg>
      </div>
      <div class="ml-3">
        <h3 class="text-sm font-medium text-blue-900">About the Validator Journey</h3>
        <div class="mt-2 text-sm text-blue-700">
          <p>The Validator Journey tracks participants who have joined the waitlist and are working towards becoming active validators on the GenLayer network.</p>
          <ul class="list-disc list-inside mt-2 space-y-1">
            <li>Complete tasks and earn points to climb the leaderboard</li>
            <li>Keep your node version up to date to show readiness</li>
            <li>Graduates become active validators on Testnet Asimov</li>
            <li>Track your progress in the Race to Testnet Asimov</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>