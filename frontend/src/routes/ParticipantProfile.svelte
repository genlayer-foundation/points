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
  
  // Get role-based color theme for defaults
  let roleColorTheme = $derived(
    participant?.steward ? 'green' :
    participant?.validator ? 'sky' :
    participant?.builder ? 'orange' :
    participant?.has_validator_waitlist ? 'sky-waitlist' :
    participant?.has_builder_welcome ? 'orange-welcome' :
    'purple'
  );
  
  // Check if user is in transition (waitlist/welcome)
  let isInTransition = $derived(
    roleColorTheme === 'sky-waitlist' || roleColorTheme === 'orange-welcome'
  );
  
  // Get solid colors based on role
  let solidColor = $derived(
    roleColorTheme === 'green' ? 'bg-green-500' :
    roleColorTheme === 'sky' ? 'bg-sky-500' :
    roleColorTheme === 'orange' ? 'bg-orange-500' :
    roleColorTheme === 'sky-waitlist' ? 'bg-sky-400' :
    roleColorTheme === 'orange-welcome' ? 'bg-orange-400' :
    'bg-purple-500'
  );
  
  let avatarColor = $derived(
    roleColorTheme === 'green' ? 'bg-green-500' :
    roleColorTheme === 'sky' ? 'bg-sky-500' :
    roleColorTheme === 'orange' ? 'bg-orange-500' :
    roleColorTheme === 'sky-waitlist' ? 'bg-sky-400' :
    roleColorTheme === 'orange-welcome' ? 'bg-orange-400' :
    'bg-purple-500'
  );
  
  // Check if user has any role cards to display
  let hasAnyRole = $derived(
    participant && (
      participant.steward ||
      participant.validator ||
      participant.builder ||
      participant.has_validator_waitlist ||
      participant.has_builder_welcome
    )
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
    <!-- Profile Header with Banner and Avatar -->
    <div class="bg-white shadow rounded-lg overflow-hidden mb-6">
      <!-- Banner Image -->
      <div class="h-32 md:h-48 relative overflow-hidden">
        {#if participant.banner_image_url}
          <img 
            src={participant.banner_image_url} 
            alt="Profile banner" 
            class="w-full h-full object-cover"
          />
        {:else}
          <!-- Default banner with solid color -->
          <div class="w-full h-full {solidColor} relative">
            {#if isInTransition}
              <!-- Static stripes for waitlist/welcome users only -->
              <div class="absolute inset-0" style="
                background-image: repeating-linear-gradient(
                  45deg,
                  transparent 0,
                  transparent 20px,
                  rgba(255,255,255,0.3) 20px,
                  rgba(255,255,255,0.3) 40px
                );
              "></div>
            {/if}
          </div>
        {/if}
      </div>
      
      <!-- Profile Info Section -->
      <div class="relative px-4 sm:px-6 pb-6">
        <!-- Avatar -->
        <div class="-mt-12 sm:-mt-16 mb-4">
          <div class="inline-block">
            {#if participant.profile_image_url}
              <img 
                src={participant.profile_image_url} 
                alt={participant.name || 'Profile'} 
                class="w-24 h-24 sm:w-32 sm:h-32 rounded-full border-4 border-white shadow-lg object-cover"
              />
            {:else}
              <div class="w-24 h-24 sm:w-32 sm:h-32 rounded-full border-4 border-white shadow-lg {avatarColor} flex items-center justify-center relative overflow-hidden">
                {#if participant.name}
                  <span class="text-3xl sm:text-4xl font-bold text-white relative z-10">
                    {participant.name.charAt(0).toUpperCase()}
                  </span>
                {:else if participant.address}
                  <div class="relative">
                    <div class="absolute inset-0 flex items-center justify-center">
                      <div class="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-white/20"></div>
                    </div>
                    <div class="absolute inset-0 flex items-center justify-center">
                      <div class="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-white/20"></div>
                    </div>
                    <svg class="w-12 h-12 sm:w-16 sm:h-16 text-white relative z-10" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                    </svg>
                  </div>
                {:else}
                  <svg class="w-12 h-12 sm:w-16 sm:h-16 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                  </svg>
                {/if}
              </div>
            {/if}
          </div>
        </div>
        
        <!-- Name and Actions Row -->
        <div class="sm:flex sm:items-start sm:justify-between">
          <div class="mb-4 sm:mb-0">
            <h1 class="text-2xl font-bold text-gray-900">
              {participant.name || (isValidatorOnly ? 'Validator' : 'Participant')}
            </h1>
            {#if participant.address}
              <p class="text-sm text-gray-500 font-mono mt-1">
                {participant.address.slice(0, 6)}...{participant.address.slice(-4)}
              </p>
            {/if}
            {#if isValidatorOnly || participant.visible === false}
              <p class="mt-2 text-sm text-gray-500">
                {#if isValidatorOnly}
                  This validator has not created an account yet
                {:else if participant.visible === false}
                  This participant is not currently listed on the leaderboard
                {/if}
              </p>
            {/if}
          </div>
          
          <!-- Action Buttons -->
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
        
        <!-- Description -->
        {#if participant.description}
          <div class="mt-4">
            <p class="text-gray-700 whitespace-pre-wrap">
              {participant.description
                .split('\n')
                .map(line => line.trim())
                .filter(line => line !== '')
                .slice(0, 3)
                .join('\n')}
            </p>
          </div>
        {/if}
        
        <!-- Contact Links -->
        {#if participant.website || participant.twitter_handle || participant.discord_handle || participant.telegram_handle || participant.linkedin_handle}
          <div class="mt-4 flex flex-wrap gap-3">
            {#if participant.website}
              <a 
                href={participant.website} 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex items-center text-sm text-gray-600 hover:text-primary-600"
              >
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path>
                </svg>
                Website
              </a>
            {/if}
            {#if participant.twitter_handle}
              <a 
                href={`https://x.com/${participant.twitter_handle}`} 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex items-center text-sm text-gray-600 hover:text-primary-600"
              >
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                @{participant.twitter_handle}
              </a>
            {/if}
            {#if participant.discord_handle}
              <span class="inline-flex items-center text-sm text-gray-600">
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
                </svg>
                {participant.discord_handle}
              </span>
            {/if}
            {#if participant.telegram_handle}
              <a 
                href={`https://t.me/${participant.telegram_handle}`} 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex items-center text-sm text-gray-600 hover:text-primary-600"
              >
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M11.944 0A12 12 0 1 0 24 12a12 12 0 0 0-12.056-12zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/>
                </svg>
                @{participant.telegram_handle}
              </a>
            {/if}
            {#if participant.linkedin_handle}
              <a 
                href={`https://linkedin.com/in/${participant.linkedin_handle}`} 
                target="_blank" 
                rel="noopener noreferrer"
                class="inline-flex items-center text-sm text-gray-600 hover:text-primary-600"
              >
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                {participant.linkedin_handle}
              </a>
            {/if}
          </div>
        {/if}
      </div>
    </div>
    
    
    <!-- Welcome Section for Users Without Roles (Only show on own profile) -->
    {#if !hasAnyRole && !isValidatorOnly && isOwnProfile}
      <!-- Welcome Card with Everything Inside -->
      <div class="bg-white border border-gray-200 rounded-lg shadow-sm mb-6">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-2xl font-bold text-gray-900">Welcome to GenLayer Points</h2>
        </div>
        <div class="p-6">
          <p class="text-gray-700 font-medium mb-2">
            GenLayer Testnet Asimov is live.
          </p>
          <p class="text-gray-600 mb-6">
            Join professional validators and builders in testing the trust infrastructure for the AI age.
          </p>
          
          <!-- Three Info Sections Inside Card -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4 border-t border-gray-100 mb-6">
            <!-- Section 1: Select Your Journey -->
            <div class="flex items-center">
              <div class="flex items-center justify-center font-bold text-purple-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
                1
              </div>
              <div class="flex items-center justify-center w-10 h-10 bg-purple-100 rounded-lg flex-shrink-0">
                <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
                </svg>
              </div>
              <div class="flex-1 ml-2">
                <h3 class="font-semibold text-gray-900">Select Your Journey</h3>
                <p class="text-sm text-gray-600">Start contributing as a Builder or Validator</p>
              </div>
            </div>
            
            <!-- Section 2: Submit Contributions -->
            <div class="flex items-center">
              <div class="flex items-center justify-center font-bold text-green-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
                2
              </div>
              <div class="flex items-center justify-center w-10 h-10 bg-green-100 rounded-lg flex-shrink-0">
                <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                </svg>
              </div>
              <div class="flex-1 ml-2">
                <h3 class="font-semibold text-gray-900">Submit Contributions</h3>
                <p class="text-sm text-gray-600">Choose between many ways of contributing</p>
              </div>
            </div>
            
            <!-- Section 3: Climb the Ranks -->
            <div class="flex items-center">
              <div class="flex items-center justify-center font-bold text-yellow-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
                3
              </div>
              <div class="flex items-center justify-center w-10 h-10 bg-yellow-100 rounded-lg flex-shrink-0">
                <svg class="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                </svg>
              </div>
              <div class="flex-1 ml-2">
                <h3 class="font-semibold text-gray-900">Climb the Ranks</h3>
                <p class="text-sm text-gray-600">Earn points for each contribution and climb the ranks</p>
              </div>
            </div>
          </div>
          
          <!-- Journey Selection Cards Inside Welcome Card -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 border-t border-gray-100">
            <!-- Validator Journey Card -->
            <div class="group relative bg-sky-50 border-2 border-sky-200 rounded-xl overflow-hidden hover:shadow-lg transition-all">
              <div class="absolute inset-0 bg-sky-100 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div class="relative p-6">
            <div class="flex items-center mb-4">
              <div class="flex items-center justify-center w-12 h-12 bg-sky-500 rounded-full mr-4 flex-shrink-0">
                <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
                </svg>
              </div>
              <div>
                <h3 class="text-xl font-bold text-sky-900 mb-1">Validator Journey</h3>
                <p class="text-sky-700 text-sm">Validate and judge subjective Intelligent Contracts on Testnet Asimov</p>
              </div>
            </div>
            <ul class="space-y-2 mb-6">
              <li class="flex items-center text-sm text-sky-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Participate in Optimistic Democracy consensus with professional validators
              </li>
              <li class="flex items-center text-sm text-sky-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Validate subjective outcomes in Intelligent Contracts with AI-powered validation
              </li>
              <li class="flex items-center text-sm text-sky-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Currently only selected validators can participate - earn your slot
              </li>
            </ul>
            <button
              onclick={() => push('/profile')}
              class="w-full flex items-center justify-center px-4 py-3 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors font-semibold group-hover:shadow-md"
            >
              <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
              </svg>
              Join the Waitlist
            </button>
          </div>
        </div>
        
        <!-- Builder Journey Card -->
        <div class="group relative bg-orange-50 border-2 border-orange-200 rounded-xl overflow-hidden hover:shadow-lg transition-all">
          <div class="absolute inset-0 bg-orange-100 opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div class="relative p-6">
            <div class="flex items-center mb-4">
              <div class="flex items-center justify-center w-12 h-12 bg-orange-500 rounded-full mr-4 flex-shrink-0">
                <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                </svg>
              </div>
              <div>
                <h3 class="text-xl font-bold text-orange-900 mb-1">Builder Journey</h3>
                <p class="text-orange-700 text-sm">Deploy smart contracts, build dApps, and contribute to the GenLayer ecosystem</p>
              </div>
            </div>
            <ul class="space-y-2 mb-6">
              <li class="flex items-center text-sm text-orange-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Deploy smart contracts
              </li>
              <li class="flex items-center text-sm text-orange-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Build innovative dApps
              </li>
              <li class="flex items-center text-sm text-orange-600">
                <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                Access developer resources
              </li>
            </ul>
            <button
              onclick={() => push('/profile')}
              class="w-full flex items-center justify-center px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-semibold group-hover:shadow-md"
            >
              <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
              </svg>
              Start Building
            </button>
              </div>
            </div>
          </div>
        </div>
      </div>
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
    
    <!-- Validator Waitlist Card -->
    {#if participant.has_validator_waitlist && !participant.validator}
      <div class="bg-sky-50 rounded-lg shadow-sm border border-sky-200 overflow-hidden mb-6">
        <!-- Header -->
        <div class="bg-sky-100 px-5 py-3 border-b border-sky-200">
          <h2 class="text-lg font-semibold text-sky-700 uppercase tracking-wider flex items-center">
            <svg class="w-5 h-5 mr-2 text-sky-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
            </svg>
            Validator Waitlist
          </h2>
        </div>
        
        <!-- Content -->
        <div class="p-6">
          <!-- Featured Section -->
          <FeaturedContributions
            userId={participant.address}
            limit={3}
            title="Featured"
            cardStyle="compact"
            showViewAll={false}
            isOwnProfile={isOwnProfile}
            hideWhenEmpty={false}
          />
          
          <!-- Contribution Breakdown -->
          {#if contributionStats.contributionTypes && contributionStats.contributionTypes.length > 0}
            <div class="mt-6">
              <h3 class="text-base font-semibold text-gray-900 mb-3">Breakdown</h3>
              <div class="space-y-2">
                {#each contributionStats.contributionTypes as type}
                  <div class="flex justify-between items-center py-2 border-b border-gray-100">
                    <span class="text-sm text-gray-700">{type.name}</span>
                    <span class="text-sm font-medium text-gray-900">{type.total_points} pts</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
          
          <!-- Contributions List -->
          <div class="mt-6">
            <UserContributions
              userAddress={participant.address}
              userName={participant.name || 'Participant'}
              compact={true}
            />
          </div>
        </div>
      </div>
    {/if}
    
    <!-- Builder Welcome Card -->
    {#if participant.has_builder_welcome && !participant.builder}
      <div class="bg-orange-50 rounded-lg shadow-sm border border-orange-200 overflow-hidden mb-6">
        <!-- Header -->
        <div class="bg-orange-100 px-5 py-3 border-b border-orange-200">
          <h2 class="text-lg font-semibold text-orange-700 uppercase tracking-wider flex items-center">
            <svg class="w-5 h-5 mr-2 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
            </svg>
            Builder Welcome
          </h2>
        </div>
        
        <!-- Content -->
        <div class="p-6">
          <p class="text-orange-700 mb-4">Welcome to the builder community! Deploy contracts to level up.</p>
          <div class="inline-flex items-center px-3 py-1 rounded-full bg-orange-200 text-orange-900 text-sm font-medium">
            <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
            +20 Points Earned
          </div>
        </div>
      </div>
    {/if}
    
    <!-- Builder Card -->
    {#if participant.builder}
      <div class="bg-orange-50 rounded-lg shadow-sm border border-orange-200 overflow-hidden mb-6">
        <!-- Header -->
        <div class="bg-orange-100 px-5 py-3 border-b border-orange-200">
          <h2 class="text-lg font-semibold text-orange-700 uppercase tracking-wider flex items-center">
            <svg class="w-5 h-5 mr-2 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
              <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
            </svg>
            Builder
          </h2>
        </div>
        
        <!-- Content -->
        <div class="p-6">
          <!-- Stats Row -->
          <div class="grid grid-cols-3 gap-4 mb-6">
            <div>
              <p class="text-xs text-gray-500">Total Contributions</p>
              <p class="text-2xl font-bold text-gray-900">{participant.builder?.total_contributions || 0}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Total Points</p>
              <p class="text-2xl font-bold text-gray-900">{participant.builder?.total_points || 0}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Builder Rank</p>
              <p class="text-2xl font-bold text-gray-900">#{participant.builder?.rank || 'N/A'}</p>
            </div>
          </div>
          
          <!-- Featured Section -->
          <FeaturedContributions
            userId={participant.address}
            limit={3}
            title="Featured"
            cardStyle="compact"
            showViewAll={false}
            isOwnProfile={isOwnProfile}
            hideWhenEmpty={false}
            category="builder"
          />
          
          <!-- Contributions -->
          <div class="mt-6">
            <UserContributions
              userAddress={participant.address}
              userName={participant.name || 'Builder'}
              category="builder"
              compact={true}
            />
          </div>
        </div>
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