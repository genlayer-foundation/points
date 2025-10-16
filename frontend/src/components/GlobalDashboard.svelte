<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import TopLeaderboard from './TopLeaderboard.svelte';
  import FeaturedContributions from './FeaturedContributions.svelte';
  import Avatar from './Avatar.svelte';
  import { contributionsAPI, leaderboardAPI, validatorsAPI, buildersAPI } from '../lib/api';
  
  // State management
  let validatorStats = $state({ total: 0, contributions: 0, points: 0 });
  let builderStats = $state({ total: 0, contributions: 0, points: 0 });
  let validatorLeaderboard = $state([]);  // Store for reuse
  let builderLeaderboard = $state([]);  // Store for reuse
  let newestValidators = $state([]);
  let newestBuilders = $state([]);
  let statsLoading = $state(true);
  let newestValidatorsLoading = $state(true);
  let newestBuildersLoading = $state(true);
  
  // Format date helper
  const formatDate = (dateString) => {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  };
  
  async function fetchGlobalData() {
    // Fetch all data in parallel for optimal performance
    try {
      statsLoading = true;
      newestValidatorsLoading = true;
      newestBuildersLoading = true;

      // Fetch all necessary data in one parallel batch
      const [
        builderLeaderboardRes,
        validatorLeaderboardRes,
        validatorContribRes,
        builderContribRes,
        validatorsRes,
        buildersRes
      ] = await Promise.all([
        leaderboardAPI.getLeaderboardByType('builder'),
        leaderboardAPI.getLeaderboardByType('validator'),
        contributionsAPI.getContributions({ category: 'validator', limit: 1 }),
        contributionsAPI.getContributions({ category: 'builder', limit: 1 }),
        validatorsAPI.getNewestValidators(5),
        buildersAPI.getNewestBuilders(5)
      ]);

      // Process validator stats
      const validatorEntries = Array.isArray(validatorLeaderboardRes.data) ? validatorLeaderboardRes.data : [];
      validatorLeaderboard = validatorEntries;

      validatorStats = {
        total: validatorEntries.length,
        contributions: validatorContribRes.data?.count || 0,
        points: validatorEntries.reduce((sum, entry) => sum + (entry.total_points || 0), 0)
      };

      // Process builder stats
      const builderEntries = Array.isArray(builderLeaderboardRes.data) ? builderLeaderboardRes.data : [];
      builderLeaderboard = builderEntries;

      builderStats = {
        total: builderEntries.length,
        contributions: builderContribRes.data?.count || 0,
        points: builderEntries.reduce((sum, entry) => sum + (entry.total_points || 0), 0)
      };

      // Process newest validators
      newestValidators = validatorsRes.data || [];

      // Process newest builders from dedicated endpoint
      newestBuilders = buildersRes.data || [];

      statsLoading = false;
      newestValidatorsLoading = false;
      newestBuildersLoading = false;
    } catch (error) {
      console.error('Error fetching global dashboard data:', error);
      statsLoading = false;
      newestValidatorsLoading = false;
      newestBuildersLoading = false;
    }
  }
  
  onMount(() => {
    fetchGlobalData();
  });
</script>

<div class="space-y-6 sm:space-y-8">
  <!-- Title -->
  <h1 class="text-2xl font-bold text-gray-900">Testnet Asimov</h1>
  
  <!-- 2 Column Layout -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <!-- VALIDATORS COLUMN CARD -->
    <div class="bg-sky-50/30 rounded-lg shadow-sm border border-sky-100 overflow-hidden">
      <!-- Column Header -->
      <div class="bg-sky-100/50 px-5 py-3 border-b border-sky-200">
        <button
          onclick={() => push('/validators')}
          class="text-lg font-semibold font-heading text-sky-700 uppercase tracking-wider hover:text-sky-800 transition-colors"
        >
          Validators
        </button>
      </div>
      
      <!-- Column Content -->
      <div class="p-4 space-y-6 sm:space-y-8">
      
      <!-- Total Validators Stat -->
      <div class="flex items-center">
        <div class="p-3 bg-sky-100 rounded-lg mr-4">
          <svg class="w-6 h-6 text-sky-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
          </svg>
        </div>
        <div>
          <p class="text-sm text-gray-500">Total Validators</p>
          <p class="text-2xl font-bold text-gray-900">{statsLoading ? '...' : validatorStats.total}</p>
        </div>
      </div>
      
      <!-- Top Validators -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-purple-100 rounded-lg">
              <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Top Validators</h2>
          </div>
          <button
            onclick={() => push('/validators/leaderboard')}
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
          category="validator"
          limit={5}
          entries={validatorLeaderboard}
          loading={statsLoading}
        />
      </div>
      
      <!-- Featured Validators Contributions -->
      <div class="space-y-4 mt-6 sm:mt-10">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-yellow-100 rounded-lg">
              <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Featured Validators Contributions</h2>
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
        <FeaturedContributions 
          showHeader={false}
          showViewAll={false}
          category="validator"
          cardStyle="highlight"
          limit={3}
        />
      </div>
      
      <!-- Newest Validators -->
      <div class="space-y-4 mt-6 sm:mt-10">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-blue-100 rounded-lg">
              <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Newest Validators</h2>
          </div>
          <button
            onclick={() => push('/validators/participants')}
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
        {:else if newestValidators.length === 0}
          <div class="bg-gray-50 rounded-lg p-6 text-center">
            <p class="text-gray-500">No new validators yet.</p>
          </div>
        {:else}
          <div class="bg-white rounded-lg divide-y divide-gray-200">
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
      </div>
    </div>
    
    <!-- BUILDERS COLUMN CARD -->
    <div class="bg-orange-50/30 rounded-lg shadow-sm border border-orange-100 overflow-hidden">
      <!-- Column Header -->
      <div class="bg-orange-100/50 px-5 py-3 border-b border-orange-200">
        <button
          onclick={() => push('/builders')}
          class="text-lg font-semibold font-heading text-orange-700 uppercase tracking-wider hover:text-orange-800 transition-colors"
        >
          Builders
        </button>
      </div>
      
      <!-- Column Content -->
      <div class="p-4 space-y-6 sm:space-y-8">
      
      <!-- Total Builders Stat -->
      <div class="flex items-center">
        <div class="p-3 bg-orange-100 rounded-lg mr-4">
          <svg class="w-6 h-6 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
            <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
          </svg>
        </div>
        <div>
          <p class="text-sm text-gray-500">Total Builders</p>
          <p class="text-2xl font-bold text-gray-900">{statsLoading ? '...' : builderStats.total}</p>
        </div>
      </div>
      
      <!-- Top Builders -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-purple-100 rounded-lg">
              <svg class="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Top Builders</h2>
          </div>
          <button
            onclick={() => push('/builders/leaderboard')}
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
          category="builder"
          limit={5}
          entries={builderLeaderboard}
          loading={statsLoading}
        />
      </div>
      
      <!-- Featured Builders Contributions -->
      <div class="space-y-4 mt-6 sm:mt-10">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-yellow-100 rounded-lg">
              <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Featured Builders Contributions</h2>
          </div>
          <button
            onclick={() => push('/builders/contributions/highlights')}
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
          category="builder"
          cardStyle="highlight"
          limit={3}
        />
      </div>
      
      <!-- Newest Builders -->
      <div class="space-y-4 mt-6 sm:mt-10">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="p-1.5 bg-blue-100 rounded-lg">
              <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path>
              </svg>
            </div>
            <h2 class="text-lg font-semibold text-gray-900">Newest Builders</h2>
          </div>
          <button
            onclick={() => push('/builders/participants')}
            class="text-sm text-gray-500 hover:text-primary-600 transition-colors"
          >
            View all
            <svg class="inline-block w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
          </button>
        </div>
        
        {#if newestBuildersLoading}
          <div class="flex justify-center items-center p-8">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        {:else if newestBuilders.length === 0}
          <div class="bg-gray-50 rounded-lg p-6 text-center">
            <p class="text-gray-500">No new builders yet.</p>
          </div>
        {:else}
          <div class="bg-white rounded-lg divide-y divide-gray-200">
            {#each newestBuilders as builder}
              <div class="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors">
                <div class="flex items-center gap-3">
                  <Avatar 
                    user={builder}
                    size="sm"
                    clickable={true}
                  />
                  <div class="min-w-0">
                    <button
                      class="text-sm font-medium text-gray-900 hover:text-primary-600 transition-colors truncate"
                      onclick={() => push(`/participant/${builder.address}`)}
                    >
                      {builder.name || `${builder.address.slice(0, 6)}...${builder.address.slice(-4)}`}
                    </button>
                    <div class="text-xs text-gray-500">
                      {formatDate(builder.created_at)}
                    </div>
                  </div>
                </div>
                <button
                  onclick={() => push(`/participant/${builder.address}`)}
                  class="text-xs text-primary-600 hover:text-primary-700 font-medium flex-shrink-0"
                >
                  View →
                </button>
              </div>
            {/each}
          </div>
        {/if}
      </div>
      </div>
    </div>
  </div>
</div>