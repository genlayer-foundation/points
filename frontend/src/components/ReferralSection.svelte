<script>
  import { getReferralCode } from '../lib/api.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';

  // Component state
  let state = $state('success'); // success, copied (simplified states)
  let referralCode = $state(null);

  // Get current user from store
  let user = $derived($userStore.user);

  // Get referral code from user profile or fetch it
  $effect(async () => {
    if (user?.referral_code) {
      referralCode = user.referral_code;
    } else if ($authState.isAuthenticated && !referralCode) {
      // Fetch referral code if not in user profile yet
      try {
        const response = await getReferralCode();
        referralCode = response.referral_code;
        // Update user store to reflect the referral code
        userStore.updateUser({ referral_code: referralCode });
      } catch (error) {
        console.error('Failed to fetch referral code:', error);
      }
    }
  });

  // Generate referral URL
  let referralUrl = $derived(referralCode ? `${window.location.origin}?ref=${referralCode}` : '');

  async function handleCopyLink() {
    if (!referralUrl) return;
    
    try {
      await navigator.clipboard.writeText(referralUrl);
      state = 'copied';
      
      // Reset state after 2 seconds
      setTimeout(() => {
        state = 'success';
      }, 2000);
      
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
      // Fallback for older browsers
      try {
        const textArea = document.createElement('textarea');
        textArea.value = referralUrl;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        state = 'copied';
        setTimeout(() => {
          state = 'success';
        }, 2000);
      } catch (fallbackError) {
        state = 'error';
        errorMessage = 'Failed to copy to clipboard';
      }
    }
  }

  function getButtonText() {
    if (state === 'copied') {
      return 'Copied !';
    }
    return 'Referral Link';
  }

  function getButtonClass() {
    const baseClasses = 'px-3 py-1.5 text-sm rounded font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap';
    
    if (state === 'copied') {
      return `${baseClasses} text-green-600 bg-green-50 border border-green-200`;
    }
    return `${baseClasses} text-blue-600 hover:bg-blue-50 border border-blue-200`;
  }
</script>

<!-- Only show for authenticated users -->
{#if $authState.isAuthenticated && referralCode}
  <div class="flex items-center gap-2">
    <!-- Referral Link Button -->
    <button 
      onclick={handleCopyLink}
      class={getButtonClass()}
      disabled={state === 'copied'}
    >
      <!-- Link Icon -->
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
      </svg>
      {getButtonText()}
    </button>

    <!-- Help Icon with Tooltip -->
    <div class="relative">
      <button 
        class="p-1.5 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors group" 
        aria-label="How referrals work"
      >
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
        </svg>
        
        <!-- Tooltip positioned below using transform and high z-index -->
        <div class="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-64" style="z-index: 999999;">
          <div>
            <p class="font-semibold mb-1">How Referrals Work</p>
            <p class="text-xs leading-relaxed">Share your referral link to invite others to GenLayer Points. When they sign up using your link, they'll be connected to you as your referral.</p>
          </div>
          <!-- Arrow pointing up -->
          <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-b-gray-800"></div>
        </div>
      </button>
    </div>
  </div>
{/if}