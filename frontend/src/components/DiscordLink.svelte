<script>
  import { authState } from '../lib/auth';
  import { getCurrentUser } from '../lib/api';
  import { showSuccess, showError } from '../lib/toastStore';

  // Props using Svelte 5 syntax
  let {
    onLinked = () => {},
    buttonClass = 'w-full px-3 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2',
    buttonText = 'Link Discord Account'
  } = $props();

  // State
  let isLinking = $state(false);
  let oauthChannel = null;

  async function linkDiscord() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }

    isLinking = true;

    // Store initial Discord username to detect if it changed
    let initialDiscordUsername = null;
    try {
      const initialUser = await getCurrentUser();
      initialDiscordUsername = initialUser.discord_connection?.username || null;
    } catch (err) {
      // Silently handle initial user state error
    }

    // Use absolute backend URL to avoid proxy issues
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const oauthUrl = `${backendUrl}/api/auth/discord/`;

    // Open OAuth in popup window
    const popupWidth = 600;
    const popupHeight = 700;
    const left = window.screenX + (window.outerWidth - popupWidth) / 2;
    const top = window.screenY + (window.outerHeight - popupHeight) / 2;

    const popup = window.open(
      oauthUrl,
      'Discord OAuth',
      `width=${popupWidth},height=${popupHeight},left=${left},top=${top},toolbar=no,menubar=no,location=no`
    );

    if (!popup) {
      showError('Please allow popups for this site to link your Discord account');
      isLinking = false;
      return;
    }

    // Handle OAuth result via BroadcastChannel
    async function handleOAuthResult(success, errorType) {
      if (success) {
        try {
          const currentUser = await getCurrentUser();
          showSuccess(`Discord account linked successfully! (${currentUser.discord_connection?.username})`);
          onLinked(currentUser);
        } catch (err) {
          showError('Discord linked but failed to refresh data. Please refresh the page.');
        }
      } else {
        if (errorType === 'already_linked') {
          showError('This Discord account is already linked to another user');
        } else if (errorType === 'not_authenticated') {
          showError('You must be logged in to link your Discord account');
        } else if (errorType === 'code_already_used') {
          showError('This authorization code has already been used. Please try again.');
        } else {
          showError('Failed to link Discord account. Please try again.');
        }
      }
      isLinking = false;
    }

    // Create BroadcastChannel for OAuth communication
    if (oauthChannel) {
      oauthChannel.close();
    }

    oauthChannel = new BroadcastChannel('discord_oauth');

    oauthChannel.onmessage = async (event) => {
      if (event.data.type === 'discord_oauth_success' || event.data.type === 'discord_oauth_error') {
        const success = event.data.type === 'discord_oauth_success';
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

          if (currentUser.discord_connection?.username && currentUser.discord_connection?.username !== initialDiscordUsername) {
            showSuccess(`Discord account linked successfully! (${currentUser.discord_connection?.username})`);
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
  onclick={linkDiscord}
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
    <!-- Discord Logo -->
    <svg class="w-3 h-3 mr-2" fill="currentColor" viewBox="0 0 24 24">
      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/>
    </svg>
    {buttonText}
  {/if}
</button>
