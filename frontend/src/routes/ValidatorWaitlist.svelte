<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth';
  import { getCurrentUser, journeyAPI } from '../lib/api';
  import Icon from '../components/Icons.svelte';
  
  let currentUser = $state(null);
  let hasFilledForm = $state(false);
  let isJoiningWaitlist = $state(false);
  let error = $state('');
  let loading = $state(true);
  
  onMount(async () => {
    await loadData();
  });
  
  async function loadData() {
    try {
      // If authenticated, get user data
      if ($authState.isAuthenticated) {
        currentUser = await getCurrentUser();
      }
    } catch (err) {
      console.error('Failed to load user data:', err);
    } finally {
      loading = false;
    }
  }
  
  async function handleJoinWaitlist() {
    if (!$authState.isAuthenticated) {
      // Show connect wallet prompt
      document.querySelector('.auth-button')?.click();
      return;
    }
    
    if (!hasFilledForm) {
      return;
    }
    
    isJoiningWaitlist = true;
    error = '';
    
    try {
      await journeyAPI.completeValidatorJourney();
      // Store success message and redirect to profile
      sessionStorage.setItem('journeySuccess', 'Successfully joined Testnet Asimov Validator Waitlist! +20 points earned.');
      push(`/participant/${$authState.address}`);
    } catch (err) {
      error = err.response?.data?.error || 'Failed to join waitlist';
      isJoiningWaitlist = false;
    }
  }
</script>

<div class="space-y-6 sm:space-y-8">
  <!-- Clean Header -->
  <div>
    <h1 class="text-2xl font-bold text-gray-900">Testnet Asimov Validator Waitlist</h1>
    <p class="mt-1 text-sm text-gray-500">
      Join the waitlist to become a validator on GenLayer's Testnet Asimov
    </p>
  </div>

  <!-- Main Card with Process -->
  <div class="bg-white border border-gray-200 rounded-lg shadow-sm">
    <div class="p-6">
      <!-- Three Steps -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <!-- Step 1: Join Waitlist -->
        <div class="flex items-center">
          <div class="flex items-center justify-center font-bold text-sky-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
            1
          </div>
          <div class="flex items-center justify-center w-10 h-10 bg-sky-100 rounded-lg flex-shrink-0">
            <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"/>
            </svg>
          </div>
          <div class="flex-1 ml-2">
            <h3 class="font-semibold text-gray-900">Join Waitlist</h3>
            <p class="text-sm text-gray-600">
              Complete the <a 
                href="https://forms.gle/hdH5ssuQPAT9i6hg9" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-sky-600 hover:text-sky-700 underline"
              >form</a> and join
            </p>
          </div>
        </div>
        
        <!-- Step 2: Contribute -->
        <div class="flex items-center">
          <div class="flex items-center justify-center font-bold text-sky-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
            2
          </div>
          <div class="flex items-center justify-center w-10 h-10 bg-sky-100 rounded-lg flex-shrink-0">
            <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          <div class="flex-1 ml-2">
            <h3 class="font-semibold text-gray-900">Contribute</h3>
            <p class="text-sm text-gray-600">Earn points to climb rankings</p>
          </div>
        </div>
        
        <!-- Step 3: Get Selected -->
        <div class="flex items-center">
          <div class="flex items-center justify-center font-bold text-sky-600 flex-shrink-0 leading-10 mr-2" style="font-size: 2.25rem;">
            3
          </div>
          <div class="flex items-center justify-center w-10 h-10 bg-sky-100 rounded-lg flex-shrink-0">
            <svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div class="flex-1 ml-2">
            <h3 class="font-semibold text-gray-900">Get Selected</h3>
            <p class="text-sm text-gray-600">Top contributors join Testnet</p>
          </div>
        </div>
      </div>

      <!-- Divider -->
      <div class="border-t border-gray-100 pt-6">
        <!-- Two Column Layout for Info -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Ways to Contribute -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">Ways to Contribute</h3>
            <p class="text-sm text-gray-600 mb-2">
              Earn points through <span class="font-medium">Technical</span> and <span class="font-medium">Ecosystem & Community</span> Contributions.
            </p>
            <a 
              href="/contributions"
              onclick={(e) => { e.preventDefault(); push('/contributions'); }}
              class="text-sm text-sky-600 hover:text-sky-700 font-medium inline-flex items-center"
            >
              View all contribution types
              <svg class="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
              </svg>
            </a>
          </div>
          
          <!-- Selection Info -->
          <div>
            <h3 class="text-sm font-semibold text-gray-900 mb-2">Selection Process</h3>
            <p class="text-sm text-gray-600">
              Validator selection is based on <span class="font-medium">leaderboard rankings</span>, prioritizing professionals with proven track records. 
              Validators who bring unique value to the GenLayer ecosystem are also considered.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Join Action Section -->
  <div class="bg-white shadow-sm rounded-lg p-6 sm:p-8">
    <h2 class="text-xl font-bold text-gray-900 mb-3">Start Your Validator Journey</h2>
    
    <p class="text-gray-700 mb-6">
      First, complete the application form to provide your technical background and validator experience. 
      Then join the waitlist to start contributing.
    </p>
    
    <div class="space-y-4">
      <div>
        <a 
          href="https://forms.gle/hdH5ssuQPAT9i6hg9" 
          target="_blank" 
          rel="noopener noreferrer"
          class="inline-flex items-center px-5 py-2.5 bg-sky-50 text-sky-700 border border-sky-300 rounded-lg hover:bg-sky-100 transition-colors font-medium"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          Complete Application Form
        </a>
      </div>
      
      <div class="pt-2">
        <div class="flex items-start space-x-3 mb-4">
          <input 
            type="checkbox" 
            id="formCompleted" 
            bind:checked={hasFilledForm}
            class="mt-0.5 h-4 w-4 text-sky-600 focus:ring-sky-500 border-gray-300 rounded"
          />
          <label for="formCompleted" class="text-sm text-gray-700">
            I have completed the GenLayer Testnet Asimov Validator Application
          </label>
        </div>
        
        <button
          onclick={handleJoinWaitlist}
          disabled={!hasFilledForm || isJoiningWaitlist}
          class="inline-flex items-center px-8 py-3 bg-sky-600 text-white rounded-lg font-medium hover:bg-sky-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          <Icon name="validator" className="mr-2 text-white" />
          {#if !$authState.isAuthenticated}
            Connect Wallet to Join Waitlist
          {:else if isJoiningWaitlist}
            Joining Waitlist...
          {:else}
            Join Validator Waitlist
          {/if}
        </button>
        
        {#if error}
          <div class="mt-4 text-red-600 text-sm">{error}</div>
        {/if}
      </div>
    </div>
  </div>
</div>