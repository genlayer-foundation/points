<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import StatCard from '../components/StatCard.svelte';
  import TopLeaderboard from '../components/TopLeaderboard.svelte';
  import FeaturedContributions from '../components/FeaturedContributions.svelte';
  import RecentContributions from '../components/RecentContributions.svelte';
  import GlobalDashboard from '../components/GlobalDashboard.svelte';
  import WelcomeNewUser from '../components/WelcomeNewUser.svelte';
  import Avatar from '../components/Avatar.svelte';
  import { contributionsAPI, usersAPI, statsAPI, leaderboardAPI, validatorsAPI } from '../lib/api';
  import { push } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';

  // State management
  let newestValidators = $state([]);
  let stats = $state({
    totalParticipants: 0,
    totalContributions: 0,
    totalPoints: 0,
    lastUpdated: null
  });

  let newestValidatorsLoading = $state(true);
  let statsLoading = $state(true);
  let newestValidatorsError = $state(null);
  let statsError = $state(null);

  // Format date helper
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };

  // Function to fetch data based on category
  async function fetchDashboardData() {

    try {
      // Fetch newest participants based on category
      newestValidatorsLoading = true;

      if ($currentCategory === 'validator') {
        // For validators, use the specialized endpoint that gets first uptime
        const validatorsRes = await validatorsAPI.getNewestValidators(5);
        newestValidators = validatorsRes.data || [];
      } else {
        // For other categories, get recent contributions
        const params = {
          limit: 50,
          ordering: '-contribution_date'
        };

        if ($currentCategory !== 'global') {
          params.category = $currentCategory;
        }

        const contributionsRes = await contributionsAPI.getContributions(params);

        // Extract unique users from contributions
        const seenUsers = new Set();
        const uniqueParticipants = [];

        if (contributionsRes.data && contributionsRes.data.results) {
          for (const contribution of contributionsRes.data.results) {
            if (contribution.user_details && !seenUsers.has(contribution.user_details.address)) {
              seenUsers.add(contribution.user_details.address);
              uniqueParticipants.push({
                ...contribution.user_details,
                first_uptime_date: contribution.contribution_date
              });
              if (uniqueParticipants.length >= 5) break;
            }
          }
        }

        newestValidators = uniqueParticipants;
      }

      newestValidatorsLoading = false;
    } catch (error) {
      newestValidatorsError = error.message || `Failed to load newest ${$currentCategory === 'validator' ? 'validators' : $currentCategory === 'builder' ? 'builders' : 'participants'}`;
      newestValidatorsLoading = false;
    }

    try {
      // Fetch stats based on category
      statsLoading = true;

      if ($currentCategory === 'global') {
        // For global, use the stats API
        try {
          const dashboardStats = await statsAPI.getDashboardStats();
          if (dashboardStats.data) {
            stats = {
              totalParticipants: dashboardStats.data.participant_count || 0,
              totalContributions: dashboardStats.data.contribution_count || 0,
              totalPoints: dashboardStats.data.total_points || 0,
              lastUpdated: new Date().toISOString()
            };
          }
        } catch (statsApiError) {
          console.warn('Stats API failed, falling back to individual requests', statsApiError);

          // Fallback to individual requests
          const [participantCountRes, contributionsRes] = await Promise.all([
            usersAPI.getParticipantCount(),
            contributionsAPI.getContributions({ limit: 1 })
          ]);

          stats = {
            totalParticipants: participantCountRes.data.count || 0,
            totalContributions: contributionsRes.data.count || 0,
            totalPoints: 0,
            lastUpdated: new Date().toISOString()
          };
        }
      } else {
        // For categories, fetch filtered data using type endpoint
        const [leaderboardRes, contributionsRes] = await Promise.all([
          leaderboardAPI.getLeaderboardByType($currentCategory),
          contributionsAPI.getContributions({ category: $currentCategory, limit: 1 })
        ]);

        // API now returns array directly
        const categoryEntries = Array.isArray(leaderboardRes.data) ? leaderboardRes.data : [];
        const categoryContributions = contributionsRes.data;

        stats = {
          totalParticipants: categoryEntries.length,
          totalContributions: categoryContributions.count || 0,
          totalPoints: categoryEntries.reduce((sum, entry) => sum + (entry.total_points || 0), 0),
          lastUpdated: new Date().toISOString()
        };
      }

      statsLoading = false;
    } catch (error) {
      statsError = error.message || 'Failed to load statistics';
      statsLoading = false;
      console.error('Error fetching dashboard stats:', error);
    }
  }

  // Fetch data when category changes (including initial mount)
  let previousCategory = $state(null);

  $effect(() => {
    if ($currentCategory && $currentCategory !== previousCategory) {
      previousCategory = $currentCategory;
      fetchDashboardData();
    }
  });

  // Icons for stat cards
  const icons = {
    participants: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    contributions: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    points: 'M13 10V3L4 14h7v7l9-11h-7z'
  };
</script>

<!-- Welcome message for new users -->
<WelcomeNewUser />

{#if $currentCategory === 'global'}
  <!-- Global Dashboard - Use separate component -->
  <GlobalDashboard />
{:else}
  <!-- Category-specific Dashboard -->
  <div class="space-y-6 sm:space-y-8">
    <h1 class="text-2xl font-bold text-gray-900">
      {$currentCategory === 'builder' ? 'Builders' :
       $currentCategory === 'validator' ? 'Validators' :
       $currentCategory === 'steward' ? 'Stewards' : 'Dashboard'}
    </h1>

  <!-- Connection error message if needed -->
  {#if statsError}
    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-yellow-700">
            Having trouble connecting to the API. Some data might not display correctly.
          </p>
        </div>
      </div>
    </div>
  {/if}

  <!-- Stats Section -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <StatCard
      title="Total Participants"
      value={statsLoading ? '...' : (stats.totalParticipants || 0)}
      icon={icons.participants}
      color="blue"
    />
    <StatCard
      title="Total Contributions"
      value={statsLoading ? '...' : (stats.totalContributions || 0)}
      icon={icons.contributions}
      color="green"
    />
    <StatCard
      title="Total Points"
      value={statsLoading ? '...' : (stats.totalPoints || 0)}
      icon={icons.points}
      color="purple"
    />
  </div>

  <!-- First Row: Leaderboard and Highlights -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Top Leaderboard -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-purple-100 rounded-lg">
            <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">
            Top {$currentCategory === 'builder' ? 'Builders' :
                 $currentCategory === 'validator' ? 'Validators' :
                 $currentCategory === 'steward' ? 'Stewards' : 'Participants'}
          </h2>
        </div>
        <button
          onclick={() => push($currentCategory === 'builder' ? '/builders/leaderboard' : $currentCategory === 'validator' ? '/validators/leaderboard' : '/leaderboard')}
          class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          View all
          <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>
      <TopLeaderboard
        showHeader={false}
      />
    </div>

    <!-- Featured Highlights -->
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
          onclick={() => push($currentCategory === 'builder' ? '/builders/contributions/highlights' : $currentCategory === 'validator' ? '/validators/contributions/highlights' : '/contributions/highlights')}
          class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          View all
          <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>
      <FeaturedContributions
        showHeader={false}
        showViewAll={false}
        cardStyle="highlight"
      />
    </div>
  </div>

  <!-- Second Row: Newest Validators and Recent Contributions -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <!-- Newest Validators -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-blue-100 rounded-lg">
            <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">
            Newest {$currentCategory === 'builder' ? 'Builders' :
                    $currentCategory === 'validator' ? 'Validators' :
                    $currentCategory === 'steward' ? 'Stewards' : 'Participants'}
          </h2>
        </div>
        <button
          onclick={() => push($currentCategory === 'builder' ? '/builders/participants' : $currentCategory === 'validator' ? '/validators/participants' : '/participants')}
          class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          View all
          <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>

      {#if newestValidatorsLoading}
        <div class="flex justify-center items-center p-8">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      {:else if newestValidatorsError}
        <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p>{newestValidatorsError}</p>
        </div>
      {:else if newestValidators.length === 0}
        <div class="bg-gray-50 rounded-lg p-6 text-center">
          <p class="text-gray-500">No new validators yet.</p>
        </div>
      {:else}
        <div class="bg-white shadow rounded-lg divide-y divide-gray-200">
          {#each newestValidators as validator}
            <div class="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
              <div class="flex items-center gap-3">
                <Avatar
                  user={validator}
                  size="sm"
                  clickable={true}
                />
                <div class="min-w-0">
                  <button
                    class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors truncate"
                    onclick={() => push(`/participant/${validator.address}`)}
                  >
                    {validator.name || `${validator.address.slice(0, 6)}...${validator.address.slice(-4)}`}
                  </button>
                  <div class="text-xs text-gray-500">
                    {formatDate(validator.first_uptime_date || validator.created_at)}
                  </div>
                </div>
              </div>
              <button
                onclick={() => push(`/participant/${validator.address}`)}
                class="text-xs text-primary-600 hover:text-primary-700 font-medium flex-shrink-0"
              >
                View →
              </button>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Recent Contributions -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="p-1.5 bg-green-100 rounded-lg">
            <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <h2 class="text-lg font-semibold text-gray-900">Recent Contributions</h2>
        </div>
        <button
          onclick={() => push($currentCategory === 'builder' ? '/builders/contributions' : $currentCategory === 'validator' ? '/validators/contributions' : '/contributions')}
          class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          View all
          <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
          </svg>
        </button>
      </div>
      <RecentContributions
        showHeader={false}
      />
    </div>
  </div>
  </div>
{/if}
