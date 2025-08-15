<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import StatCard from '../components/StatCard.svelte';
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import ContributionsList from '../components/ContributionsList.svelte';
  import { leaderboardAPI, contributionsAPI, usersAPI, statsAPI } from '../lib/api';
  import { authState } from '../lib/auth.js';
  import { push } from 'svelte-spa-router';
  
  // State management
  let leaderboard = $state([]);
  let contributions = $state([]);
  let highlights = $state([]);
  let stats = $state({
    totalParticipants: 0,
    totalContributions: 0,
    totalPoints: 0,
    lastUpdated: null
  });
  
  let leaderboardLoading = $state(true);
  let contributionsLoading = $state(true);
  let highlightsLoading = $state(true);
  let statsLoading = $state(true);
  let leaderboardError = $state(null);
  let contributionsError = $state(null);
  let highlightsError = $state(null);
  let statsError = $state(null);
  
  // Tab state  
  let activeTab = $state('highlights');
  
  // Format date helper
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };
  
  // Fetch data
  onMount(async () => {
    // Fetch highlights
    try {
      highlightsLoading = true;
      const highlightsRes = await contributionsAPI.getAllHighlights();
      highlights = highlightsRes.data || [];
      highlightsLoading = false;
    } catch (error) {
      highlightsError = error.message || 'Failed to load highlights';
      highlightsLoading = false;
    }
    
    try {
      // Fetch leaderboard
      leaderboardLoading = true;
      const leaderboardRes = await leaderboardAPI.getLeaderboard();
      // API now returns unpaginated data, so it's directly in data
      leaderboard = leaderboardRes.data || [];
      leaderboardLoading = false;
    } catch (error) {
      leaderboardError = error.message || 'Failed to load leaderboard';
      leaderboardLoading = false;
    }
    
    try {
      // Fetch recent contributions
      contributionsLoading = true;
      const contributionsRes = await contributionsAPI.getContributions({ limit: 5, ordering: '-created_at' });
      contributions = contributionsRes.data.results || [];
      contributionsLoading = false;
    } catch (error) {
      contributionsError = error.message || 'Failed to load contributions';
      contributionsLoading = false;
    }
    
    try {
      // Fetch stats
      statsLoading = true;
      
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
      
      statsLoading = false;
    } catch (error) {
      statsError = error.message || 'Failed to load statistics';
      statsLoading = false;
      console.error('Error fetching dashboard stats:', error);
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
    <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
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
        onclick={() => activeTab = 'highlights'}
        class="
          {activeTab === 'highlights' 
            ? 'border-primary-500 text-primary-600' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'} 
          whitespace-nowrap py-3 sm:py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 flex-1 sm:flex-initial
        "
      >
        <div class="flex items-center justify-center sm:justify-start gap-1 sm:gap-2">
          <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
          </svg>
          <span class="text-xs sm:text-sm">Highlights</span>
        </div>
      </button>
      
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
    {#if activeTab === 'highlights'}
      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
          <h2 class="text-lg sm:text-xl font-semibold text-gray-900">Featured Contributions</h2>
        </div>
        
        {#if highlightsLoading}
          <div class="flex justify-center items-center p-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        {:else if highlightsError}
          <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            <p>{highlightsError}</p>
          </div>
        {:else if highlights.length === 0}
          <div class="bg-gray-50 rounded-lg p-6 text-center">
            <p class="text-gray-500">No highlighted contributions yet.</p>
          </div>
        {:else}
          <div class="space-y-4">
            {#each highlights as highlight}
              <div class="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <div class="flex items-center gap-2 mb-2">
                      <svg class="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
                      </svg>
                      <h3 class="text-lg font-semibold text-gray-900">{highlight.title}</h3>
                    </div>
                    
                    <p class="text-gray-600 mb-3">{highlight.description}</p>
                    
                    <div class="flex items-center gap-4 text-sm">
                      <button 
                        class="text-primary-600 hover:text-primary-700 font-medium"
                        onclick={() => push(`/participant/${highlight.user_address}`)}
                      >
                        {highlight.user_name || `${highlight.user_address.slice(0, 6)}...${highlight.user_address.slice(-4)}`}
                      </button>
                      
                      <button
                        class="text-gray-500 hover:text-gray-700"
                        onclick={() => push(`/contribution-type/${highlight.contribution_type_id}`)}
                      >
                        {highlight.contribution_type_name}
                      </button>
                      
                      <span class="text-gray-400">•</span>
                      <span class="text-gray-500">{formatDate(highlight.contribution_date)}</span>
                    </div>
                  </div>
                  
                  <div class="ml-4 flex-shrink-0">
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800">
                      {highlight.contribution_points} pts
                    </span>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {:else if activeTab === 'leaderboard'}
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