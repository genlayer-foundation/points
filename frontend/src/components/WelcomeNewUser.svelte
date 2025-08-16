<script>
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { contributionsAPI } from '../lib/api';
  
  let isNewUser = $state(false);
  let hasJourneys = $state(false);
  let hasContributions = $state(false);
  let loading = $state(true);
  
  onMount(async () => {
    if (!$authState.isAuthenticated) {
      loading = false;
      return;
    }
    
    try {
      // Check if user has journey badges or contributions
      const user = $userStore.user;
      hasJourneys = user?.has_validator_waitlist || user?.has_builder_initiate || user?.validator || user?.builder;
      
      // Check if user has any contributions
      const contribResponse = await contributionsAPI.getUserContributions($authState.address);
      hasContributions = contribResponse.data?.results?.length > 0;
      
      // User is new if they have no journeys and no contributions
      isNewUser = !hasJourneys && !hasContributions;
    } catch (err) {
      console.error('Error checking user status:', err);
    } finally {
      loading = false;
    }
  });
  
  function handleStartJourney() {
    push('/profile');
  }
  
  function handleSubmitContribution() {
    push('/submit-contribution');
  }
</script>

{#if !loading && $authState.isAuthenticated && isNewUser}
  <div class="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg shadow-xl p-8 mb-8 text-white">
    <div class="max-w-4xl mx-auto">
      <div class="flex items-center mb-6">
        <svg class="w-12 h-12 mr-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z"/>
          <path fill-rule="evenodd" d="M4 5a2 2 0 012-2 1 1 0 000 2H6a2 2 0 100 4h2a2 2 0 100-4h-.5a1 1 0 000-2H8a2 2 0 012-2h2a2 2 0 012 2v9a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" clip-rule="evenodd"/>
        </svg>
        <div>
          <h2 class="text-3xl font-bold">Welcome to Tally, {$userStore.user?.name || 'Participant'}!</h2>
          <p class="text-purple-100 mt-1">Your journey to becoming a top contributor starts here</p>
        </div>
      </div>
      
      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-white/10 backdrop-blur rounded-lg p-6">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <span class="text-xl font-bold">1</span>
              </div>
            </div>
            <div class="ml-4">
              <h3 class="text-xl font-semibold mb-2">Start Your Journey</h3>
              <p class="text-purple-100 mb-4">
                Choose your path: Become a Validator or Builder. Complete challenges to earn badges and unlock rewards.
              </p>
              <button
                onclick={handleStartJourney}
                class="inline-flex items-center px-4 py-2 bg-white text-purple-600 rounded-md hover:bg-purple-50 transition-colors font-medium"
              >
                Choose Your Path
                <svg class="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        
        <div class="bg-white/10 backdrop-blur rounded-lg p-6">
          <div class="flex items-start">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                <span class="text-xl font-bold">2</span>
              </div>
            </div>
            <div class="ml-4">
              <h3 class="text-xl font-semibold mb-2">Submit Contributions</h3>
              <p class="text-purple-100 mb-4">
                Already contributing? Submit your work to earn points and climb the leaderboard.
              </p>
              <button
                onclick={handleSubmitContribution}
                class="inline-flex items-center px-4 py-2 bg-white/20 text-white border border-white/30 rounded-md hover:bg-white/30 transition-colors font-medium"
              >
                Submit Contribution
                <svg class="ml-2 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <div class="mt-6 pt-6 border-t border-white/20">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-purple-100 text-sm">Need help getting started?</p>
            <p class="text-white font-medium">Check out our documentation and tutorials</p>
          </div>
          <a 
            href="https://docs.genlayer.com" 
            target="_blank" 
            rel="noopener noreferrer"
            class="inline-flex items-center text-white hover:text-purple-100 transition-colors"
          >
            View Docs
            <svg class="ml-1 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        </div>
      </div>
    </div>
  </div>
{/if}