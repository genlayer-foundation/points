<script>
  import { authState } from '../lib/auth';
  import { getCurrentUser } from '../lib/api';
  import { showSuccess, showError } from '../lib/toastStore';

  let {
    platform = '',
    platformLabel = '',
    connection = null,
    initiateUrl = '',
    onLinked = () => {},
    compact = false,
  } = $props();

  let isLinking = $state(false);
  let oauthWindow = $state(null);
  let popupMonitor = $state(null);
  let handledOAuthResult = $state(false);

  const storageKey = `oauth_result_${platform}`;
  // Global flag per platform to prevent duplicate toasts across multiple SocialLink instances
  const handledFlag = `oauth_handled_${platform}`;

  function clearPopupMonitor() {
    if (popupMonitor) {
      clearInterval(popupMonitor);
      popupMonitor = null;
    }
    oauthWindow = null;
  }

  function reserveToastSlot() {
    const shouldToast = !sessionStorage.getItem(handledFlag);
    if (shouldToast) {
      sessionStorage.setItem(handledFlag, '1');
      setTimeout(() => sessionStorage.removeItem(handledFlag), 3000);
    }
    return shouldToast;
  }

  // Listen for localStorage changes from the OAuth return tab (same origin)
  // App.svelte detects the OAuth redirect params and writes to localStorage before routes mount
  function onStorageEvent(e) {
    if (e.key !== storageKey || !e.newValue) return;
    const result = JSON.parse(e.newValue);
    localStorage.removeItem(storageKey);
    handleOAuthReturn(result.verified === 'true', result.error || '');
  }

  $effect(() => {
    window.addEventListener('storage', onStorageEvent);
    return () => {
      window.removeEventListener('storage', onStorageEvent);
      clearPopupMonitor();
    };
  });

  function handleOAuthReturn(success, oauthError, currentUser = null) {
    handledOAuthResult = true;
    clearPopupMonitor();

    // Deduplicate toasts — only the first instance for this platform shows them
    const shouldToast = reserveToastSlot();

    if (success) {
      const userPromise = currentUser ? Promise.resolve(currentUser) : getCurrentUser();
      userPromise.then((resolvedUser) => {
        if (shouldToast) {
          const connData = resolvedUser?.[`${platform}_connection`];
          const username = connData?.platform_username || '';
          showSuccess(`${platformLabel} account linked successfully!${username ? ` (@${username})` : ''}`);
        }
        onLinked(resolvedUser);
        isLinking = false;
      }).catch(() => {
        if (shouldToast) {
          showSuccess(`${platformLabel} account linked! Please refresh to see changes.`);
        }
        isLinking = false;
      });
    } else {
      if (shouldToast) {
        if (oauthError === 'already_linked') {
          showError(`This ${platformLabel} account is already linked to another user`);
        } else if (oauthError === 'authorization_failed') {
          showError(`${platformLabel} authorization was cancelled or failed`);
        } else {
          showError(`Failed to link ${platformLabel} account. Please try again.`);
        }
      }
      isLinking = false;
    }
  }

  async function reconcileAfterPopupClose() {
    if (!isLinking || handledOAuthResult) return;

    // Poll a few times — the backend may still be processing the OAuth exchange
    // or the storage event from App.svelte may arrive between retries.
    const maxAttempts = 3;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      if (handledOAuthResult) return; // storage event arrived between retries
      try {
        const currentUser = await getCurrentUser();
        if (currentUser?.[`${platform}_connection`]?.platform_username) {
          handleOAuthReturn(true, '', currentUser);
          return;
        }
      } catch {
        // Network/auth error — keep retrying.
      }
      if (attempt < maxAttempts - 1) {
        await new Promise((r) => setTimeout(r, 1000));
      }
    }

    // All retries exhausted and no storage event arrived — silently reset.
    // The user can try again; we avoid false-positive error toasts.
    if (!handledOAuthResult) {
      isLinking = false;
    }
  }

  // Platform brand config
  const platformConfig = {
    github: {
      color: '#24292f',
      hoverColor: '#1b1f23',
      icon: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/></svg>`,
    },
    twitter: {
      color: '#000000',
      hoverColor: '#333333',
      icon: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
    },
    discord: {
      color: '#5865F2',
      hoverColor: '#4752C4',
      icon: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg>`,
    },
  };

  let config = $derived(platformConfig[platform] || platformConfig.github);

  async function linkAccount() {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }

    handledOAuthResult = false;
    isLinking = true;

    const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const redirectUrl = encodeURIComponent(window.location.href);
    const oauthUrl = `${backendUrl}${initiateUrl}?redirect=${redirectUrl}`;

    clearPopupMonitor();
    oauthWindow = window.open(oauthUrl, '_blank');
    if (!oauthWindow) {
      isLinking = false;
      showError(`Failed to open ${platformLabel} authorization window. Please allow pop-ups and try again.`);
      return;
    }

    popupMonitor = setInterval(() => {
      if (!oauthWindow || oauthWindow.closed) {
        clearPopupMonitor();
        // Wait 1.5 s — the popup's App.svelte needs time to load, write to
        // localStorage, and for the storage event to propagate.  The original
        // 300 ms was too aggressive in production.
        setTimeout(() => {
          reconcileAfterPopupClose();
        }, 1500);
      }
    }, 500);
  }


</script>

{#if compact}
  <!-- Compact mode: small pill for Profile header -->
  {#if connection}
    <div class="social-pill" style="--brand-color: {config.color};">
      <span class="social-pill-icon">{@html config.icon}</span>
      <span class="social-pill-name">{connection.platform_username}</span>
    </div>
  {:else}
    <button
      onclick={linkAccount}
      disabled={isLinking}
      class="social-pill social-pill-link"
      style="--brand-color: {config.color};"
    >
      {#if isLinking}
        <svg class="animate-spin w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      {:else}
        <span class="social-pill-icon">{@html config.icon}</span>
        <span class="social-pill-name">Link {platformLabel}</span>
      {/if}
    </button>
  {/if}
{:else}
  <!-- Full mode: for ProfileEdit -->
  {#if connection}
    <div
      class="px-4 py-3 rounded-[8px] text-white flex items-center gap-2.5"
      style="background-color: {config.color};"
    >
      <span class="flex-shrink-0 opacity-90">{@html config.icon}</span>
      <span class="font-medium text-sm">{connection.platform_username}</span>
    </div>
    {#if connection.linked_at}
      <p class="text-xs text-gray-400 mt-1">
        Linked on {new Date(connection.linked_at).toLocaleDateString()}
      </p>
    {/if}
  {:else}
    <button
      onclick={linkAccount}
      disabled={isLinking}
      class="social-connect-btn"
      style="--brand-color: {config.color}; --brand-hover: {config.hoverColor};"
    >
      {#if isLinking}
        <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>Connecting...</span>
      {:else}
        <span class="flex-shrink-0">{@html config.icon}</span>
        <span>Connect {platformLabel}</span>
      {/if}
    </button>
  {/if}
{/if}

<style>
  /* Full connect button (ProfileEdit) */
  .social-connect-btn {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    font-weight: 500;
    font-size: 0.875rem;
    color: white;
    background-color: var(--brand-color);
    border: none;
    cursor: pointer;
    transition: background-color 0.15s, opacity 0.15s;
  }

  .social-connect-btn:hover:not(:disabled) {
    background-color: var(--brand-hover);
  }

  .social-connect-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Compact pill (ProfileHeader) */
  .social-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 6px;
    background: white;
    border: 1px solid #f0f0f0;
    font-size: 13px;
    font-weight: 500;
    color: #1a1a1a;
    transition: background-color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }

  .social-pill-link {
    cursor: pointer;
    color: #888;
    border: 1px dashed #d0d0d0;
    background: #fafafa;
  }

  .social-pill-link:hover:not(:disabled) {
    border-color: var(--brand-color);
    color: var(--brand-color);
    background: white;
  }

  .social-pill-link:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .social-pill-icon {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .social-pill-icon :global(svg) {
    width: 14px;
    height: 14px;
  }

  .social-pill-name {
    letter-spacing: 0.28px;
    line-height: 1;
  }
</style>
