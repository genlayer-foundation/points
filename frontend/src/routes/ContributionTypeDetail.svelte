<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import ContributionsList from '../components/ContributionsList.svelte';
  import StatCard from '../components/StatCard.svelte';
  import { contributionsAPI } from '../lib/api';

  // This will be set by the router
  export let params = {};

  let contributionType = null;
  let contributions = [];
  let statistics = {};
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
      const [typeData, statsData, contributionsData] = await Promise.all([
        fetchContributionType(),
        fetchStatistics(),
        fetchContributions()
      ]);

      contributionType = typeData;
      statistics = statsData || {};
      contributions = contributionsData.results || [];
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
        <p class="text-gray-600 mb-4">{contributionType.description}</p>
      {/if}
      <p class="text-sm text-gray-500">Added on {formatDate(contributionType.created_at)}</p>
    </div>

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard 
        title="Total Contributions" 
        value={statistics.count || 0}
        icon="🏆"
        color="bg-blue-500"
      />
      <StatCard 
        title="Unique Contributors" 
        value={statistics.participants_count || 0}
        icon="👥"
        color="bg-green-500"
      />
      <StatCard 
        title="Points" 
        value={statistics.min_points != null && statistics.max_points != null && statistics.current_multiplier != null
          ? (statistics.min_points === statistics.max_points 
              ? `${Math.round(statistics.min_points * statistics.current_multiplier)}` 
              : `${Math.round(statistics.min_points * statistics.current_multiplier)} - ${Math.round(statistics.max_points * statistics.current_multiplier)}`)
          : "0"}
        icon="✨"
        color="bg-purple-500"
      />
      <StatCard 
        title="Last Contribution" 
        value={statistics.last_earned ? formatDate(statistics.last_earned) : 'Never'}
        icon="🕒"
        color="bg-yellow-500"
      />
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
    {/if}

    <!-- Contributions List -->
    <ContributionsList 
      contributions={contributions} 
      loading={false} 
      error={null} 
      showUser={true}
    />
  {:else}
    <div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">
      <p>Contribution type not found.</p>
    </div>
  {/if}
</div>