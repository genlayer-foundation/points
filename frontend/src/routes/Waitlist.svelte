<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import api, { usersAPI, leaderboardAPI, contributionsAPI } from '../lib/api';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import Avatar from '../components/Avatar.svelte';
  import StatCard from '../components/StatCard.svelte';
  import ContributionCard from '../components/ContributionCard.svelte';
  import Icon from '../components/Icons.svelte';

  // Get current user from store
  let user = $derived($userStore.user);
  
  // State variables
  let topWaitlistUsers = $state([]);  // Top 10 for Race to Testnet
  let newestWaitlistUsers = $state([]);
  let recentlyGraduated = $state([]);
  let highlightedContributions = $state([]);
  let topLoading = $state(true);  // Loading for top section
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
  let highlightedLoading = $state(true);
  
  onMount(async () => {
    await Promise.all([
      fetchTopWaitlistUsers(),  // Fast: only top 10
      fetchNewestWaitlistUsers(),  // Get 5 newest for sidebar
      fetchRecentlyGraduated(),
      fetchHighlightedContributions(),
      fetchStats()  // Fetch stats separately
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

  async function fetchTopWaitlistUsers() {
    try {
      topLoading = true;

      // Fetch only top 10 for Race to Testnet
      const response = await leaderboardAPI.getWaitlistTop(10);

      if (response.data) {
        topWaitlistUsers = response.data.map(entry => ({
          address: entry.user_details?.address || '',
          isWaitlisted: true,
          user: entry.user_details || {},
          score: entry.total_points,
          waitlistRank: entry.rank,
          referral_points: entry.referral_points || null
        }));
      }

      topLoading = false;
    } catch (err) {
      console.error('Failed to load top waitlist users:', err);
      topLoading = false;
    }
  }

  async function fetchNewestWaitlistUsers() {
    try {
      // Get recent waitlist contributions to find newest participants
      const response = await contributionsAPI.getContributions({
        contribution_type_slug: 'validator-waitlist',
        limit: 5,
        ordering: '-contribution_date'
      });

      if (response.data?.results) {
        newestWaitlistUsers = response.data.results.map(contrib => ({
          address: contrib.user_details?.address || '',
          user: contrib.user_details || {},
          joinedWaitlist: contrib.contribution_date
        }));
      }
    } catch (err) {
      console.error('Failed to load newest waitlist users:', err);
    }
  }

  async function fetchStats() {
    try {
      statsLoading = true;
      error = null;

      const statsResponse = await leaderboardAPI.getWaitlistStats();

      if (statsResponse.data) {
        statistics = statsResponse.data || {};
        stats = {
          totalParticipants: statsResponse.data.total_participants || 0,
          totalContributions: statsResponse.data.total_contributions || 0,
          totalPoints: statsResponse.data.total_points || 0
        };
      }

      statsLoading = false;
    } catch (err) {
      error = err.message || 'Failed to load waitlist stats';
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
  
  async function fetchHighlightedContributions() {
    try {
      highlightedLoading = true;
      
      // Fetch highlighted contributions from waitlist users only
      const response = await contributionsAPI.getHighlights({
        waitlist_only: true,
        limit: 5
      });
      
      if (response.data) {
        highlightedContributions = response.data;
      }
      
      highlightedLoading = false;
    } catch (err) {
      console.error('Failed to load highlighted contributions:', err);
      highlightedLoading = false;
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
        <button
          onclick={() => push('/validators/waitlist/participants')}
          class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          View all
          <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>
      
      {#if topLoading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if topWaitlistUsers.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No participants in the race yet.</p>
        </div>
      {:else}
        <div class="bg-white shadow rounded-lg divide-y divide-gray-200">
          {#each topWaitlistUsers as user}
            {@const referralTotal = user.referral_points ? user.referral_points.builder_points + user.referral_points.validator_points : 0}
            {@const contributionPoints = Math.max(0, user.score - referralTotal)}
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
                  <div class="flex items-center gap-3 mt-0.5">
                    <!-- Contribution Points -->
                    <div class="flex items-center gap-1 group relative">
                      <Icon name="lightning" size="sm" className="text-amber-600" />
                      <span class="text-sm text-gray-700 font-medium">{contributionPoints}</span>
                      <!-- Tooltip -->
                      <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 whitespace-nowrap">
                        <div>Contribution Points</div>
                        <div class="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                          <div class="border-4 border-transparent border-t-gray-900"></div>
                        </div>
                      </div>
                    </div>

                    <!-- Referral Points -->
                    {#if user.referral_points}
                      {#if referralTotal > 0}
                        <div class="flex items-center gap-1 group relative">
                          <Icon name="users" size="sm" className="text-purple-600" />
                          <span class="text-sm text-purple-600 font-medium">{referralTotal}</span>
                          <!-- Tooltip -->
                          <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 whitespace-nowrap">
                            <div>Referral Points</div>
                            <div class="text-xs text-gray-300 mt-1">
                              Builder: {user.referral_points.builder_points} | Validator: {user.referral_points.validator_points}
                            </div>
                            <div class="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                              <div class="border-4 border-transparent border-t-gray-900"></div>
                            </div>
                          </div>
                        </div>
                      {/if}
                    {/if}
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
  
  <!-- Second Row: Highlighted Contributions and Newest Participants -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Highlighted Contributions -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-yellow-100 rounded-lg">
            <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Highlighted Contributions</h2>
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
      
      {#if highlightedLoading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if highlightedContributions.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No highlighted contributions yet.</p>
        </div>
      {:else}
        <div class="space-y-3">
          {#each highlightedContributions.slice(0, 3) as highlight}
            <ContributionCard 
              contribution={highlight.contribution}
              submission={{
                notes: highlight.contribution?.notes,
                evidence_items: highlight.contribution?.evidence_items
              }}
              showExpand={highlight.contribution?.evidence_items?.length > 0 || highlight.contribution?.notes}
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
      
      {#if newestWaitlistUsers.length === 0}
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
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>
  
  <!-- Join Validator Waitlist Card -->
  {#if $authState.isAuthenticated && user && !user.validator && !user.has_validator_waitlist}
    <div class="bg-sky-50 border-2 border-sky-200 rounded-xl overflow-hidden hover:shadow-lg transition-all">
      <div class="p-6">
        <div class="flex items-center mb-4">
          <div class="flex items-center justify-center w-12 h-12 bg-sky-500 rounded-full mr-4 flex-shrink-0">
            <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-bold text-sky-900 mb-1">Join the Validator Journey</h3>
            <p class="text-sky-700 text-sm">Validate and judge subjective Intelligent Contracts on Testnet Asimov</p>
          </div>
        </div>

        <div class="space-y-4">
          <div>
            <p class="text-sm text-sky-700 mb-3">The Validator Journey tracks participants who have joined the waitlist and are working towards becoming active validators on the GenLayer network.</p>
            <ul class="space-y-2">
              <li class="flex items-center text-sm text-sky-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Complete tasks and earn points to climb the leaderboard
              </li>
              <li class="flex items-center text-sm text-sky-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Graduates become active validators on Testnet Asimov
              </li>
              <li class="flex items-center text-sm text-sky-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Track your progress in the Race to Testnet Asimov
              </li>
            </ul>
          </div>

          <button
            onclick={() => push('/validators/waitlist/join')}
            class="w-full flex items-center justify-center px-4 py-3 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors font-semibold group-hover:shadow-md"
          >
            <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
            </svg>
            Join the Waitlist
          </button>
        </div>
      </div>
    </div>
  {:else if !$authState.isAuthenticated || !user || user.validator || user.has_validator_waitlist}
    <!-- Information Card (shown when not eligible to join) -->
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
              <li>Graduates become active validators on Testnet Asimov</li>
              <li>Track your progress in the Race to Testnet Asimov</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>