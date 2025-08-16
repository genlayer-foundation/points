<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import RecentContributions from '../components/RecentContributions.svelte';
  import FeaturedContributions from '../components/FeaturedContributions.svelte';
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import StatCard from '../components/StatCard.svelte';
  import { contributionsAPI } from '../lib/api';
  import { push } from 'svelte-spa-router';

  // This will be set by the router
  export let params = {};

  let contributionType = null;
  let contributions = [];
  let statistics = {};
  let topContributors = [];
  let loading = true;
  let error = null;

  // Get contribution type details
  const fetchContributionType = async () => {
    try {
      const response = await contributionsAPI.getContributionType(params.id);
      return response.data;
    } catch (err) {
      error = err.message;
      return null;
    }
  };

  // Get contribution type statistics
  const fetchStatistics = async () => {
    try {
      const response = await contributionsAPI.getContributionTypeStatistics();
      // Statistics endpoint returns array directly, not paginated
      const allStats = response.data || [];
      return allStats.find(stat => stat.id.toString() === params.id);
    } catch (err) {
      error = err.message;
      return {};
    }
  };

  // Get contributions for this type
  const fetchContributions = async () => {
    try {
      const response = await contributionsAPI.getContributions({ contribution_type: params.id });
      return response.data;
    } catch (err) {
      error = err.message;
      return { results: [] };
    }
  };

  // Get top contributors for this type
  const fetchTopContributors = async () => {
    try {
      const response = await contributionsAPI.getContributionTypeTopContributors(params.id);
      return response.data || [];
    } catch (err) {
      console.error('Error fetching top contributors:', err);
      return [];
    }
  };


  // Format date for display
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };

  onMount(async () => {
    loading = true;
    error = null;

    try {
      // Fetch all data in parallel
      const [typeData, statsData, contributionsData, topContributorsData] = await Promise.all([
        fetchContributionType(),
        fetchStatistics(),
        fetchContributions(),
        fetchTopContributors()
      ]);

      contributionType = typeData;
      statistics = statsData || {};
      contributions = contributionsData.results || [];
      topContributors = topContributorsData;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });
</script>

<div class="space-y-6">
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      <p class="font-bold">Error</p>
      <p>{error}</p>
    </div>
  {:else if contributionType}
    <div class="bg-white shadow rounded-lg p-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-2">{contributionType.name}</h1>
      {#if contributionType.description}
        <p class="text-gray-600 mb-3">{contributionType.description}</p>
      {/if}
      <div class="flex items-center justify-between border-t pt-3">
        <p class="text-sm text-gray-500">Added on {formatDate(contributionType.created_at)}</p>
        <div class="flex items-center">
          <span class="text-sm text-gray-500 mr-2">Points per contribution:</span>
          <span class="text-lg font-bold text-purple-600">
            {statistics.min_points != null && statistics.max_points != null && statistics.current_multiplier != null
              ? (statistics.min_points === statistics.max_points 
                  ? `${Math.round(statistics.min_points * statistics.current_multiplier)}` 
                  : `${Math.round(statistics.min_points * statistics.current_multiplier)}-${Math.round(statistics.max_points * statistics.current_multiplier)}`)
              : "0"}
          </span>
        </div>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white shadow rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 bg-blue-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Total Contributions</p>
            <p class="text-2xl font-bold text-gray-900">{statistics.count || 0}</p>
          </div>
        </div>
      </div>
      
      <div class="bg-white shadow rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 bg-green-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Unique Contributors</p>
            <p class="text-2xl font-bold text-gray-900">{statistics.participants_count || 0}</p>
          </div>
        </div>
      </div>
      
      <div class="bg-white shadow rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 bg-purple-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Total Points Given</p>
            <p class="text-2xl font-bold text-gray-900">{statistics.total_points_given || 0}</p>
          </div>
        </div>
      </div>
      
      <div class="bg-white shadow rounded-lg p-4">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 bg-yellow-100 rounded-lg mr-4">
            <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Last Contribution</p>
            <p class="text-lg font-bold text-gray-900">{statistics.last_earned ? formatDate(statistics.last_earned) : 'Never'}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Highlights Section -->
    <FeaturedContributions
      contributionTypeId={params.id}
      title="Featured Highlights"
      cardStyle="compact"
      showViewAll={false}
      className="mb-6"
    />

    <!-- Pioneer Opportunity Alert if no contributions -->
    {#if statistics.count === 0 || contributions.length === 0}
      <div class="bg-blue-50 border border-blue-200 shadow overflow-hidden rounded-lg">
        <div class="px-4 py-5 sm:px-6 bg-blue-100 border-b border-blue-200">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-blue-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 class="text-lg leading-6 font-medium text-blue-900">
              Pioneer Opportunity!
            </h3>
          </div>
          <p class="mt-1 max-w-2xl text-sm text-blue-700">
            Be the first to make this contribution and earn extra points!
          </p>
        </div>
        <div class="px-4 py-5 sm:p-6">
          <p class="text-sm text-blue-800">
            No one has earned this contribution type yet. This is a great opportunity to be a pioneer and potentially earn bonus points for being among the first contributors!
          </p>
          <div class="mt-4">
            <p class="text-sm font-semibold text-blue-900">Points:</p>
            <p class="text-2xl font-bold text-blue-900">
              {#if contributionType.min_points != null && contributionType.max_points != null && contributionType.current_multiplier != null}
                {#if contributionType.min_points === contributionType.max_points}
                  {Math.round(contributionType.min_points * contributionType.current_multiplier)}
                {:else}
                  {Math.round(contributionType.min_points * contributionType.current_multiplier)} - {Math.round(contributionType.max_points * contributionType.current_multiplier)}
                {/if}
              {:else}
                TBD
              {/if}
            </p>
          </div>
        </div>
      </div>
    {:else}
      <!-- Top Contributors and Recent Contributions -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Top Contributors -->
        <div class="space-y-4">
          <h2 class="text-lg font-semibold text-gray-900">Top Contributors</h2>
          <LeaderboardTable
            entries={topContributors.map((c, i) => ({
              rank: i + 1,
              user_details: {
                name: c.name,
                address: c.address
              },
              total_points: c.total_points
            }))}
            loading={false}
            error={null}
            showHeader={false}
            compact={true}
            hideAddress={true}
          />
        </div>

        <!-- Recent Contributions -->
        <RecentContributions 
          contributionTypeId={params.id}
          limit={10}
          showViewAll={false}
        />
      </div>
    {/if}

  {:else}
    <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
      <p>Contribution type not found.</p>
    </div>
  {/if}
</div>