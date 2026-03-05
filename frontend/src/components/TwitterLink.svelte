<script>
  import { authState } from '../lib/auth';
  import { getCurrentUser } from '../lib/api';
  import { showSuccess, showError } from '../lib/toastStore';

  // Props using Svelte 5 syntax
  let {
    onLinked = () => {},
    buttonClass = 'w-full px-3 py-2 bg-black text-white rounded-md hover:bg-gray-800 transition-colors flex items-center justify-center gap-2',
    buttonText = 'Link Twitter Account'
  } = $props();

  // State
  let isLinking = $state(false);
  let oauthChannel = null;

  async function linkTwitter() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }

    isLinking = true;

    // Store initial Twitter username to detect if it changed
    let initialTwitterUsername = null;
    try {
      const initialUser = await getCurrentUser();
      initialTwitterUsername = initialUser.twitter_connection?.username || null;
    } catch (err) {
      // Silently handle initial user state error
    }

    // Use absolute backend URL to avoid proxy issues
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const oauthUrl = `${backendUrl}/api/auth/twitter/`;

    // Open OAuth in popup window
    const popupWidth = 600;
    const popupHeight = 700;
    const left = window.screenX + (window.outerWidth - popupWidth) / 2;
    const top = window.screenY + (window.outerHeight - popupHeight) / 2;

    const popup = window.open(
      oauthUrl,
      'Twitter OAuth',
      `width=${popupWidth},height=${popupHeight},left=${left},top=${top},toolbar=no,menubar=no,location=no`
    );

    if (!popup) {
      showError('Please allow popups for this site to link your Twitter account');
      isLinking = false;
      return;
    }

    // Handle OAuth result via BroadcastChannel
    async function handleOAuthResult(success, errorType) {
      if (success) {
        try {
          const currentUser = await getCurrentUser();
          showSuccess(`Twitter account linked successfully! (@${currentUser.twitter_connection?.username})`);
          onLinked(currentUser);
        } catch (err) {
          showError('Twitter linked but failed to refresh data. Please refresh the page.');
        }
      } else {
        if (errorType === 'already_linked') {
          showError('This Twitter account is already linked to another user');
        } else if (errorType === 'not_authenticated') {
          showError('You must be logged in to link your Twitter account');
        } else if (errorType === 'code_already_used') {
          showError('This authorization code has already been used. Please try again.');
        } else {
          showError('Failed to link Twitter account. Please try again.');
        }
      }
      isLinking = false;
    }

    // Create BroadcastChannel for OAuth communication
    if (oauthChannel) {
      oauthChannel.close();
    }

    oauthChannel = new BroadcastChannel('twitter_oauth');

    oauthChannel.onmessage = async (event) => {
      if (event.data.type === 'twitter_oauth_success' || event.data.type === 'twitter_oauth_error') {
        const success = event.data.type === 'twitter_oauth_success';
        const errorType = event.data.error || '';
        await handleOAuthResult(success, errorType);

        oauthChannel.close();
        oauthChannel = null;
      }
    };

    // Fallback: Check when popup closes
    const popupChecker = setInterval(async () => {
      if (popup.closed) {
        clearInterval(popupChecker);

        await new Promise(resolve => setTimeout(resolve, 300));

        try {
          const currentUser = await getCurrentUser();

          if (currentUser.twitter_connection?.username && currentUser.twitter_connection?.username !== initialTwitterUsername) {
            showSuccess(`Twitter account linked successfully! (@${currentUser.twitter_connection?.username})`);
            onLinked(currentUser);
          }
        } catch (err) {
          // Silently handle reload error
        } finally {
          isLinking = false;
        }

        if (oauthChannel) {
          oauthChannel.close();
          oauthChannel = null;
        }
      }
    }, 500);
  }
</script>

<button
  onclick={linkTwitter}
  disabled={isLinking}
  class={buttonClass}
>
  {#if isLinking}
    <svg class="animate-spin h-3 w-3 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    Linking...
  {:else}
    <!-- X (Twitter) Logo -->
    <svg class="w-3 h-3 mr-2" fill="currentColor" viewBox="0 0 24 24">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
    </svg>
    {buttonText}
  {/if}
</button>
