<script>
  import { onMount } from 'svelte';
  import StatCard from '../components/StatCard.svelte';
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import ContributionsList from '../components/ContributionsList.svelte';
  import { leaderboardAPI, contributionsAPI, usersAPI, statsAPI } from '../lib/api';
  import { authState } from '../lib/auth.js';
  import { push } from 'svelte-spa-router';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  
  // State management
  let leaderboard = $state([]);
  let contributions = $state([]);
  let stats = $state({
    totalParticipants: 0,
    totalContributions: 0,
    totalPoints: 0,
    lastUpdated: null
  });
  
  let leaderboardLoading = $state(true);
  let contributionsLoading = $state(true);
  let statsLoading = $state(true);
  let leaderboardError = $state(null);
  let contributionsError = $state(null);
  let statsError = $state(null);
  
  // Tab state
  let activeTab = $state('leaderboard');
  
  // Fetch data based on category
  async function fetchDashboardData() {
    try {
      // Fetch leaderboard based on category
      leaderboardLoading = true;
      let leaderboardRes;
      
      if ($currentCategory === 'global') {
        leaderboardRes = await leaderboardAPI.getLeaderboard();
        leaderboard = leaderboardRes.data || [];
      } else {
        // Fetch category-specific leaderboard
        const response = await fetch(`http://localhost:8002/api/v1/leaderboard/category/${$currentCategory}/`);
        const data = await response.json();
        // Transform the entries to match the expected format
        leaderboard = (data.entries || []).map(entry => ({
          rank: entry.rank,
          total_points: entry.total_points,
          user_details: {
            id: entry.user.id,
            name: entry.user.name,
            address: entry.user.address
          }
        }));
      }
      
      leaderboardLoading = false;
    } catch (error) {
      leaderboardError = error.message || 'Failed to load leaderboard';
      leaderboardLoading = false;
    }
    
    try {
      // Fetch recent contributions based on category
      contributionsLoading = true;
      const params = { limit: 5, ordering: '-created_at' };
      
      // Add category filter if not global
      if ($currentCategory !== 'global') {
        params.category = $currentCategory;
      }
      
      const contributionsRes = await contributionsAPI.getContributions(params);
      contributions = contributionsRes.data.results || [];
      contributionsLoading = false;
    } catch (error) {
      contributionsError = error.message || 'Failed to load contributions';
      contributionsLoading = false;
    }
    
    try {
      // Fetch stats based on category
      statsLoading = true;
      
      if ($currentCategory === 'global') {
        // Try to get from the stats API first
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
            contributionsAPI.getContributions({ limit: 1 }) // Just to get count from the response
          ]);
          
          stats = {
            totalParticipants: participantCountRes.data.count || 0,
            totalContributions: contributionsRes.data.count || 0,
            totalPoints: leaderboard.reduce((sum, entry) => sum + entry.total_points, 0),
            lastUpdated: new Date().toISOString()
          };
        }
      } else {
        // For category-specific stats, calculate from filtered data
        // Count unique users in the leaderboard for this category
        const participantCount = leaderboard.length;
        
        // Get contribution count for this category
        const contributionsParams = { limit: 1 };
        if ($currentCategory !== 'global') {
          contributionsParams.category = $currentCategory;
        }
        const contributionsRes = await contributionsAPI.getContributions(contributionsParams);
        
        stats = {
          totalParticipants: participantCount,
          totalContributions: contributionsRes.data.count || 0,
          totalPoints: leaderboard.reduce((sum, entry) => sum + (entry.total_points || 0), 0),
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
  
  // Fetch data on mount
  onMount(() => {
    fetchDashboardData();
  });
  
  // Re-fetch when category changes
  $effect(() => {
    if ($currentCategory) {
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

<div class="space-y-6">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-900">
      {$currentCategory === 'global' ? 'Testnet Asimov' : 
       $currentCategory === 'builder' ? 'Builders' : 
       'Validators'} Dashboard
    </h1>
    {#if $authState.isAuthenticated}
      <button
        onclick={() => push('/submit-contribution')}
        class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
        </svg>
        Submit Contribution
      </button>
    {/if}
  </div>
  
  <!-- Connection error message if needed -->
  {#if statsError || leaderboardError || contributionsError}
    <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
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
  <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
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
  
  <!-- Tab Navigation (Transparent) -->
  <div class="border-b border-gray-200">
    <nav class="-mb-px flex space-x-4 sm:space-x-8" aria-label="Tabs">
      <button
        onclick={() => activeTab = 'leaderboard'}
        class="
          {activeTab === 'leaderboard' 
            ? 'border-primary-500 text-primary-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} 
          whitespace-nowrap py-3 sm:py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 flex-1 sm:flex-initial
        "
      >
        <div class="flex items-center justify-center sm:justify-start gap-1 sm:gap-2">
          <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
          </svg>
          <span class="text-xs sm:text-sm">Leaderboard</span>
        </div>
      </button>
      
      <button
        onclick={() => activeTab = 'contributions'}
        class="
          {activeTab === 'contributions' 
            ? 'border-primary-500 text-primary-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} 
          whitespace-nowrap py-3 sm:py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 flex-1 sm:flex-initial
        "
      >
        <div class="flex items-center justify-center sm:justify-start gap-1 sm:gap-2">
          <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span class="text-xs sm:text-sm">Recent</span>
        </div>
      </button>
    </nav>
  </div>
  
  <!-- Tab Content -->
  <div class="mt-6">
    {#if activeTab === 'leaderboard'}
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
          <h2 class="text-lg sm:text-xl font-semibold text-gray-900">Top Contributors</h2>
          <button
            onclick={() => push('/leaderboard')}
            class="text-sm text-primary-600 hover:text-primary-700 font-medium self-start sm:self-auto"
          >
            View All →
          </button>
        </div>
        <LeaderboardTable
          entries={(leaderboard || []).slice(0, 10)} 
          loading={leaderboardLoading}
          error={leaderboardError}
        />
      </div>
    {:else if activeTab === 'contributions'}
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
          <h2 class="text-lg sm:text-xl font-semibold text-gray-900">Recent Contributions</h2>
          <button
            onclick={() => push('/contributions')}
            class="text-sm text-primary-600 hover:text-primary-700 font-medium self-start sm:self-auto"
          >
            View All →
          </button>
        </div>
        <ContributionsList
          contributions={contributions || []}
          loading={contributionsLoading}
          error={contributionsError}
          showUser={true}
        />
      </div>
    {/if}
  </div>
</div>