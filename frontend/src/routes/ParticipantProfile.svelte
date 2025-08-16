<script>
  import { onMount } from 'svelte';
  import { push, querystring } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import UserContributions from '../components/UserContributions.svelte';
  import FeaturedContributions from '../components/FeaturedContributions.svelte';
  import StatCard from '../components/StatCard.svelte';
  import ValidatorStatus from '../components/ValidatorStatus.svelte';
  import { usersAPI, statsAPI, leaderboardAPI } from '../lib/api';
  import { authState } from '../lib/auth';
  import { getValidatorBalance } from '../lib/blockchain';
  
  // Import route params from svelte-spa-router
  import { params } from 'svelte-spa-router';
  
  // State management
  let participant = $state(null);
  let contributionStats = $state({
    totalContributions: 0,
    totalPoints: 0,
    averagePoints: 0,
    contributionTypes: []
  });
  let isValidatorOnly = $state(false); // Track if this is just a validator without user account
  
  let loading = $state(true);
  let error = $state(null);
  let statsError = $state(null);
  let successMessage = $state(null);
  let balance = $state(null);
  let loadingBalance = $state(false);
  
  // Check if this is the current user's profile
  let isOwnProfile = $derived(
    $authState.isAuthenticated && 
    participant?.address && 
    $authState.address?.toLowerCase() === participant.address.toLowerCase()
  );
  
  $effect(() => {
    const currentParams = $params;
    console.log("ParticipantProfile params:", currentParams);
    
    // Check for success message from profile update
    const savedMessage = sessionStorage.getItem('profileUpdateSuccess');
    if (savedMessage) {
      successMessage = savedMessage;
      sessionStorage.removeItem('profileUpdateSuccess');
      // Auto-hide success message after 3 seconds
      setTimeout(() => {
        successMessage = null;
      }, 3000);
    }
    
    if (currentParams && currentParams.address) {
      console.log("Using params.address:", currentParams.address);
      fetchParticipantData(currentParams.address);
    } else {
      console.log("No valid address found");
      error = "No valid wallet address provided";
      loading = false;
    }
  });
  
  async function fetchParticipantData(participantAddress) {
    try {
      loading = true;
      error = null;
      
      console.log("Fetching participant data for address:", participantAddress);
      
      // Fetch participant details
      const res = await usersAPI.getUserByAddress(participantAddress);
      console.log("Participant data received:", res.data);
      console.log("Leaderboard entry data:", res.data.leaderboard_entry);
      participant = res.data;
      
      // Fetch validator balance
      if (participant.address) {
        loadingBalance = true;
        try {
          balance = await getValidatorBalance(participant.address);
        } catch (err) {
          console.error('Failed to fetch balance:', err);
          // Don't show error, just leave balance as null
        } finally {
          loadingBalance = false;
        }
      }
      
      // Also try to fetch the leaderboard entry directly
      try {
        const leaderboardRes = await leaderboardAPI.getLeaderboardEntry(participantAddress);
        console.log("Leaderboard data received:", leaderboardRes.data);
        
        // If the leaderboard entry isn't included in the user data, add it
        if (!participant.leaderboard_entry && leaderboardRes.data.results && leaderboardRes.data.results.length > 0) {
          participant.leaderboard_entry = leaderboardRes.data.results[0];
          console.log("Added leaderboard entry from separate request:", participant.leaderboard_entry);
        }
      } catch (leaderboardError) {
        console.warn('Leaderboard API error:', leaderboardError);
      }
      
      // Fetch participant stats
      try {
        const statsRes = await statsAPI.getUserStats(participantAddress);
        if (statsRes.data) {
          contributionStats = statsRes.data;
          console.log("Stats data received:", statsRes.data);
        }
      } catch (statsError) {
        console.warn('Stats API error, will use basic data:', statsError);
        statsError = statsError.message || 'Failed to load participant statistics';
      }
      
      loading = false;
    } catch (err) {
      // Check if it's a 404 (user not found) - for validators without accounts
      if (err.response && err.response.status === 404) {
        // Create a minimal participant object for validators without accounts
        participant = {
          address: participantAddress,
          name: null,
          leaderboard_entry: {
            total_points: null,
            rank: null
          },
          created_at: null
        };
        isValidatorOnly = true;
        loading = false;
        error = null; // Clear the error since this is a valid state
      } else {
        error = err.message || 'Failed to load participant data';
        loading = false;
      }
    }
    
    // We've moved the contributions loading to the ContributionsList component
    // so we don't need to fetch them here anymore
  }
  
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
  
  // Icons for stat cards
  const icons = {
    contributions: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    points: 'M13 10V3L4 14h7v7l9-11h-7z',
    rank: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z'
  };
</script>

<div>
  <div class="mb-5">
    <a href="/" onclick={(e) => { e.preventDefault(); push('/'); }} class="text-primary-600 hover:text-primary-700">
      ← Back to Dashboard
    </a>
  </div>
  
  <!-- Success message -->
  {#if successMessage}
    <div class="bg-green-50 border-l-4 border-green-400 p-4 mb-6">
      <div class="flex">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <p class="text-sm text-green-700">
            {successMessage}
          </p>
        </div>
      </div>
    </div>
  {/if}
  
  <!-- Connection error message if needed -->
  {#if error || statsError}
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
  
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if participant}
    <div class="mb-6">
      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 flex items-center">
            {participant.name || (isValidatorOnly ? 'Validator' : 'Participant')} 
            {#if !isValidatorOnly && participant.visible !== false}
              <span class="ml-3 inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-primary-100 text-primary-800">
                Rank #{participant.leaderboard_entry?.rank || 'N/A'}
              </span>
            {/if}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            {#if isValidatorOnly}
              This validator has not created an account yet
            {:else if participant.visible === false}
              This participant is not currently listed on the leaderboard
            {:else}
              Wallet details and contributions
            {/if}
          </p>
        </div>
        {#if isOwnProfile}
          <button
            onclick={() => push('/profile')}
            class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 flex items-center"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
            </svg>
            Edit Profile
          </button>
        {/if}
      </div>
    </div>
    
    <!-- Explorer Button - Standalone -->
    <div class="mb-6">
      <a 
        href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${participant.address}`}
        target="_blank"
        rel="noopener noreferrer"
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
      >
        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
        </svg>
        View in Testnet Asimov Explorer
      </a>
    </div>
    
    <!-- Main Information -->
    <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
      <div class="border-t border-gray-200">
        <dl>
          {#if participant.address}
            <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Wallet Address
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2 font-mono">
                {participant.address}
              </dd>
            </div>
            <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Balance
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {#if loadingBalance}
                  <span class="text-gray-500">Loading balance...</span>
                {:else if balance}
                  <span class="font-mono">{balance.formatted} GEN</span>
                {:else}
                  <span class="text-gray-500">Unable to fetch balance</span>
                {/if}
              </dd>
            </div>
          {/if}
          {#if participant.validator?.node_version || participant.validator?.target_version}
            <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Node Version
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {#if participant.validator?.node_version}
                  <div class="flex items-center justify-between">
                    <span class="font-mono text-base font-semibold">{participant.validator.node_version}</span>
                    {#if participant.validator.matches_target}
                      <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800 border border-green-200">
                        <svg class="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                        </svg>
                        Up to date
                      </span>
                    {:else}
                      <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-amber-100 text-amber-800 border border-amber-200">
                        <svg class="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                        </svg>
                        Outdated
                      </span>
                    {/if}
                  </div>
                  {#if participant.validator.target_version && !participant.validator.matches_target}
                    <p class="mt-2 text-xs text-gray-600 bg-amber-50 rounded px-2 py-1 inline-block">
                      📍 Target: {participant.validator.target_version}
                    </p>
                  {/if}
                {:else if participant.validator?.target_version}
                  <div class="text-gray-500 italic">
                    Not set
                    <span class="ml-2 text-xs text-gray-400">(Target: {participant.validator.target_version})</span>
                  </div>
                {/if}
              </dd>
            </div>
          {/if}
          {#if !isValidatorOnly}
            <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Joined
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {formatDate(participant.created_at)}
              </dd>
            </div>
            <div class="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Total Points
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {participant.leaderboard_entry?.total_points ?? '—'}
              </dd>
            </div>
          {/if}
          {#if participant.address}
            <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Validator Status
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                <ValidatorStatus address={participant.address} />
              </dd>
            </div>
          {/if}
        </dl>
      </div>
    </div>
    
    {#if !isValidatorOnly}
      <!-- Stats Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <StatCard 
          title="Total Contributions" 
          value={contributionStats.totalContributions || 0} 
          icon={icons.contributions}
          color="green"
        />
        <StatCard 
          title="Total Points" 
          value={participant.leaderboard_entry?.total_points ?? '—'} 
          icon={icons.points}
          color="purple"
        />
        <StatCard 
          title="Current Rank" 
          value={participant.leaderboard_entry?.rank || 'N/A'} 
          icon={icons.rank}
          color="blue"
        />
      </div>
      
      <!-- Highlights Section -->
      <FeaturedContributions
        userId={participant.address}
        limit={5}
        title="Featured Contributions"
        cardStyle="highlight"
        showViewAll={false}
        className="mb-6"
      />
    {:else}
      <!-- Simple message for validators without accounts -->
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">No Account Found</h3>
        <p class="mt-1 text-sm text-gray-500">This validator has not created an account yet.</p>
      </div>
    {/if}
    
    
    
    <!-- Contribution Types Breakdown -->
    {#if !isValidatorOnly && contributionStats.contributionTypes && contributionStats.contributionTypes.length > 0}
      <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
        <div class="px-4 py-5 sm:px-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            Contribution Breakdown
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            Points by contribution type
          </p>
        </div>
        <div class="border-t border-gray-200">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Count
                  </th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Points
                  </th>
                  <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    % of Total
                  </th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {#each contributionStats.contributionTypes as type, i}
                  <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <a 
                        href={`/contribution-type/${type.id}`}
                        onclick={(e) => { e.preventDefault(); push(`/contribution-type/${type.id}`); }}
                        class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800 cursor-pointer hover:bg-green-200"
                      >
                        {type.name}
                      </a>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {type.count}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
                      {type.total_points}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="flex items-center">
                        <div class="w-full bg-gray-200 rounded-full h-2.5">
                          <div class="bg-primary-600 h-2.5 rounded-full" style={`width: ${type.percentage}%`}></div>
                        </div>
                        <span class="ml-2 text-sm text-gray-600">{type.percentage.toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    {/if}
    
    <!-- Contributions -->
    {#if !isValidatorOnly}
      <UserContributions
        userAddress={participant.address}
        userName={participant.name || 'Participant'}
      />
    {/if}
  {:else}
    <div class="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
      Participant not found
    </div>
  {/if}
</div>