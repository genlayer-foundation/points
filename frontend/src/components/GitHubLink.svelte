<script>
  import { authState } from '../lib/auth';
  import { getCurrentUser } from '../lib/api';
  import { showSuccess, showError } from '../lib/toastStore';

  // Props using Svelte 5 syntax
  let {
    onLinked = () => {},
    buttonClass = 'w-full px-3 py-2 bg-gray-800 text-white rounded-md hover:bg-gray-900 transition-colors flex items-center justify-center gap-2',
    buttonText = 'Link GitHub Account'
  } = $props();

  // State
  let isLinking = $state(false);
  let oauthChannel = null;

  async function linkGitHub() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }

    isLinking = true;

    // Store initial GitHub username to detect if it changed
    let initialGithubUsername = null;
    try {
      const initialUser = await getCurrentUser();
      initialGithubUsername = initialUser.github_username || null;
    } catch (err) {
      // Silently handle initial user state error
    }

    // Use absolute backend URL to avoid proxy issues
    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const oauthUrl = `${backendUrl}/api/auth/github/`;

    // Open OAuth in popup window
    const popupWidth = 600;
    const popupHeight = 700;
    const left = window.screenX + (window.outerWidth - popupWidth) / 2;
    const top = window.screenY + (window.outerHeight - popupHeight) / 2;

    const popup = window.open(
      oauthUrl,
      'GitHub OAuth',
      `width=${popupWidth},height=${popupHeight},left=${left},top=${top},toolbar=no,menubar=no,location=no`
    );

    if (!popup) {
      showError('Please allow popups for this site to link your GitHub account');
      isLinking = false;
      return;
    }

    // Handle OAuth result via BroadcastChannel
    async function handleOAuthResult(success, errorType) {
      if (success) {
        try {
          // Reload user data to get updated GitHub info
          const currentUser = await getCurrentUser();
          showSuccess(`GitHub account linked successfully! (@${currentUser.github_username})`);

          // Call the onLinked callback with updated user data
          onLinked(currentUser);
        } catch (err) {
          showError('GitHub linked but failed to refresh data. Please refresh the page.');
        }
      } else {
        // Show error toast based on error type
        if (errorType === 'already_linked') {
          showError('This GitHub account is already linked to another user');
        } else if (errorType === 'not_authenticated') {
          showError('You must be logged in to link your GitHub account');
        } else if (errorType === 'code_already_used') {
          showError('This authorization code has already been used. Please try again.');
        } else {
          showError('Failed to link GitHub account. Please try again.');
        }
      }
      isLinking = false;
    }

    // Create BroadcastChannel for OAuth communication
    if (oauthChannel) {
      oauthChannel.close();
    }

    oauthChannel = new BroadcastChannel('github_oauth');

    oauthChannel.onmessage = async (event) => {
      if (event.data.type === 'github_oauth_success' || event.data.type === 'github_oauth_error') {
        const success = event.data.type === 'github_oauth_success';
        const errorType = event.data.error || '';
        await handleOAuthResult(success, errorType);

        // Close channel after receiving message
        oauthChannel.close();
        oauthChannel = null;
      }
    };

    // Fallback: Check when popup closes
    const popupChecker = setInterval(async () => {
      if (popup.closed) {
        clearInterval(popupChecker);

        // Wait a moment for any async operations to complete
        await new Promise(resolve => setTimeout(resolve, 300));

        try {
          // Try to get updated user data
          const currentUser = await getCurrentUser();

          // Only show success if GitHub username changed (was newly linked)
          if (currentUser.github_username && currentUser.github_username !== initialGithubUsername) {
            showSuccess(`GitHub account linked successfully! (@${currentUser.github_username})`);
            onLinked(currentUser);
          }
        } catch (err) {
          // Silently handle reload error
        } finally {
          isLinking = false;
        }

        // Clean up channel
        if (oauthChannel) {
          oauthChannel.close();
          oauthChannel = null;
        }
      }
    }, 500);
  }
</script>

<button
  onclick={linkGitHub}
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
    <svg class="w-3 h-3 mr-2" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M10 0C4.477 0 0 4.477 0 10c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.604-3.369-1.341-3.369-1.341-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0110 4.836c.85.004 1.705.115 2.504.337 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C17.137 18.163 20 14.418 20 10c0-5.523-4.477-10-10-10z" clip-rule="evenodd"/>
    </svg>
    {buttonText}
  {/if}
</button>
