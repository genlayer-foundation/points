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

  let buttonElement = $state(null);
  let showTooltip = $state(false);
  let tooltipPosition = $state({ top: 0, left: 0 });

  function updateTooltipPosition() {
    if (buttonElement && showTooltip) {
      const rect = buttonElement.getBoundingClientRect();
      tooltipPosition = {
        top: rect.bottom + 8,
        left: rect.left + rect.width / 2
      };
    }
  }

  function handleMouseEnter() {
    showTooltip = true;
    updateTooltipPosition();
    // Add scroll listener to update position while tooltip is shown
    window.addEventListener('scroll', updateTooltipPosition, true);
  }

  function handleMouseLeave() {
    showTooltip = false;
    // Remove scroll listener when tooltip is hidden
    window.removeEventListener('scroll', updateTooltipPosition, true);
  }

  function getButtonClass() {
    const baseClasses = 'w-36 px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap relative';

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
    bind:this={buttonElement}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
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

  <!-- Tooltip - Fixed position to avoid overflow clipping -->
  {#if showTooltip}
    <div
      class="fixed px-4 py-2 bg-gray-800 text-white text-xs rounded-lg w-72 whitespace-normal transform -translate-x-1/2 pointer-events-none"
      style="top: {tooltipPosition.top}px; left: {tooltipPosition.left}px; z-index: 999999;"
    >
      <p class="leading-relaxed whitespace-normal">Building is better together. Earn 10% of points from every contribution your referrals make. Welcome journey points count once they make any other contribution.</p>
      <!-- Arrow pointing up -->
      <div class="absolute bottom-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-b-gray-800"></div>
    </div>
  {/if}
{/if}