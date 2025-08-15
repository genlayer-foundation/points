<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import ContributionsList from '../components/ContributionsList.svelte';
  import StatCard from '../components/StatCard.svelte';
  import { contributionsAPI } from '../lib/api';
  import { push } from 'svelte-spa-router';

  // This will be set by the router
  export let params = {};

  let contributionType = null;
  let contributions = [];
  let statistics = {};
  let topContributors = [];
  let recentContributions = [];
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

  // Get recent contributions for this type
  const fetchRecentContributions = async () => {
    try {
      const response = await contributionsAPI.getContributionTypeRecentContributions(params.id);
      return response.data || [];
    } catch (err) {
      console.error('Error fetching recent contributions:', err);
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
      const [typeData, statsData, contributionsData, topContributorsData, recentContributionsData] = await Promise.all([
        fetchContributionType(),
        fetchStatistics(),
        fetchContributions(),
        fetchTopContributors(),
        fetchRecentContributions()
      ]);

      contributionType = typeData;
      statistics = statsData || {};
      contributions = contributionsData.results || [];
      topContributors = topContributorsData;
      recentContributions = recentContributionsData;
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
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Top Contributors -->
        <div class="bg-white shadow rounded-lg p-6">
          <div class="flex items-center mb-4">
            <svg class="w-5 h-5 text-yellow-500 mr-2" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
            </svg>
            <h2 class="text-lg font-semibold text-gray-900">Top Contributors</h2>
          </div>
          {#if topContributors.length > 0}
            <div class="space-y-3">
              {#each topContributors as contributor, index}
                <div class="flex items-center justify-between p-3 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
                     on:click={() => push(`/participant/${contributor.address}`)}>
                  <div class="flex items-center space-x-3">
                    <div class="flex-shrink-0">
                      <span class="text-lg font-bold text-gray-500">#{index + 1}</span>
                    </div>
                    <div>
                      <p class="text-sm font-medium text-gray-900">
                        {contributor.name || `${contributor.address.slice(0, 6)}...${contributor.address.slice(-4)}`}
                      </p>
                      <p class="text-xs text-gray-500">{contributor.contribution_count} contribution{contributor.contribution_count !== 1 ? 's' : ''}</p>
                    </div>
                  </div>
                  <div class="text-right">
                    <p class="text-sm font-semibold text-purple-600">{contributor.total_points} pts</p>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <p class="text-gray-500 text-sm">No contributors yet</p>
          {/if}
        </div>

        <!-- Recent Contributions -->
        <div class="bg-white shadow rounded-lg p-6">
          <div class="flex items-center mb-4">
            <svg class="w-5 h-5 text-blue-500 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <h2 class="text-lg font-semibold text-gray-900">Recent Contributions</h2>
          </div>
          {#if recentContributions.length > 0}
            <div class="space-y-3">
              {#each recentContributions as contribution}
                <div class="p-3 hover:bg-gray-50 rounded-lg transition-colors">
                  <div class="flex justify-between items-start">
                    <div class="flex-1">
                      <p class="text-sm font-medium text-gray-900 cursor-pointer hover:text-purple-600"
                         on:click={() => push(`/participant/${contribution.user_details?.address || ''}`)}>
                        {contribution.user_details?.name || (contribution.user_details?.address ? `${contribution.user_details.address.slice(0, 6)}...${contribution.user_details.address.slice(-4)}` : 'Unknown')}
                      </p>
                      {#if contribution.notes}
                        <p class="text-xs text-gray-600 mt-1">{contribution.notes}</p>
                      {/if}
                      <p class="text-xs text-gray-500 mt-1">{formatDate(contribution.contribution_date)}</p>
                    </div>
                    <div class="ml-4">
                      <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800">
                        {contribution.frozen_global_points} pts
                      </span>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          {:else}
            <p class="text-gray-500 text-sm">No recent contributions</p>
          {/if}
        </div>
      </div>
    {/if}

  {:else}
    <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
      <p>Contribution type not found.</p>
    </div>
  {/if}
</div>