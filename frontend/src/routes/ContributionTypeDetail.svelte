<script>
  import { onMount } from 'svelte';
  import { format } from 'date-fns';
  import RecentContributions from '../components/RecentContributions.svelte';
  import FeaturedContributions from '../components/FeaturedContributions.svelte';
  import LeaderboardTable from '../components/LeaderboardTable.svelte';
  import StatCard from '../components/StatCard.svelte';
  import Icons from '../components/Icons.svelte';
  import Badge from '../components/Badge.svelte';
  import { contributionsAPI } from '../lib/api';
  import { push } from 'svelte-spa-router';
  import { getCategoryColors, getPioneerColors, getPioneerContributionsColors } from '../lib/categoryColors';

  // This will be set by the router
  let { params = {} } = $props();

  let contributionType = $state(null);
  let contributions = $state([]);
  let statistics = $state({});
  let topContributors = $state([]);
  let missions = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let expandedMissions = $state(new Set());

  // Determine category colors based on contribution type
  let categoryColors = $derived(contributionType ? getCategoryColors(contributionType.category) : getCategoryColors('global'));
  let pioneerColors = $derived(contributionType ? getPioneerColors(contributionType.category) : getPioneerColors('global'));

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
      const response = await contributionsAPI.getContributions({ 
        contribution_type: params.id,
        ordering: '-contribution_date'  // Order by contribution date descending
      });
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

  // Get missions for this contribution type
  const fetchMissions = async () => {
    try {
      const response = await contributionsAPI.getMissions({
        contribution_type: params.id
      });

      if (response.data?.results !== undefined) {
        return response.data.results || [];
      } else {
        return response.data || [];
      }
    } catch (err) {
      console.error('Error fetching missions:', err);
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

  // Toggle expanded state for missions
  function toggleMissionExpanded(missionId) {
    const newExpanded = new Set(expandedMissions);
    if (newExpanded.has(missionId)) {
      newExpanded.delete(missionId);
    } else {
      newExpanded.add(missionId);
    }
    expandedMissions = newExpanded;
  }

  onMount(async () => {
    loading = true;
    error = null;

    try {
      // Fetch all data in parallel
      const [typeData, statsData, contributionsData, topContributorsData, missionsData] = await Promise.all([
        fetchContributionType(),
        fetchStatistics(),
        fetchContributions(),
        fetchTopContributors(),
        fetchMissions()
      ]);

      contributionType = typeData;
      statistics = statsData || {};
      contributions = contributionsData.results || [];
      topContributors = topContributorsData;
      missions = missionsData;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });
</script>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .smooth-expand {
    transition: max-height 0.3s ease-out;
    overflow: hidden;
  }
</style>

<div class="min-h-screen {categoryColors.pageBg} -m-8 p-8">
  <div class="space-y-6 sm:space-y-8">
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
    <div class="{categoryColors.headerBg} shadow rounded-lg p-4 sm:p-6 border-2 {categoryColors.borderLight}">
      <h1 class="text-xl sm:text-2xl font-bold {categoryColors.textDark} mb-2">{contributionType.name}</h1>
      {#if contributionType.description}
        <p class="text-sm sm:text-base text-gray-600 mb-4">{contributionType.description}</p>
      {/if}
      
      <!-- Ideas Section -->
      {#if Array.isArray(contributionType.examples) && contributionType.examples.length}
        <div class="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div class="flex items-center gap-2 mb-3">
            <Icons name="lightbulb" size="sm" className="text-yellow-600" />
            <h3 class="text-sm font-semibold text-yellow-800">Ideas</h3>
          </div>
          <div class="flex flex-wrap gap-2">
            {#each contributionType.examples as example}
              <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-300">
                {example}
              </span>
            {/each}
          </div>
        </div>
      {/if}
      
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 border-t pt-4">
        <p class="text-sm text-gray-500">Added on {formatDate(contributionType.created_at)}</p>
        <div class="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
          <span class="text-sm text-gray-500">Points per contribution:</span>
          <span class="text-xl sm:text-lg font-bold text-purple-600">
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
      <div class="{categoryColors.cardBg} shadow rounded-lg p-4 border {categoryColors.borderLight}">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 {categoryColors.statBg} rounded-lg mr-4">
            <svg class="w-6 h-6 {categoryColors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Total Contributions</p>
            <p class="text-2xl font-bold text-gray-900">{statistics.count || 0}</p>
          </div>
        </div>
      </div>
      
      <div class="{categoryColors.cardBg} shadow rounded-lg p-4 border {categoryColors.borderLight}">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 {categoryColors.statBg} rounded-lg mr-4">
            <svg class="w-6 h-6 {categoryColors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Unique Contributors</p>
            <p class="text-2xl font-bold text-gray-900">{statistics.participants_count || 0}</p>
          </div>
        </div>
      </div>
      
      <div class="{categoryColors.cardBg} shadow rounded-lg p-4 border {categoryColors.borderLight}">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 {categoryColors.statBg} rounded-lg mr-4">
            <svg class="w-6 h-6 {categoryColors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
            </svg>
          </div>
          <div>
            <p class="text-sm text-gray-500">Total Points Given</p>
            <p class="text-2xl font-bold text-gray-900">{statistics.total_points_given || 0}</p>
          </div>
        </div>
      </div>
      
      <div class="{categoryColors.cardBg} shadow rounded-lg p-4 border {categoryColors.borderLight}">
        <div class="flex items-center">
          <div class="flex-shrink-0 p-3 {categoryColors.statBg} rounded-lg mr-4">
            <svg class="w-6 h-6 {categoryColors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
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

    <!-- Missions for this Contribution Type -->
    {#if missions && missions.length > 0}
      {@const missionColors = getPioneerContributionsColors(contributionType?.category || 'global')}

      <div class="{missionColors.containerBg} border {missionColors.containerBorder} shadow overflow-hidden rounded-lg">
        <div class="px-4 py-5 sm:px-6 {missionColors.headerBg} border-b {missionColors.headerBorder}">
          <div class="flex items-center">
            <Icons name="sparkle" size="md" className="{missionColors.headerIcon} mr-2" />
            <h3 class="text-lg leading-6 font-medium {missionColors.headerText}">
              Missions
            </h3>
          </div>
          <p class="mt-1 max-w-2xl text-sm {missionColors.descriptionText}">
            Special missions for {contributionType?.name || 'this contribution type'}.
          </p>
        </div>

        <div class="bg-white">
          <table class="w-full">
            <thead class="{missionColors.tableHeaderBg}">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium {missionColors.tableHeaderText} uppercase tracking-wider w-1/5">
                  Mission
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium {missionColors.tableHeaderText} uppercase tracking-wider w-3/5">
                  Description
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium {missionColors.tableHeaderText} uppercase tracking-wider w-1/5">
                  End Date
                </th>
                <th class="px-4 py-3 text-right text-xs font-medium {missionColors.tableHeaderText} uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody class="divide-y {missionColors.tableBorder}">
              {#each missions as mission}
                {@const isExpanded = expandedMissions.has(mission.id)}
                {@const hasLongText = mission.long_description && mission.long_description.length > 150}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4">
                    <Badge
                      badge={{
                        id: mission.id,
                        name: mission.name,
                        description: '',
                        points: 0,
                        actionId: mission.id,
                        actionName: mission.name,
                        evidenceUrl: ''
                      }}
                      color={missionColors.badgeColor}
                      clickable={false}
                    />
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex items-start">
                      <div class="flex-1 text-sm {missionColors.contentText} prose prose-sm max-w-none">
                        <div class="{!isExpanded && hasLongText ? 'line-clamp-2' : ''}">
                          {@html (mission.long_description || mission.short_description || '').replace(/\n/g, '<br>')}
                        </div>
                      </div>
                      {#if hasLongText}
                        <button
                          onclick={() => toggleMissionExpanded(mission.id)}
                          class="ml-2 flex-shrink-0 text-gray-400 hover:text-gray-600"
                          aria-label="Toggle description"
                        >
                          <svg
                            class="h-4 w-4 transition-transform duration-200 {isExpanded ? 'rotate-180' : ''}"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      {/if}
                    </div>
                  </td>
                  <td class="px-6 py-4 text-sm {missionColors.contentText}">
                    {#if mission.end_date}
                      {formatDate(mission.end_date)}
                    {:else}
                      Ongoing
                    {/if}
                  </td>
                  <td class="px-4 py-4 text-right">
                    <button
                      onclick={() => push(`/submit-contribution?type=${params.id}`)}
                      class="inline-flex items-center text-sm font-medium {missionColors.titleText} hover:opacity-80"
                    >
                      Submit
                      <svg class="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}

    <!-- Featured User Contributions -->
    <FeaturedContributions
      contributionTypeId={params.id}
      title="Featured Contributions"
      cardStyle="compact"
      showViewAll={false}
      className="mb-6"
    />

    <!-- Pioneer Opportunity Alert if no contributions -->
    {#if statistics.count === 0 || contributions.length === 0}
      <div class="{pioneerColors.bg} border {pioneerColors.border} shadow overflow-hidden rounded-lg">
        <div class="px-4 py-5 sm:px-6 {pioneerColors.headerBg} border-b {pioneerColors.border}">
          <div class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 {pioneerColors.icon} mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <h3 class="text-lg leading-6 font-medium {pioneerColors.text}">
              Pioneer Opportunity!
            </h3>
          </div>
          <p class="mt-1 max-w-2xl text-sm {pioneerColors.accent}">
            Be the first to make this contribution and earn extra points!
          </p>
        </div>
        <div class="px-4 py-5 sm:p-6">
          <p class="text-sm {pioneerColors.text}">
            No one has earned this contribution type yet. This is a great opportunity to be a pioneer and potentially earn bonus points for being among the first contributors!
          </p>
          <div class="mt-4">
            <p class="text-sm font-semibold {pioneerColors.text}">Points:</p>
            <p class="text-2xl font-bold {pioneerColors.text}">
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
</div>