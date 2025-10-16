<script>
  import { onMount } from 'svelte';
  import { push, querystring } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import RecentContributions from '../components/RecentContributions.svelte';
  import FeaturedContributions from '../components/FeaturedContributions.svelte';
  import ValidatorStatus from '../components/ValidatorStatus.svelte';
  import ProfileStats from '../components/ProfileStats.svelte';
  import ContributionBreakdown from '../components/ContributionBreakdown.svelte';
  import BuilderProgress from '../components/BuilderProgress.svelte';
  import ReferralSection from '../components/ReferralSection.svelte';
  import Icons from '../components/Icons.svelte';
  import Tooltip from '../components/Tooltip.svelte';
  import { usersAPI, statsAPI, leaderboardAPI, journeyAPI, creatorAPI, getCurrentUser } from '../lib/api';
  import { authState } from '../lib/auth';
  import { getValidatorBalance } from '../lib/blockchain';
  import Avatar from '../components/Avatar.svelte';
  import { showSuccess, showWarning } from '../lib/toastStore';

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
  let validatorStats = $state({
    totalContributions: 0,
    totalPoints: 0,
    averagePoints: 0,
    contributionTypes: []
  });
  let builderStats = $state({
    totalContributions: 0,
    totalPoints: 0,
    averagePoints: 0,
    contributionTypes: []
  });
  let isValidatorOnly = $state(false); // Track if this is just a validator without user account
  
  let loading = $state(true);
  let error = $state(null);
  let statsError = $state(null);
  let balance = $state(null);
  let testnetBalance = $state(null);
  let loadingBalance = $state(false);
  let hasDeployedContract = $state(false);
  let isRefreshingBalance = $state(false);
  let isClaimingBuilderBadge = $state(false);
  let hasCalledComplete = $state(false);
  let referralData = $state(null);
  let loadingReferrals = $state(false);

  // Check if this is the current user's profile
  let isOwnProfile = $derived(
    $authState.isAuthenticated && 
    participant?.address && 
    $authState.address?.toLowerCase() === participant.address.toLowerCase()
  );
  
  // Derived states for builder requirements
  let requirement1Met = $derived(participant?.has_builder_welcome || false);
  let requirement2Met = $derived(testnetBalance > 0);
  let allRequirementsMet = $derived(requirement1Met && requirement2Met);
  
  // Auto-complete journey when all requirements are met
  $effect(() => {
    if (allRequirementsMet && !hasCalledComplete && isOwnProfile && !participant?.builder) {
      hasCalledComplete = true;
      completeBuilderJourney();
    }
  });
  
  // Determine participant type
  let participantType = $derived(
    !participant ? null :
    participant.validator ? 'validator' :
    participant.builder ? 'builder' :
    participant.steward ? 'steward' :
    participant.creator ? 'creator' :
    'participant'
  );
  
  // Get type-specific color theme
  let typeColor = $derived(
    participantType === 'validator' ? 'sky' :
    participantType === 'builder' ? 'orange' :
    participantType === 'steward' ? 'green' :
    participantType === 'creator' ? 'purple' :
    'gray'
  );
  
  // Get role-based color theme for defaults
  let roleColorTheme = $derived(
    participant?.steward ? 'green' :
    participant?.validator ? 'sky' :
    participant?.builder ? 'orange' :
    participant?.creator ? 'purple' :
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
      participant.creator ||
      participant.has_validator_waitlist ||
      participant.has_builder_welcome
    )
  );

  // Check if user is ONLY a creator (no other roles)
  let isCreatorOnly = $derived(
    participant?.creator &&
    !participant.steward &&
    !participant.validator &&
    !participant.builder &&
    !participant.has_validator_waitlist &&
    !participant.has_builder_welcome
  );
  
  $effect(() => {
    const currentParams = $params;
    console.log("ParticipantProfile params:", currentParams);

    // Check for success message from profile update
    const savedMessage = sessionStorage.getItem('profileUpdateSuccess');
    if (savedMessage) {
      showSuccess(savedMessage);
      sessionStorage.removeItem('profileUpdateSuccess');
    }

    // Check for builder journey success
    const builderSuccess = sessionStorage.getItem('builderJourneySuccess');
    if (builderSuccess === 'true') {
      showSuccess('Congratulations! 🎉 You are now a GenLayer Builder! Your Builder profile has been created and you can start contributing to the ecosystem.');
      sessionStorage.removeItem('builderJourneySuccess');
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

  // Also check on mount to ensure we catch the notification
  onMount(() => {
    const builderSuccess = sessionStorage.getItem('builderJourneySuccess');
    if (builderSuccess === 'true') {
      showSuccess('Congratulations! 🎉 You are now a GenLayer Builder! Your Builder profile has been created and you can start contributing to the ecosystem.');
      sessionStorage.removeItem('builderJourneySuccess');
    }
  });

  // Show warning toast when there are connection issues
  $effect(() => {
    if (statsError && !loading) {
      showWarning('Having trouble connecting to the API. Some data might not display correctly.');
    }
  });


  async function refreshBalance() {
    if (!participant?.address) {
      return;
    }
    
    isRefreshingBalance = true;
    try {
      const result = await getValidatorBalance(participant.address);
      testnetBalance = parseFloat(result.formatted);
    } catch (err) {
      console.error('Failed to refresh balance:', err);
      testnetBalance = 0;
    } finally {
      isRefreshingBalance = false;
    }
  }

  async function fetchReferrals() {
    if (loadingReferrals) {
      return;
    }

    loadingReferrals = true;
    try {
      if (isOwnProfile) {
        // For own profile, use authenticated endpoint
        const response = await usersAPI.getReferrals();
        referralData = response.data;
      } else if (participant?.referral_details) {
        // For other profiles, use data already in participant object
        referralData = participant.referral_details;
      }
    } catch (err) {
      console.error('Failed to fetch referrals:', err);
      referralData = null;
    } finally {
      loadingReferrals = false;
    }
  }
  
  async function claimBuilderWelcome() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }
    
    isClaimingBuilderBadge = true;
    
    try {
      await journeyAPI.startBuilderJourney();
      // Reload user data to get updated contribution status
      const updatedUser = await getCurrentUser();
      participant = updatedUser;
    } catch (err) {
      console.error('Failed to claim builder contribution:', err);
    } finally {
      isClaimingBuilderBadge = false;
    }
  }
  
  async function startCreatorJourney() {
    if (!$authState.isAuthenticated) {
      return;
    }

    // Clear any existing error states
    error = null;
    successMessage = '';

    try {
      const response = await creatorAPI.joinAsCreator();

      // If successful, reload the user data
      if (response.status === 201 || response.status === 200) {
        // Show a success message
        successMessage = 'You are now a Supporter! Start growing the community through referrals.';

        // Reload participant data to get Supporter profile (same pattern as Builder)
        const updatedUser = await getCurrentUser();
        participant = updatedUser;

        // Auto-hide success message after 5 seconds
        setTimeout(() => {
          successMessage = '';
        }, 5000);
      }
    } catch (err) {
      console.error('Error joining as creator:', err);
      error = err.response?.data?.message || 'Failed to join as supporter';
      successMessage = '';
    }
  }

  async function completeBuilderJourney() {
    if (!$authState.isAuthenticated || !allRequirementsMet) {
      return;
    }

    try {
      const response = await journeyAPI.completeBuilderJourney();

      // If successful, show success notification and reload data
      if (response.status === 201 || response.status === 200) {
        showSuccess('Congratulations! 🎉 You are now a GenLayer Builder! Your Builder profile has been created and you can start contributing to the ecosystem.');

        // Reload participant data to get Builder profile
        const updatedUser = await getCurrentUser();
        participant = updatedUser;
      }
    } catch (err) {
      // If already has the contribution and Builder profile
      if (err.response?.status === 200) {
        // Still reload data
        const updatedUser = await getCurrentUser();
        participant = updatedUser;
      } else {
        console.error('Failed to complete builder journey:', err);
        // Reset flag to allow retry
        hasCalledComplete = false;
      }
    }
  }

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
      
      // Set loading to false immediately to show UI progressively
      loading = false;
      
      // Fetch balance asynchronously (don't block UI)
      if (participant.address) {
        loadingBalance = true;
        getValidatorBalance(participant.address).then(result => {
          balance = result;
          loadingBalance = false;
        }).catch(err => {
          console.error('Failed to fetch balance:', err);
          loadingBalance = false;
          // Don't show error, just leave balance as null
        });
      }
      
      // Fetch leaderboard entry asynchronously
      leaderboardAPI.getLeaderboardEntry(participantAddress).then(leaderboardRes => {
        console.log("Leaderboard data received:", leaderboardRes.data);
        
        // Store all leaderboard entries (user can be on multiple leaderboards)
        if (leaderboardRes.data && Array.isArray(leaderboardRes.data)) {
          participant.leaderboard_entries = leaderboardRes.data;
          
          // Find the waitlist entry if they're on the waitlist
          participant.waitlist_entry = leaderboardRes.data.find(entry => 
            entry.type === 'validator-waitlist'
          );
          
          // Find the validator entry if they're a validator
          participant.validator_entry = leaderboardRes.data.find(entry => 
            entry.type === 'validator'
          );
          
          console.log("Added leaderboard entries from separate request:", participant.leaderboard_entries);
          console.log("Waitlist entry:", participant.waitlist_entry);
          console.log("Validator entry:", participant.validator_entry);
        }
      }).catch(leaderboardError => {
        console.warn('Leaderboard API error:', leaderboardError);
      });
      
      // Fetch participant stats asynchronously
      statsAPI.getUserStats(participantAddress).then(statsRes => {
        if (statsRes.data) {
          contributionStats = statsRes.data;
          console.log("Stats data received:", statsRes.data);
        }
      }).catch(statsError => {
        console.warn('Stats API error, will use basic data:', statsError);
        statsError = statsError.message || 'Failed to load participant statistics';
      });
      
      // Fetch validator-specific stats if user has validator waitlist
      if (participant.has_validator_waitlist) {
        statsAPI.getUserStats(participantAddress, 'validator').then(validatorStatsRes => {
          if (validatorStatsRes.data) {
            validatorStats = validatorStatsRes.data;
            console.log("Validator stats data received:", validatorStatsRes.data);
          }
        }).catch(error => {
          console.warn('Validator stats API error:', error);
        });
      }
      
      // Fetch builder-specific stats if user has builder welcome
      if (participant.has_builder_welcome) {
        statsAPI.getUserStats(participantAddress, 'builder').then(builderStatsRes => {
          if (builderStatsRes.data) {
            builderStats = builderStatsRes.data;
            console.log("Builder stats data received:", builderStatsRes.data);
          }
        }).catch(error => {
          console.warn('Builder stats API error:', error);
        });
      }

      // Fetch referral data for all profiles
      fetchReferrals();

      // Load additional data asynchronously for own profile
      if (isOwnProfile) {

        if (participant.has_builder_welcome) {
          // Check testnet balance asynchronously
          getValidatorBalance(participant.address).then(result => {
            testnetBalance = parseFloat(result.formatted);
          }).catch(err => {
            console.error('Failed to check testnet balance:', err);
            testnetBalance = 0;
          });

          // Check for contract deployments asynchronously
          usersAPI.getDeploymentStatus().then(deploymentResult => {
            hasDeployedContract = deploymentResult.data.has_deployments || false;
          }).catch(err => {
            console.error('Failed to check deployments:', err);
            hasDeployedContract = false;
          });
        }
      }
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
    <div class="bg-white shadow rounded-lg mb-6">
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
          <div class="w-full h-full {solidColor}">
          </div>
        {/if}
      </div>
      
      <!-- Profile Info Section -->
      <div class="relative px-4 sm:px-6 pb-6" style="overflow: visible;">
        <!-- Avatar -->
        <div class="-mt-12 sm:-mt-16 mb-4">
          <Avatar 
            user={participant}
            size="3xl"
            showBorder={true}
            className=""
          />
        </div>
        
        <!-- Name and Actions Row -->
        <div class="sm:flex sm:items-start sm:justify-between">
          <div class="mb-4 sm:mb-0">
            <!-- Name with badges inline -->
            <div class="flex items-center flex-wrap gap-2">
              <h1 class="text-2xl font-bold text-gray-900">
                {participant.name || (isValidatorOnly ? 'Validator' : 'Participant')}
              </h1>
              
              <!-- Badges next to name -->
              {#if participant.steward || participant.validator || participant.builder || participant.creator || participant.has_validator_waitlist || participant.has_builder_welcome}
                {#if participant.steward}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Steward
                  </span>
                {/if}
                {#if participant.validator}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-100 text-sky-800">
                    Validator
                  </span>
                {:else if participant.has_validator_waitlist}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-sky-50 text-sky-700 border border-sky-200">
                    Validator Waitlist
                  </span>
                {/if}
                {#if participant.builder}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                    Builder
                  </span>
                {:else if participant.has_builder_welcome}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200">
                    Builder Welcome
                  </span>
                {/if}
                {#if participant.creator}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                    Supporter
                  </span>
                {/if}
              {/if}
            </div>
            
            {#if participant.address}
              <!-- Address with copy button and referral link -->
              <div class="flex items-center gap-2 mt-2" style="overflow: visible;">
                <code class="text-sm text-gray-600 font-mono">
                  {participant.address.substring(0, 6)}...{participant.address.substring(participant.address.length - 4)}
                </code>
                <button
                  onclick={() => {
                    navigator.clipboard.writeText(participant.address);
                    showSuccess('Address copied to clipboard!');
                  }}
                  title="Copy address"
                  class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                  </svg>
                </button>
                
                <!-- Referral Section for own profile -->
                {#if isOwnProfile}
                  <div class="ml-2">
                    <ReferralSection />
                  </div>
                {/if}
              </div>
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
        {#if participant.website || participant.twitter_handle || participant.discord_handle || participant.telegram_handle || participant.linkedin_handle || participant.github_username}
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
            {#if participant.github_username}
              <a
                href={`https://github.com/${participant.github_username}`}
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center text-sm text-gray-600 hover:text-primary-600"
              >
                <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
                </svg>
                {participant.github_username}
              </a>
            {/if}
          </div>
        {/if}
      </div>
    </div>
    
    <!-- Metrics Container -->
    {#if !isValidatorOnly}
      <!-- Balance and Joined Date in a row -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <!-- Balance Card -->
        <div class="bg-white shadow rounded-lg p-4">
          <div class="flex items-center">
            <div class="flex-shrink-0 p-2.5 rounded-lg mr-3 bg-green-50 text-green-500">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-sm text-gray-500">Balance</p>
              <div class="flex items-center">
                {#if loadingBalance}
                  <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-green-600 mr-2"></div>
                  <span class="text-gray-500">Loading...</span>
                {:else if balance}
                  <Tooltip tooltipText="Asimov Testnet Tokens are valueless faucet tokens for testing only and provide no right or expectation of profit or redemption.">
                    {#snippet children()}
                      <p class="text-xl font-bold text-gray-900 cursor-help">
                        {balance.formatted} GEN<sup class="text-red-500">*</sup>
                      </p>
                    {/snippet}
                  </Tooltip>
                {:else}
                  <Tooltip tooltipText="Asimov Testnet Tokens are valueless faucet tokens for testing only and provide no right or expectation of profit or redemption.">
                    {#snippet children()}
                      <p class="text-xl font-bold text-gray-900 cursor-help">
                        0 GEN<sup class="text-red-500">*</sup>
                      </p>
                    {/snippet}
                  </Tooltip>
                {/if}
              </div>
            </div>
          </div>
        </div>

        <!-- Joined Date Card -->
        {#if participant.created_at}
          <div class="bg-white shadow rounded-lg p-4">
            <div class="flex items-center">
              <div class="flex-shrink-0 p-2.5 rounded-lg mr-3 bg-blue-50 text-blue-500">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
              </div>
              <div class="flex-1">
                <p class="text-sm text-gray-500">Joined</p>
                <p class="text-xl font-bold text-gray-900">
                  {new Date(participant.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                </p>
              </div>
            </div>
          </div>
        {/if}
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
            <div class="mb-6">
              <ProfileStats
                contributions={participant.validator?.total_contributions || 0}
                points={participant.validator?.total_points || 0}
                rank={participant.validator_entry?.rank || participant.validator?.rank}
                colorTheme="sky"
              />
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
              colorTheme="sky"
            />
          </div>
          
          <!-- Contribution Types Breakdown -->
          {#if participant.validator?.contribution_types && participant.validator.contribution_types.length > 0}
            <div class="px-4 mt-6">
              <ContributionBreakdown
                contributionTypes={participant.validator.contribution_types}
                colorTheme="sky"
                userAddress={participant.address}
              />
            </div>
          {/if}
          
          <!-- Contributions -->
          <div class="px-4 mt-6 pb-6">
            <RecentContributions
              title="Recent Contributions"
              limit={5}
              userId={participant.address}
              category="validator"
              showHeader={true}
              showViewAll={true}
              viewAllPath={`/all-contributions?user=${participant.address}&category=validator`}
              viewAllText="View All →"
            />
          </div>
        {/if}
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
          <!-- Stats -->
          <div class="mb-6">
            <ProfileStats
              contributions={participant.builder?.total_contributions || 0}
              points={participant.builder?.total_points || 0}
              rank={participant.builder?.rank}
              colorTheme="orange"
            />
          </div>
          
          <!-- Featured Section -->
          <FeaturedContributions
            userId={participant.address}
            limit={3}
            title="Featured"
            cardStyle="compact"
            showViewAll={false}
            isOwnProfile={isOwnProfile}
            hideWhenEmpty={!isOwnProfile}
            category="builder"
            colorTheme="orange"
          />
          
          <!-- Contribution Breakdown -->
          {#if participant.builder?.contribution_types && participant.builder.contribution_types.length > 0}
            <div class="mt-6">
              <ContributionBreakdown
                contributionTypes={participant.builder.contribution_types}
                colorTheme="orange"
                userAddress={participant.address}
              />
            </div>
          {/if}
          
          <!-- Contributions -->
          <div class="mt-6">
            <RecentContributions
              title="Recent Contributions"
              limit={5}
              userId={participant.address}
              category="builder"
              showHeader={true}
              showViewAll={true}
              viewAllPath={`/all-contributions?user=${participant.address}&category=builder`}
              viewAllText="View All →"
            />
          </div>
        </div>
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
          <!-- Stats -->
          <div class="mb-4">
            <ProfileStats
              contributions={validatorStats.totalContributions || 0}
              points={validatorStats.totalPoints || 20}
              rank={participant.waitlist_entry?.rank || participant.has_validator_waitlist?.rank}
              colorTheme="sky"
            />
          </div>
          
          <!-- Call to Action -->
          {#if isOwnProfile}
            <div class="bg-sky-50 border-l-4 border-sky-400 px-4 py-3 mb-6">
              <div class="flex items-center">
                <svg class="h-5 w-5 text-sky-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
                </svg>
                <p class="text-sm font-medium text-sky-800">
                  Climb the ranks and get invited to validate on Testnet Asimov
                </p>
              </div>
            </div>
          {/if}
          
          <!-- Featured Section -->
          <FeaturedContributions
            userId={participant.address}
            limit={3}
            title="Featured"
            cardStyle="compact"
            showViewAll={false}
            isOwnProfile={isOwnProfile}
            hideWhenEmpty={!isOwnProfile}
            category="validator"
            colorTheme="sky"
          />
          
          <!-- Contribution Breakdown -->
          {#if validatorStats.contributionTypes && validatorStats.contributionTypes.length > 0}
            <div class="mt-6">
              <ContributionBreakdown
                contributionTypes={validatorStats.contributionTypes}
                colorTheme="sky"
                userAddress={participant.address}
              />
            </div>
          {/if}
          
          <!-- Contributions List -->
          <div class="mt-6">
            <RecentContributions
              title="Recent Contributions"
              limit={5}
              userId={participant.address}
              category="validator"
              showHeader={true}
              showViewAll={true}
              viewAllPath={`/all-contributions?user=${participant.address}&category=validator`}
              viewAllText="View All →"
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
          <!-- Welcome message and requirements -->
          {#if isOwnProfile}
            <div class="mb-6">
              <BuilderProgress 
                testnetBalance={testnetBalance}
                hasBuilderWelcome={participant?.has_builder_welcome || false}
                hasDeployedContract={hasDeployedContract}
                showActions={true}
                colorTheme="orange"
                onClaimBuilderBadge={claimBuilderWelcome}
                isClaimingBuilderBadge={isClaimingBuilderBadge}
                onRefreshBalance={refreshBalance}
                isRefreshingBalance={isRefreshingBalance}
              />
            </div>
          {:else}
            <p class="text-orange-700 mb-4">Building amazing things on GenLayer!</p>
          {/if}
          
          <!-- Stats -->
          <div class="mb-6">
            <ProfileStats
              contributions={builderStats.totalContributions || 0}
              points={builderStats.totalPoints || 20}
              rank={participant.has_builder_welcome?.rank}
              colorTheme="orange"
            />
          </div>
          
          <!-- Featured Section -->
          <FeaturedContributions
            userId={participant.address}
            limit={3}
            title="Featured"
            cardStyle="compact"
            showViewAll={false}
            isOwnProfile={isOwnProfile}
            hideWhenEmpty={!isOwnProfile}
            category="builder"
            colorTheme="orange"
          />
          
          <!-- Contribution Breakdown -->
          {#if builderStats.contributionTypes && builderStats.contributionTypes.length > 0}
            <div class="mt-6">
              <ContributionBreakdown
                contributionTypes={builderStats.contributionTypes}
                colorTheme="orange"
                userAddress={participant.address}
              />
            </div>
          {/if}
          
          <!-- Contributions List -->
          <div class="mt-6">
            <RecentContributions
              title="Recent Contributions"
              limit={5}
              userId={participant.address}
              category="builder"
              showHeader={true}
              showViewAll={true}
              viewAllPath={`/all-contributions?user=${participant.address}&category=builder`}
              viewAllText="View All →"
            />
          </div>
        </div>
      </div>
    {/if}

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
            <!-- Builder Journey Card -->
            <div class="group relative bg-orange-50 border-2 border-orange-200 rounded-xl overflow-hidden hover:shadow-lg transition-all flex flex-col">
              <div class="absolute inset-0 bg-orange-100 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div class="relative p-6 flex flex-col flex-1">
                <div class="flex items-center mb-4">
                  <div class="flex items-center justify-center w-12 h-12 bg-orange-500 rounded-full mr-4 flex-shrink-0">
                    <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                    </svg>
                  </div>
                  <div>
                    <h3 class="text-xl font-bold text-orange-900 mb-1">Builder Journey</h3>
                    <p class="text-orange-700 text-sm">Learn GenLayer's basics and deploy your first Intelligent Contract powered by Optimistic Democracy</p>
                  </div>
                </div>
                <ul class="space-y-2 mb-6 flex-1">
                  <li class="flex items-center text-sm text-orange-600">
                    <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    Explore the Studio and docs
                  </li>
                  <li class="flex items-center text-sm text-orange-600">
                    <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    Learn Intelligent Contracts fundamentals
                  </li>
                  <li class="flex items-center text-sm text-orange-600">
                    <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    Deploy, contribute and become a GenLayer Builder
                  </li>
                </ul>
                <button
                  onclick={() => push('/builders/welcome')}
                  class="w-full flex items-center justify-center px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors font-semibold group-hover:shadow-md mt-auto"
                >
                  <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                  </svg>
                  Start Building
                </button>
              </div>
            </div>
            
            <!-- Validator Journey Card -->
            <div class="group relative bg-sky-50 border-2 border-sky-200 rounded-xl overflow-hidden hover:shadow-lg transition-all flex flex-col">
              <div class="absolute inset-0 bg-sky-100 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div class="relative p-6 flex flex-col flex-1">
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
                <ul class="space-y-2 mb-6 flex-1">
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
                  onclick={() => push('/validators/waitlist/join')}
                  class="w-full flex items-center justify-center px-4 py-3 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors font-semibold group-hover:shadow-md mt-auto"
                >
                  <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L3.5 7v6c0 5.55 3.84 10.74 8.5 12 4.66-1.26 8.5-6.45 8.5-12V7L12 2zm2 5h-3l-1 5h3l-3 7 5-8h-3l2-4z"/>
                  </svg>
                  Join the Waitlist
                </button>
              </div>
            </div>
          </div>

          <!-- Become a Supporter Section (Below the two journey cards) -->
          <div class="mt-6">
            <div class="group relative bg-purple-50 border-2 border-purple-200 rounded-xl overflow-hidden hover:shadow-lg transition-all">
              <div class="absolute inset-0 bg-purple-100 opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div class="relative p-6">
                <div class="flex items-center mb-4">
                  <div class="flex items-center justify-center w-12 h-12 bg-purple-500 rounded-full mr-4 flex-shrink-0">
                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                  </div>
                  <div>
                    <h3 class="text-xl font-bold text-purple-900 mb-1">Become a Supporter</h3>
                    <p class="text-purple-700 text-sm">Grow the GenLayer community through referrals and earn rewards</p>
                  </div>
                </div>
                <ul class="space-y-2 mb-6">
                  <li class="flex items-center text-sm text-purple-600">
                    <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    Refer builders and validators to the program
                  </li>
                  <li class="flex items-center text-sm text-purple-600">
                    <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    Earn 10% of points from every contribution your referrals make
                  </li>
                  <li class="flex items-center text-sm text-purple-600">
                    <svg class="w-4 h-4 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                    </svg>
                    Receive 500 Discord XP for each valid referral
                  </li>
                </ul>
                <button
                  onclick={startCreatorJourney}
                  class="w-full flex items-center justify-center px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-semibold group-hover:shadow-md"
                >
                  <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                  </svg>
                  Become a Supporter
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Referrals Card - Full Width -->
    {#if !isValidatorOnly && (!isOwnProfile || hasAnyRole)}
      <div class="bg-purple-50 rounded-lg shadow-sm border border-purple-200 overflow-visible mb-6">
        <!-- Header -->
        <div class="bg-purple-100 px-5 py-3 border-b border-purple-200 flex items-center justify-between">
          <h2 class="text-lg font-semibold text-purple-700 uppercase tracking-wider flex items-center">
            <svg class="w-5 h-5 mr-2 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
            </svg>
            Referral Program
          </h2>
          {#if !loadingReferrals && referralData && referralData.total_referrals > 5}
            <button
              onclick={() => push('/referrals')}
              class="inline-flex items-center text-sm font-medium text-purple-700 hover:text-purple-900 group"
            >
              View all
              <svg class="w-4 h-4 ml-1 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path>
              </svg>
            </button>
          {/if}
        </div>

        <!-- Content -->
        <div class="p-6">
          {#if loadingReferrals || (referralData && (referralData.total_referrals > 0 || !isOwnProfile))}
            <!-- Metrics Grid - 3 columns (hide for own profile with 0 referrals) -->
            <div class="grid grid-cols-3 gap-3 mb-4">
              <!-- Total Referrals Container -->
              <div class="bg-white border border-gray-200 rounded-lg p-3">
                <div class="flex items-center">
                  <div class="flex-shrink-0 p-2.5 rounded-lg bg-purple-100 text-purple-600 mr-3">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                  </div>
                  <div class="flex-1">
                    <p class="text-sm text-gray-500">Total Referrals</p>
                    <p class="text-xl font-bold text-gray-900">
                      {#if loadingReferrals}
                        <span class="text-gray-400">...</span>
                      {:else}
                        {referralData?.total_referrals || 0}
                      {/if}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Builder Referral Points Container -->
              <div class="bg-white border border-gray-200 rounded-lg p-3">
                <div class="flex items-center">
                  <div class="flex-shrink-0 p-2.5 rounded-lg bg-orange-100 mr-3">
                    <Icons name="builder" size="md" className="text-orange-600" />
                  </div>
                  <div class="flex-1">
                    <div class="flex items-center gap-1.5">
                      <p class="text-sm text-gray-500">Builder Referral Points</p>
                      <div class="relative group">
                        <svg class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 w-[260px]">
                          <div class="text-center">Points earned from referrals' builder contributions</div>
                          <div class="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                            <div class="border-4 border-transparent border-t-gray-900"></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <p class="text-xl font-bold text-gray-900">
                      {#if loadingReferrals}
                        <span class="text-gray-400">...</span>
                      {:else}
                        {referralData?.builder_points || 0}
                      {/if}
                    </p>
                  </div>
                </div>
              </div>

              <!-- Validator Referral Points Container -->
              <div class="bg-white border border-gray-200 rounded-lg p-3">
                <div class="flex items-center">
                  <div class="flex-shrink-0 p-2.5 rounded-lg bg-blue-100 mr-3">
                    <Icons name="validator" size="md" className="text-blue-600" />
                  </div>
                  <div class="flex-1">
                    <div class="flex items-center gap-1.5">
                      <p class="text-sm text-gray-500">Validator Referral Points</p>
                      <div class="relative group">
                        <svg class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 w-[260px]">
                          <div class="text-center">Points earned from referrals' validator contributions</div>
                          <div class="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                            <div class="border-4 border-transparent border-t-gray-900"></div>
                          </div>
                        </div>
                      </div>
                    </div>
                    <p class="text-xl font-bold text-gray-900">
                      {#if loadingReferrals}
                        <span class="text-gray-400">...</span>
                      {:else}
                        {referralData?.validator_points || 0}
                      {/if}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          {/if}

          {#if isOwnProfile && !loadingReferrals}
            <!-- Referral link section - always show for own profile -->
            {#if !referralData || referralData.total_referrals === 0}
              <div class="flex flex-col lg:flex-row gap-6 items-start">
                <!-- Image -->
                <div class="w-full lg:w-1/3 flex-shrink-0">
                  <img src="/assets/builders_program.png" alt="Builder Program" class="w-full rounded-lg max-w-sm mx-auto" />
                </div>

                <!-- Text and Action -->
                <div class="w-full lg:w-2/3 space-y-4">
                  <p class="text-gray-700">
                    For each builder referred who submits at least one contribution, the referrer receives 10% of the points that builder earns permanently. In addition, referrers receive 500 Discord XP for each valid referral.
                  </p>
                  <p class="text-gray-700 font-bold italic">
                    Share the image with your referral link on X to be eligible for the $1000 raffle.
                  </p>
                  <div class="flex justify-start" style="overflow: visible;">
                    <ReferralSection />
                  </div>
                </div>
              </div>
            {:else}
              <div class="flex justify-start" style="overflow: visible;">
                <ReferralSection />
              </div>
            {/if}
          {/if}

          <!-- Table with referrals (only show for own profile when user has referrals) -->
          {#if isOwnProfile && !loadingReferrals && referralData && referralData.referrals && referralData.total_referrals > 0}
            <div class="mt-6">
              <h3 class="text-lg font-semibold text-gray-900 mb-4">Last Referrals</h3>
              <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Participant
                      </th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Builder Points Earned
                      </th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Validator Points Earned
                      </th>
                      <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Joined Date
                      </th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    {#each referralData.referrals.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5) as referral, i}
                      <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        <td class="px-6 py-4 whitespace-nowrap">
                          <div class="flex items-center">
                            <div class="flex-shrink-0 mr-3">
                              <Avatar
                                user={referral}
                                size="sm"
                                clickable={true}
                              />
                            </div>
                            <div>
                              <button
                                onclick={() => push(`/participant/${referral.address}`)}
                                class="text-sm font-medium text-gray-900 hover:text-purple-600 transition-colors"
                              >
                                {referral.name || 'Anonymous'}
                              </button>
                              <div class="text-sm text-gray-500">
                                {referral.address.slice(0, 6)}...{referral.address.slice(-4)}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          <div class="flex flex-col gap-1">
                            {#if referral.builder_contribution_points > 0}
                              <div class="inline-flex items-center gap-1">
                                <span class="text-sm text-gray-600">{referral.builder_contribution_points.toLocaleString()}</span>
                                <span class="text-gray-400">→</span>
                                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                                  +{Math.round(referral.builder_contribution_points * 0.1)}
                                </span>
                              </div>
                            {:else}
                              <span class="text-sm text-gray-400">—</span>
                            {/if}
                          </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap">
                          <div class="flex flex-col gap-1">
                            {#if referral.validator_contribution_points > 0}
                              <div class="inline-flex items-center gap-1">
                                <span class="text-sm text-gray-600">{referral.validator_contribution_points.toLocaleString()}</span>
                                <span class="text-gray-400">→</span>
                                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                  +{Math.round(referral.validator_contribution_points * 0.1)}
                                </span>
                              </div>
                            {:else}
                              <span class="text-sm text-gray-400">—</span>
                            {/if}
                          </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(referral.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>
          {/if}
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