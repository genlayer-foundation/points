<script>
  import { onMount } from 'svelte';
  import StatCard from '../components/StatCard.svelte';
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import ContributionsList from '../components/ContributionsList.svelte';
  import { leaderboardAPI, contributionsAPI, usersAPI, statsAPI } from '../lib/api';
  
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
  
  // Fetch data
  onMount(async () => {
    try {
      // Fetch leaderboard
      leaderboardLoading = true;
      const leaderboardRes = await leaderboardAPI.getLeaderboard();
      leaderboard = leaderboardRes.data.results || [];
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
  <h1 class="text-2xl font-bold text-gray-900">Dashboard</h1>
  
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
  
  <!-- Leaderboard Section -->
  <LeaderboardTable
    entries={(leaderboard || []).slice(0, 10)} 
    loading={leaderboardLoading}
    error={leaderboardError}
  />
  
  <!-- Recent Contributions Section -->
  <div>
    <h2 class="text-xl font-semibold text-gray-900 mb-4">Recent Contributions</h2>
    <ContributionsList
      contributions={contributions || []}
      loading={contributionsLoading}
      error={contributionsError}
      showUser={true}
    />
  </div>
</div>