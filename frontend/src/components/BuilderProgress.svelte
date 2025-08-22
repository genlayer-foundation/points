<script>
  import { push } from 'svelte-spa-router';
  
  let {
    testnetBalance = null,
    hasValidatorWelcome = false,
    hasDeployedContract = false,
    showActions = true,
    colorTheme = 'orange'
  } = $props();
  
  // Calculate completed requirements (excluding deploy which is coming soon)
  let completedCount = $derived(
    (hasValidatorWelcome ? 1 : 0) +
    (testnetBalance && testnetBalance > 0 ? 1 : 0)
  );
</script>

<div class="bg-white rounded-lg p-5 border border-{colorTheme}-200">
  <h3 class="text-base font-semibold text-gray-900 mb-3 flex items-center">
    <svg class="w-5 h-5 mr-2 text-{colorTheme}-500" fill="currentColor" viewBox="0 0 20 20">
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
    </svg>
    Builder Badge Progress
  </h3>
  
  <div class="space-y-3">
    <!-- Requirement 1: First Points -->
    <div class="flex items-start">
      <div class="flex-shrink-0 mt-0.5">
        {#if hasValidatorWelcome}
          <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
            <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </div>
        {:else}
          <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
            <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
          </div>
        {/if}
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm font-medium text-gray-900">Earn your first points</p>
        <p class="text-xs text-gray-500">
          {#if hasValidatorWelcome}
            Welcome! You've earned your first points in the Builder Journey
          {:else}
            Join the validator waitlist to get started
          {/if}
        </p>
      </div>
    </div>
    
    <!-- Requirement 2: Fund Account -->
    <div class="flex items-start">
      <div class="flex-shrink-0 mt-0.5">
        {#if testnetBalance && testnetBalance > 0}
          <div class="w-5 h-5 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center">
            <svg class="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </div>
        {:else}
          <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
            <div class="w-2 h-2 bg-gray-400 rounded-full"></div>
          </div>
        {/if}
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm font-medium text-gray-900">Top up your GenLayer Testnet Asimov account</p>
        <p class="text-xs text-gray-500">
          {#if testnetBalance === null}
            <span class="inline-flex items-center">
              <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Checking balance...
            </span>
          {:else if testnetBalance > 0}
            Current balance: {testnetBalance} GEN
          {:else}
            Visit the faucet to get testnet tokens
          {/if}
        </p>
      </div>
    </div>
    
    <!-- Requirement 3: Deploy Contract (Coming Soon) -->
    <div class="flex items-start opacity-60">
      <div class="flex-shrink-0 mt-0.5">
        <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
          <svg class="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
          </svg>
        </div>
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm font-medium text-gray-900">Deploy your first smart contract</p>
        <p class="text-xs text-gray-500">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
            Coming Soon
          </span>
        </p>
      </div>
    </div>
  </div>
  
  {#if showActions}
    <!-- CTA Button -->
    <div class="mt-5 flex items-center justify-between">
      <div class="text-xs text-gray-500">
        <span class="font-medium">{completedCount} of 2</span> requirements completed
      </div>
      <button
        onclick={() => push('/submit-contribution')}
        class="inline-flex items-center px-4 py-2 bg-{colorTheme}-500 text-white text-sm font-medium rounded-lg hover:bg-{colorTheme}-600 transition-all duration-200 shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
      >
        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd"/>
        </svg>
        Continue Building
      </button>
    </div>
  {/if}
</div>