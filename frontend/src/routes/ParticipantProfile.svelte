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
  
  // Determine participant type
  let participantType = $derived(
    !participant ? null :
    participant.validator ? 'validator' :
    participant.builder ? 'builder' :
    participant.steward ? 'steward' :
    'participant'
  );
  
  // Get type-specific color theme
  let typeColor = $derived(
    participantType === 'validator' ? 'sky' :
    participantType === 'builder' ? 'orange' :
    participantType === 'steward' ? 'green' :
    'gray'
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
          <h1 class="text-2xl font-bold text-gray-900 flex items-center">
            {participant.name || (isValidatorOnly ? 'Validator' : 'Participant')} 
            {#if participantType && participantType !== 'participant'}
              <span class="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-{typeColor}-100 text-{typeColor}-800 capitalize">
                {participantType}
              </span>
            {/if}
            {#if !isValidatorOnly && participant.visible !== false && participantType !== 'steward'}
              <span class="ml-3 inline-flex items-center px-3 py-0.5 rounded-full text-sm font-medium bg-primary-100 text-primary-800">
                Rank #{participant.leaderboard_entry?.rank || 'N/A'}
              </span>
            {/if}
          </h1>
          {#if isValidatorOnly || participant.visible === false}
            <p class="mt-1 text-sm text-gray-500">
              {#if isValidatorOnly}
                This validator has not created an account yet
              {:else if participant.visible === false}
                This participant is not currently listed on the leaderboard
              {/if}
            </p>
          {/if}
        </div>
        <div class="flex gap-3">
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
          <a 
            href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${participant.address}`}
            target="_blank"
            rel="noopener noreferrer"
            class="px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center"
          >
            <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
            </svg>
            View in Explorer
          </a>
        </div>
      </div>
    </div>
    
    <!-- Main Information (Common for all) -->
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
          {#if !isValidatorOnly}
            <div class="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
              <dt class="text-sm font-medium text-gray-500">
                Joined
              </dt>
              <dd class="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                {formatDate(participant.created_at)}
              </dd>
            </div>
          {/if}
        </dl>
      </div>
    </div>
    
    <!-- Stats Cards (from upstream) -->
    {#if !isValidatorOnly && participantType !== 'steward'}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
      
      <!-- Journey Section for Own Profile -->
      {#if isOwnProfile}
        {#if (!participant.validator && !participant.has_validator_waitlist) || (!participant.builder && !participant.has_builder_welcome)}
          <div class="mb-6 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg p-6 text-white">
            <h3 class="text-lg font-semibold mb-3">Start Your Journey</h3>
            <p class="text-purple-100 mb-4">
              Begin your path to becoming a validator or builder and earn badges along the way!
            </p>
            <button
              onclick={() => push('/profile')}
              class="px-4 py-2 bg-white text-purple-600 rounded-md hover:bg-purple-50 transition-colors font-medium"
            >
              View Available Journeys →
            </button>
          </div>
        {/if}
      {/if}
      
      <!-- Profile Sections in Order: Validator, Builder-Welcome Journey, Validator-Waitlist Journey, Builder -->
      
      <!-- 1. Validator Profile (if active) -->
      {#if participant.validator}
        <!-- Validator section already exists below -->
      {/if}
      
      <!-- 2. Builder Welcome Journey Card -->
      {#if participant.has_builder_welcome && !participant.builder}
        <div class="mb-6 bg-gradient-to-r from-orange-50 to-orange-100 shadow rounded-lg p-6 border border-orange-300">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-orange-900 mb-2 flex items-center">
                <svg class="w-5 h-5 mr-2 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                Builder Journey
              </h3>
              <p class="text-sm text-orange-700">Welcome to the builder community! Keep deploying to level up.</p>
            </div>
            <div class="text-right">
              <div class="inline-flex items-center px-3 py-1 rounded-full bg-orange-200 text-orange-900 text-xs font-medium">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
                +20 Points
              </div>
            </div>
          </div>
        </div>
      {/if}
      
      <!-- 3. Validator Waitlist Journey Card -->
      {#if participant.has_validator_waitlist && !participant.validator}
        <div class="mb-6 bg-gradient-to-r from-sky-50 to-sky-100 shadow rounded-lg p-6 border border-sky-300">
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold text-sky-900 mb-2 flex items-center">
                <svg class="w-5 h-5 mr-2 text-sky-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
                </svg>
                Validator Journey
              </h3>
              <p class="text-sm text-sky-700">On the waitlist! Working towards becoming a validator.</p>
            </div>
            <div class="text-right">
              <div class="inline-flex items-center px-3 py-1 rounded-full bg-sky-200 text-sky-900 text-xs font-medium">
                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
                +20 Points
              </div>
            </div>
          </div>
        </div>
      {/if}
      
      <!-- 4. Builder Profile (if active) -->
      {#if participant.builder}
        <div class="mb-6 bg-orange-50/30 rounded-lg shadow-sm border border-orange-100 overflow-hidden">
          <!-- Header -->
          <div class="bg-orange-100/50 px-5 py-3 border-b border-orange-200">
            <h2 class="text-lg font-semibold text-orange-700 uppercase tracking-wider flex items-center">
              <svg class="w-5 h-5 mr-2 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
              </svg>
              Builder
            </h2>
          </div>
          
          <!-- Content -->
          <div class="p-4">
            <div class="text-sm text-orange-800">
              <p>Active builder on GenLayer!</p>
              {#if participant.builder?.total_points}
                <p class="mt-1">Total Points: <span class="font-bold text-orange-900">{participant.builder.total_points}</span></p>
              {/if}
              {#if participant.builder?.rank}
                <p>Builder Rank: <span class="font-bold text-orange-900">#{participant.builder.rank}</span></p>
              {/if}
            </div>
          </div>
        </div>
      {/if}
      
      <!-- Highlights Section -->
      <FeaturedContributions
        userId={participant.address}
        limit={5}
        title="Featured Contributions"
        cardStyle="highlight"
        showViewAll={false}
        className="mb-6"
        isOwnProfile={isOwnProfile}
        hideWhenEmpty={!isOwnProfile}
      />
    {/if}
    
    <!-- Steward Section -->
    {#if participant.steward}
      <div class="bg-green-50/30 rounded-lg shadow-sm border border-green-100 overflow-hidden mb-6">
        <!-- Header -->
        <div class="bg-green-100/50 px-5 py-3 border-b border-green-200">
          <h2 class="text-lg font-semibold text-green-700 uppercase tracking-wider flex items-center">
            <span class="mr-2">🌱</span>
            Ecosystem Steward
          </h2>
        </div>
        
        <!-- Content -->
        <div class="p-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Role Stat -->
            <div class="flex items-center">
              <div class="p-3 bg-green-100 rounded-lg mr-4">
                <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
                </svg>
              </div>
              <div>
                <p class="text-sm text-gray-500">Role</p>
                <p class="text-2xl font-bold text-gray-900">Admin</p>
              </div>
            </div>
            
            <!-- Since Date Stat -->
            {#if participant.steward?.created_at}
              <div class="flex items-center">
                <div class="p-3 bg-green-100 rounded-lg mr-4">
                  <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                  </svg>
                </div>
                <div>
                  <p class="text-sm text-gray-500">Steward Since</p>
                  <p class="text-2xl font-bold text-gray-900">{formatDate(participant.steward.created_at)}</p>
                </div>
              </div>
            {/if}
          </div>
        </div>
      </div>
    {/if}
    
    <!-- Validator Section -->
    {#if participant.validator}
      <div class="bg-sky-50/30 rounded-lg shadow-sm border border-sky-100 overflow-hidden mb-6">
        <!-- Header -->
        <div class="bg-sky-100/50 px-5 py-3 border-b border-sky-200">
          <h2 class="text-lg font-semibold text-sky-700 uppercase tracking-wider flex items-center">
            <svg class="w-5 h-5 mr-2 text-sky-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
            </svg>
            Testnet Validator
          </h2>
        </div>
        
        <!-- Content -->
        <div class="p-4">
          <!-- Stats Cards at the beginning -->
          {#if !isValidatorOnly}
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              <div class="bg-sky-50 rounded-lg p-4 border border-sky-200">
                <div class="flex items-center">
                  <div class="p-3 bg-sky-100 rounded-lg mr-4">
                    <svg class="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
                    </svg>
                  </div>
                  <div>
                    <p class="text-xs text-gray-500">Total Contributions</p>
                    <p class="text-2xl font-bold text-gray-900">{participant.validator?.total_contributions || 0}</p>
                  </div>
                </div>
              </div>
              
              <div class="bg-sky-50 rounded-lg p-4 border border-sky-200">
                <div class="flex items-center">
                  <div class="p-3 bg-sky-100 rounded-lg mr-4">
                    <svg class="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    </svg>
                  </div>
                  <div>
                    <p class="text-xs text-gray-500">Total Points</p>
                    <p class="text-2xl font-bold text-gray-900">{participant.validator?.total_points || 0}</p>
                  </div>
                </div>
              </div>
              
              <div class="bg-sky-50 rounded-lg p-4 border border-sky-200 sm:col-span-2 lg:col-span-1">
                <div class="flex items-center">
                  <div class="p-3 bg-sky-100 rounded-lg mr-4">
                    <svg class="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
                    </svg>
                  </div>
                  <div>
                    <p class="text-xs text-gray-500">Current Rank</p>
                    <p class="text-2xl font-bold text-gray-900">#{participant.validator?.rank || 'N/A'}</p>
                  </div>
                </div>
              </div>
            </div>
          {/if}
          
          <!-- Testnet Asimov Section -->
          <div class="mt-6">
            <h3 class="text-base font-semibold text-gray-900 mb-3">Testnet Asimov</h3>
            
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
              <!-- Status -->
              <div class="flex items-center">
                <div class="p-3 bg-sky-100 rounded-lg mr-4">
                  <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                  </svg>
                </div>
                <div>
                  <p class="text-sm text-gray-500">Status</p>
                  <ValidatorStatus address={participant.address} />
                </div>
              </div>
              
              <!-- Node Version -->
              <div class="flex items-start sm:col-span-2 lg:col-span-1">
                <div class="p-3 bg-sky-100 rounded-lg mr-4">
                  <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                  </svg>
                </div>
                <div class="flex-1 flex gap-6">
                  <div>
                    <p class="text-sm text-gray-500">Node Version</p>
                    {#if participant.validator?.node_version}
                      <div class="flex items-center gap-2">
                        <p class="text-xl sm:text-2xl font-bold text-gray-900 font-mono">{participant.validator.node_version}</p>
                        {#if participant.validator.matches_target}
                          <svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                          </svg>
                        {:else}
                          <svg class="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                          </svg>
                        {/if}
                      </div>
                    {:else}
                      <div class="flex items-center gap-2">
                        <svg class="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                        <p class="text-base text-gray-500">Not set</p>
                      </div>
                    {/if}
                  </div>
                  {#if participant.validator?.target_version}
                    <div>
                      <p class="text-xs text-gray-400">Target Version</p>
                      <p class="text-sm text-gray-500 font-mono">{participant.validator.target_version}</p>
                    </div>
                  {/if}
                </div>
              </div>
              
              <!-- Validator Since -->
              {#if participant.validator?.created_at}
                <div class="flex items-center">
                  <div class="p-3 bg-sky-100 rounded-lg mr-4">
                    <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                  </div>
                  <div>
                    <p class="text-sm text-gray-500">Validator Since</p>
                    <p class="text-2xl font-bold text-gray-900">{formatDate(participant.validator.created_at)}</p>
                  </div>
                </div>
              {/if}
            </div>
          </div>
        </div>
        
        <!-- Validator Stats and Contributions Section -->
        {#if !isValidatorOnly}
          <!-- Highlights Section -->
          <div class="px-4 mt-6">
            <FeaturedContributions
              userId={participant.address}
              limit={5}
              title="Featured Contributions"
              cardStyle="highlight"
              showViewAll={false}
              isOwnProfile={isOwnProfile}
              hideWhenEmpty={!isOwnProfile}
              category="validator"
            />
          </div>
          
          <!-- Contribution Types Breakdown -->
          {#if participant.validator?.contribution_types && participant.validator.contribution_types.length > 0}
            <div class="px-4 mt-6">
              <div class="mb-4">
                <h3 class="text-lg leading-6 font-medium text-gray-900">
                  Contribution Breakdown
                </h3>
                <p class="mt-1 text-sm text-gray-500">
                  Points distribution across contribution types
                </p>
              </div>
              
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {#each participant.validator.contribution_types as type}
                  <div class="bg-sky-50 border border-sky-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div class="flex flex-col h-full">
                      <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center gap-2 flex-1 min-w-0">
                          <div class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 bg-sky-500">
                            <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 6v12m6-6H6"></path>
                            </svg>
                          </div>
                          <h3 class="text-sm font-semibold text-gray-900 truncate">
                            <button
                              class="hover:text-sky-600 transition-colors"
                              onclick={() => push(`/contribution-type/${type.id}`)}
                            >
                              {type.name}
                            </button>
                          </h3>
                        </div>
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-sky-100 text-sky-800 ml-2 flex-shrink-0">
                          {type.total_points} pts
                        </span>
                      </div>
                      
                      <div class="text-xs text-gray-500 mb-2">
                        {#if type.count > 1}
                          × {type.count} contributions
                        {:else}
                          × 1 contribution
                        {/if}
                      </div>
                      
                      <div class="flex items-center gap-2 mt-auto">
                        <div class="flex-1 bg-gray-200 rounded-full h-2">
                          <div 
                            class="h-2 rounded-full transition-all duration-300"
                            class:bg-purple-500={type.percentage >= 40}
                            class:bg-blue-500={type.percentage >= 25 && type.percentage < 40}
                            class:bg-green-500={type.percentage >= 10 && type.percentage < 25}
                            class:bg-gray-400={type.percentage < 10}
                            style={`width: ${type.percentage}%`}
                          ></div>
                        </div>
                        <span class="text-xs text-gray-600 font-medium min-w-[2.5rem] text-right">
                          {type.percentage.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
          
          <!-- Contributions -->
          <div class="px-4 mt-6 pb-6">
            <UserContributions
              userAddress={participant.address}
              userName={participant.name || 'Validator'}
              category="validator"
            />
          </div>
        {/if}
      </div>
    {/if}
    
    {#if isValidatorOnly}
      <!-- Simple message for validators without accounts -->
      <div class="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6 text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <h3 class="mt-2 text-sm font-medium text-gray-900">No Account Found</h3>
        <p class="mt-1 text-sm text-gray-500">This validator has not created an account yet.</p>
      </div>
    {/if}
  {:else}
    <div class="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded">
      Participant not found
    </div>
  {/if}
</div>