<script>
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { journeyAPI } from '../lib/api';
  import { push } from 'svelte-spa-router';
  
  let { user } = $props();
  
  let isCompleting = $state(false);
  let error = $state('');
  
  // Check if user has validator profile or waitlist badge
  let hasValidator = $derived(user?.validator);
  let hasWaitlist = $derived(user?.has_validator_waitlist);
  let showJourney = $derived(!hasValidator && !hasWaitlist);
  
  async function completeJourney() {
    error = '';
    isCompleting = true;
    
    try {
      const response = await journeyAPI.completeValidatorJourney();
      // Update user store with new badge status
      await userStore.loadUser();
      // Show success message
      alert(response.data.message || 'Validator waitlist badge awarded!');
    } catch (err) {
      error = err.response?.data?.error || 'Failed to complete journey';
    } finally {
      isCompleting = false;
    }
  }
</script>

{#if showJourney}
  <div class="bg-sky-50 border-2 border-sky-200 rounded-lg p-6">
    <div class="flex items-start">
      <div class="flex-shrink-0">
        <div class="w-12 h-12 bg-sky-100 rounded-full flex items-center justify-center">
          <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
        </div>
      </div>
      <div class="ml-4 flex-1">
        <h3 class="text-lg font-semibold text-sky-900 mb-2">Validator Journey</h3>
        <p class="text-sky-700 mb-4">
          Join the validator waitlist and earn 20 points! Complete the requirements below to get started.
        </p>
        
        <div class="space-y-3 mb-4">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-sky-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <p class="text-sm font-medium text-sky-800">Complete the Interest Form</p>
              <a 
                href="https://docs.google.com/forms/d/e/1FAIpQLSc7YujY6S6knB9XC8kL-2wsgNHrweqULstgc-OOMERlRsfg0A/viewform"
                target="_blank"
                rel="noopener noreferrer"
                class="text-xs text-sky-600 hover:text-sky-800 underline"
              >
                Open the validator interest form →
              </a>
            </div>
          </div>
          
          <div class="flex items-start">
            <svg class="w-5 h-5 text-sky-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <p class="text-sm font-medium text-sky-800">Earn Points & Climb Leaderboard</p>
              <p class="text-xs text-sky-600">Top contributors will be selected for phase 4</p>
            </div>
          </div>
        </div>
        
        {#if error}
          <div class="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm mb-3">
            {error}
          </div>
        {/if}
        
        <div class="bg-sky-100 border border-sky-300 rounded-md p-3 mb-4">
          <p class="text-xs text-sky-700">
            <strong>Note:</strong> After completing the form, click the button below to receive your waitlist badge.
          </p>
        </div>
        
        <button
          onclick={completeJourney}
          disabled={isCompleting}
          class="px-4 py-2 bg-sky-600 text-white rounded-md hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isCompleting ? 'Processing...' : 'I\'ve Completed the Form - Claim Badge'}
        </button>
      </div>
    </div>
  </div>
{:else if hasWaitlist && !hasValidator}
  <div class="bg-sky-50 border-2 border-sky-200 rounded-lg p-6">
    <div class="flex items-center">
      <div class="flex-shrink-0">
        <svg class="w-8 h-8 text-sky-600" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
      </div>
      <div class="ml-4">
        <h3 class="text-lg font-semibold text-sky-900">Validator Waitlist Member</h3>
        <p class="text-sky-700">You're on the waitlist! Keep earning points to improve your position.</p>
        <div class="mt-2 inline-flex items-center px-3 py-1 rounded-full bg-sky-200 text-sky-800 text-sm font-medium">
          <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
          </svg>
          Waitlist Badge Earned
        </div>
      </div>
    </div>
  </div>
{/if}