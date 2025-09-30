<script>
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';

  // Component state
  let state = $state('success'); // success, copied (simplified states)
  let referralCode = $state(null);

  // Get current user from store
  let user = $derived($userStore.user);

  // Get referral code from user store (populated from login response)
  $effect(() => {
    if (user?.referral_code) {
      referralCode = user.referral_code;
    }
  });

  // Generate referral URL
  let referralUrl = $derived(referralCode ? `${window.location.origin}?ref=${referralCode}` : '');

  async function handleCopyLink() {
    if (!referralUrl) return;

    const copyText = `Build. Earn. Amplify.
Join GenLayer's Builder Program and earn points for real contributions.
👉 Start here: ${referralUrl}`;

    try {
      await navigator.clipboard.writeText(copyText);
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
        textArea.value = copyText;
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
    const baseClasses = 'w-36 px-4 py-2 text-sm rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap group relative';

    if (state === 'copied') {
      return `${baseClasses} text-green-600 bg-green-50 border border-green-200`;
    }
    return `${baseClasses} text-purple-600 hover:bg-purple-50 border border-purple-200`;
  }
</script>

<!-- Only show for authenticated users -->
{#if $authState.isAuthenticated && referralCode}
  <!-- Referral Link Button with Tooltip -->
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

    <!-- Tooltip on button hover -->
    <div class="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 px-4 py-2 bg-gray-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none w-72 whitespace-normal" style="z-index: 999999;">
      <p class="font-semibold mb-1 whitespace-normal">Amplify Your Impact</p>
      <p class="leading-relaxed whitespace-normal">Building is better together. Earn 10% of points from every contribution your referrals make.</p>
      <!-- Arrow pointing up -->
      <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-b-gray-800"></div>
    </div>
  </button>
{/if}