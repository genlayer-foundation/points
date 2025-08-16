<script>
  import { authState } from '../lib/auth';
  import { userStore } from '../lib/userStore';
  import { journeyAPI } from '../lib/api';
  
  let { user } = $props();
  
  let isCompleting = $state(false);
  let error = $state('');
  
  // Check if user has builder profile or initiate badge
  let hasBuilder = $derived(user?.builder);
  let hasInitiate = $derived(user?.has_builder_initiate);
  let showJourney = $derived(!hasBuilder && !hasInitiate);
  
  async function completeJourney() {
    error = '';
    isCompleting = true;
    
    try {
      const response = await journeyAPI.completeBuilderJourney();
      // Update user store with new badge status
      await userStore.loadUser();
      // Show success message
      alert(response.data.message || 'Builder initiate badge awarded!');
    } catch (err) {
      error = err.response?.data?.error || 'Failed to complete journey';
    } finally {
      isCompleting = false;
    }
  }
</script>

{#if showJourney}
  <div class="bg-orange-50 border-2 border-orange-200 rounded-lg p-6">
    <div class="flex items-start">
      <div class="flex-shrink-0">
        <div class="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
          <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
          </svg>
        </div>
      </div>
      <div class="ml-4 flex-1">
        <h3 class="text-lg font-semibold text-orange-900 mb-2">Builder Journey</h3>
        <p class="text-orange-700 mb-4">
          Start your builder journey and earn 20 points! Deploy your first contract to get started.
        </p>
        
        <div class="space-y-3 mb-4">
          <div class="flex items-start">
            <svg class="w-5 h-5 text-orange-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <p class="text-sm font-medium text-orange-800">Deploy a Smart Contract</p>
              <p class="text-xs text-orange-600">Use the GenLayer Studio with this wallet</p>
              <span class="text-xs text-orange-500 italic">Coming soon...</span>
            </div>
          </div>
          
          <div class="flex items-start">
            <svg class="w-5 h-5 text-orange-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
            </svg>
            <div>
              <p class="text-sm font-medium text-orange-800">Complete the Tutorial</p>
              <p class="text-xs text-orange-600">Learn the basics of building on GenLayer</p>
              <span class="text-xs text-orange-500 italic">Tutorial coming soon...</span>
            </div>
          </div>
        </div>
        
        {#if error}
          <div class="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm mb-3">
            {error}
          </div>
        {/if}
        
        <div class="bg-orange-100 border border-orange-300 rounded-md p-3 mb-4">
          <p class="text-xs text-orange-700">
            <strong>Note:</strong> Builder tools are coming soon. For now, you can manually claim your initiate badge to get started!
          </p>
        </div>
        
        <button
          onclick={completeJourney}
          disabled={isCompleting}
          class="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isCompleting ? 'Processing...' : 'Claim Builder Initiate Badge (Demo)'}
        </button>
      </div>
    </div>
  </div>
{:else if hasInitiate && !hasBuilder}
  <div class="bg-orange-50 border-2 border-orange-200 rounded-lg p-6">
    <div class="flex items-center">
      <div class="flex-shrink-0">
        <svg class="w-8 h-8 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
        </svg>
      </div>
      <div class="ml-4">
        <h3 class="text-lg font-semibold text-orange-900">Builder Initiate</h3>
        <p class="text-orange-700">You've started your builder journey! Keep building to earn more points.</p>
        <div class="mt-2 inline-flex items-center px-3 py-1 rounded-full bg-orange-200 text-orange-800 text-sm font-medium">
          <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
          </svg>
          Initiate Badge Earned
        </div>
      </div>
    </div>
  </div>
{/if}