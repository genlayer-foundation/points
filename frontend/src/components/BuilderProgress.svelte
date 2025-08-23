<script>
  import { push } from 'svelte-spa-router';
  
  let {
    testnetBalance = null,
    hasBuilderWelcome = false,
    hasDeployedContract = false,
    showActions = true,
    colorTheme = 'orange',
    onClaimBuilderBadge = null,
    isClaimingBuilderBadge = false,
    onRefreshBalance = null,
    isRefreshingBalance = false
  } = $props();
  
  // Calculate completed requirements (excluding deploy which is coming soon)
  let completedCount = $derived(
    (hasBuilderWelcome ? 1 : 0) +
    (testnetBalance && testnetBalance > 0 ? 1 : 0)
  );
</script>

<div class="bg-white rounded-lg p-5 border border-{colorTheme}-200">
  <h3 class="text-base font-semibold text-gray-900 mb-3 flex items-center">
    <svg class="w-5 h-5 mr-2 text-{colorTheme}-500" fill="currentColor" viewBox="0 0 20 20">
      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
    </svg>
    Builder Requirements
  </h3>
  
  <div class="max-w-2xl">
    <!-- Requirements Grid -->
    <div class="grid grid-cols-1 md:grid-cols-[1fr,auto] gap-3">
      <!-- Requirement 1: First Points -->
      <div class="flex items-start gap-3">
        <div class="mt-0.5">
          {#if hasBuilderWelcome}
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
        <div>
          <p class="text-sm font-medium text-gray-900">Earn your first points</p>
          <p class="text-xs text-gray-500">
            {#if hasBuilderWelcome}
              Welcome! You've earned your first points in the Builder Journey
            {:else}
              Earn your first contribution to get started
            {/if}
          </p>
        </div>
      </div>
      <div class="flex items-start">
        {#if !hasBuilderWelcome && showActions}
          <button
            onclick={() => onClaimBuilderBadge ? onClaimBuilderBadge() : null}
            disabled={isClaimingBuilderBadge || !onClaimBuilderBadge}
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {#if isClaimingBuilderBadge}
              <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Claiming...
            {:else}
              <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
              </svg>
              Claim Contribution
            {/if}
          </button>
        {/if}
      </div>
    
      <!-- Requirement 2: Fund Account -->
      <div class="flex items-start gap-3">
        <div class="mt-0.5">
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
        <div>
          <p class="text-sm font-medium text-gray-900">Top up your GenLayer Testnet Asimov account</p>
          <p class="text-xs text-gray-500 flex items-center gap-2">
            {#if testnetBalance === null}
              <span class="inline-flex items-center">
                <svg class="animate-spin -ml-0.5 mr-1.5 h-3 w-3 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Checking balance...
              </span>
            {:else if testnetBalance > 0}
              <span>Current balance: {testnetBalance} GEN</span>
            {:else}
              <span>Visit the faucet to get testnet tokens</span>
            {/if}
            {#if showActions && onRefreshBalance && testnetBalance !== null}
              <button
                onclick={onRefreshBalance}
                disabled={isRefreshingBalance}
                class="inline-flex items-center justify-center w-4 h-4 rounded hover:bg-gray-100 transition-colors disabled:opacity-50"
                title="Refresh balance"
              >
                {#if isRefreshingBalance}
                  <svg class="animate-spin w-3 h-3 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                {:else}
                  <svg class="w-3 h-3 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                {/if}
              </button>
            {/if}
          </p>
        </div>
      </div>
      <div class="flex items-start">
        {#if showActions && testnetBalance !== null && testnetBalance === 0}
          <a
            href="https://genlayer-faucet.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
          >
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"/>
            </svg>
            Get Tokens
          </a>
        {/if}
      </div>
    
      <!-- Requirement 3: Deploy Contract (Coming Soon) -->
      <div class="flex items-start gap-3 opacity-60">
        <div class="mt-0.5">
          <div class="w-5 h-5 rounded-full bg-gray-100 border-2 border-gray-300 flex items-center justify-center">
            <svg class="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/>
            </svg>
          </div>
        </div>
        <div>
          <p class="text-sm font-medium text-gray-900">Deploy your first smart contract</p>
          <p class="text-xs text-gray-500">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
              Coming Soon
            </span>
          </p>
        </div>
      </div>
      <div class="flex items-start">
        {#if showActions}
          <a
            href="https://studio.genlayer.com"
            target="_blank"
            rel="noopener noreferrer"
            class="px-3 py-1 bg-orange-500 text-white text-xs font-medium rounded-md hover:bg-orange-600 transition-colors flex items-center whitespace-nowrap"
          >
            <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/>
              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"/>
            </svg>
            Open Studio
          </a>
        {/if}
      </div>
    </div>
    
    {#if showActions}
      <!-- Progress status -->
      <div class="mt-4 text-xs text-gray-500">
        <span class="font-medium">{completedCount} of 2</span> requirements completed
      </div>
    {/if}
  </div>
</div>