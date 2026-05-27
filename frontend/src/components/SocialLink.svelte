<script>
  import { onMount, onDestroy } from 'svelte';
  import { authState } from '../lib/auth';
  import { API_BASE_URL } from '../lib/config.js';
  import { getCurrentUser, socialAPI } from '../lib/api';
  import { showSuccess, showError } from '../lib/toastStore';

  let {
    platform = '',
    platformLabel = '',
    connection = null,
    initiateUrl = '',
    onLinked = () => {},
    compact = false,
    allowUsernameRefresh = false,
  } = $props();

  let isLinking = $state(false);
  let isRefreshing = $state(false);
  let handledOAuthResult = $state(false);

  // Imperative bookkeeping — plain let, NOT $state, to avoid Svelte 5
  // reactivity issues (effect re-runs clearing the monitor prematurely).
  let oauthWindow = null;
  let popupMonitor = null;

  const storageKey = `oauth_result_${platform}`;
  const handledFlag = `oauth_handled_${platform}`;
  const pendingFlag = `oauth_pending_${platform}`;
  const modeFlag = `oauth_mode_${platform}`;

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

  function markOAuthPending() {
    sessionStorage.setItem(pendingFlag, '1');
  }

  function clearOAuthPending() {
    sessionStorage.removeItem(pendingFlag);
    sessionStorage.removeItem(modeFlag);
  }

  function hasPendingOAuth() {
    return isLinking || isRefreshing || sessionStorage.getItem(pendingFlag) === '1';
  }

  // --- Event handlers ---

  // Primary: postMessage from the OAuth popup
  function onMessageEvent(e) {
    if (e.data?.type !== 'oauth_result') return;
    if (e.data?.platform !== platform) return;
    if (!hasPendingOAuth()) return;
    handleOAuthReturn(e.data.verified === 'true', e.data.error || '');
  }

  // Fallback: localStorage storage event (Safari may clear window.opener)
  function onStorageEvent(e) {
    if (e.key !== storageKey || !e.newValue) return;
    if (!hasPendingOAuth()) return;
    localStorage.removeItem(storageKey);
    try {
      const result = JSON.parse(e.newValue);
      handleOAuthReturn(result.verified === 'true', result.error || '');
    } catch {
      handleOAuthReturn(false, 'authorization_failed');
    }
  }

  // Lifecycle — use onMount/onDestroy (not $effect) to avoid reactive
  // dependency tracking on the cleanup's reads of popupMonitor/oauthWindow.
  onMount(() => {
    window.addEventListener('message', onMessageEvent);
    window.addEventListener('storage', onStorageEvent);
    consumeStoredOAuthResult();
  });

  onDestroy(() => {
    window.removeEventListener('message', onMessageEvent);
    window.removeEventListener('storage', onStorageEvent);
    clearPopupMonitor();
  });

  function handleOAuthReturn(success, oauthError, currentUser = null) {
    // Prevent double-processing from multiple OAuth return channels.
    if (handledOAuthResult) {
      clearOAuthPending();
      return;
    }
    handledOAuthResult = true;
    const wasRefreshing = isRefreshing || sessionStorage.getItem(modeFlag) === 'refresh_username';
    clearPopupMonitor();
    clearOAuthPending();

    const shouldToast = reserveToastSlot();

    if (success) {
      const userPromise = currentUser ? Promise.resolve(currentUser) : getCurrentUser();
      userPromise.then((resolvedUser) => {
        if (shouldToast) {
          const connData = resolvedUser?.[`${platform}_connection`];
          const username = connData?.platform_username || '';
          if (wasRefreshing) {
            const previousUsername = connection?.platform_username || '';
            showSuccess(
              username && previousUsername && username !== previousUsername
                ? `${platformLabel} username updated to ${username}`
                : `${platformLabel} username is already up to date`
            );
          } else {
            showSuccess(`${platformLabel} account linked successfully!${username ? ` (@${username})` : ''}`);
          }
        }
        onLinked(resolvedUser);
        isLinking = false;
        isRefreshing = false;
      }).catch(() => {
        if (shouldToast) {
          showSuccess(
            wasRefreshing
              ? `${platformLabel} username refreshed! Please reload to see changes.`
              : `${platformLabel} account linked! Please refresh to see changes.`
          );
        }
        isLinking = false;
        isRefreshing = false;
      });
    } else {
      if (shouldToast) {
        if (oauthError === 'already_linked') {
          showError(
            wasRefreshing
              ? `This ${platformLabel} account is linked to another user`
              : `This ${platformLabel} account is already linked to another user`
          );
        } else if (oauthError === 'account_mismatch') {
          showError(`This ${platformLabel} account does not match the account already linked`);
        } else if (oauthError === 'authorization_failed') {
          showError(`${platformLabel} authorization was cancelled or failed`);
        } else {
          showError(
            wasRefreshing
              ? `Failed to refresh ${platformLabel} username. Please try again.`
              : `Failed to link ${platformLabel} account. Please try again.`
          );
        }
      }
      isLinking = false;
      isRefreshing = false;
    }
  }

  async function reconcileAfterPopupClose() {
    if ((!isLinking && !isRefreshing) || handledOAuthResult) return;

    // Check localStorage first — the popup writes here, and the storage event
    // may have been missed (same-tab writes don't fire storage events; the
    // popup IS a different window, but race conditions can cause misses).
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      localStorage.removeItem(storageKey);
      const result = JSON.parse(stored);
      handleOAuthReturn(result.verified === 'true', result.error || '');
      return;
    }

    const maxAttempts = 3;
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      if (handledOAuthResult) return;
      try {
        const currentUser = await getCurrentUser();
        if (!isRefreshing && currentUser?.[`${platform}_connection`]?.platform_username) {
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

    if (!handledOAuthResult) {
      handleOAuthReturn(false, 'authorization_failed');
    }
  }

  // Platform brand config
  const platformConfig = {
    github: {
      color: '#24292f',
      hoverColor: '#1b1f23',
      icon: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/></svg>`,
      profileUrl: (username) => `https://github.com/${username}`,
    },
    twitter: {
      color: '#000000',
      hoverColor: '#333333',
      icon: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>`,
      profileUrl: (username) => `https://x.com/${username}`,
    },
    discord: {
      color: '#5865F2',
      hoverColor: '#4752C4',
      icon: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg>`,
      profileUrl: null,
    },
  };

  let config = $derived(platformConfig[platform] || platformConfig.github);
  let discordRoles = $derived.by(() => {
    if (platform !== 'discord') return [];
    return [...(connection?.roles || [])].sort((a, b) => (b.position || 0) - (a.position || 0) || String(a.name).localeCompare(String(b.name)));
  });
  let hasDiscordRank = $derived(platform === 'discord' && connection?.mee6_rank !== null && connection?.mee6_rank !== undefined);
  let hasDiscordLevel = $derived(platform === 'discord' && connection?.mee6_level !== null && connection?.mee6_level !== undefined);
  let hasDiscordLeaderboardStats = $derived(hasDiscordRank || hasDiscordLevel);
  let compactTitle = $derived.by(() => {
    if (platform !== 'discord' || !connection) return undefined;
    const stats = [];
    if (hasDiscordLevel) stats.push(`level ${formatNumber(connection.mee6_level)}`);
    if (hasDiscordRank) stats.push(`rank #${formatNumber(connection.mee6_rank)}`);
    const roles = discordRoles.length > 0
      ? `Discord roles: ${discordRoles.map((role) => role.name).join(', ')}`
      : 'Discord roles not synced yet';
    return stats.length ? `Discord ${stats.join(', ')}. ${roles}` : roles;
  });

  function getDiscordRoleColor(role) {
    if (role?.color && role.color > 0 && role.color_hex) {
      return role.color_hex;
    }
    return '#b5bac1';
  }

  function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return value;
    return new Intl.NumberFormat().format(number);
  }

  const refreshHandlers = {
    github: socialAPI.refreshGitHubUsername,
    discord: socialAPI.refreshDiscordUsername,
  };
  let canRefresh = $derived(allowUsernameRefresh && (platform === 'twitter' || !!refreshHandlers[platform]));

  function isMobileBrowser() {
    const userAgent = navigator.userAgent || navigator.vendor || window.opera || '';
    const touchDesktopTablet =
      navigator.maxTouchPoints > 1 && /macintosh/i.test(userAgent);
    return /android|iphone|ipad|ipod/i.test(userAgent) || touchDesktopTablet;
  }

  function getCurrentRedirectUrl() {
    return `${window.location.origin}${window.location.pathname}${window.location.search || ''}${window.location.hash || ''}`;
  }

  function consumeStoredOAuthResult() {
    if (!hasPendingOAuth()) return;

    const stored = localStorage.getItem(storageKey);
    if (!stored) return;

    localStorage.removeItem(storageKey);
    try {
      const result = JSON.parse(stored);
      handleOAuthReturn(result.verified === 'true', result.error || '');
    } catch {
      handleOAuthReturn(false, 'authorization_failed');
    }
  }

  async function linkAccount({ refreshUsername = false } = {}) {
    if (!$authState.isAuthenticated) {
      document.querySelector('.auth-button')?.click();
      return;
    }

    handledOAuthResult = false;
    isLinking = !refreshUsername;
    isRefreshing = refreshUsername;
    localStorage.removeItem(storageKey);
    markOAuthPending();
    sessionStorage.setItem(modeFlag, refreshUsername ? 'refresh_username' : 'link');

    const redirectUrl = encodeURIComponent(getCurrentRedirectUrl());
    const oauthUrl = `${API_BASE_URL}${initiateUrl}?redirect=${redirectUrl}`;

    if (isMobileBrowser()) {
      window.location.assign(oauthUrl);
      return;
    }

    clearPopupMonitor();
    oauthWindow = window.open(oauthUrl, 'oauth_popup');
    if (!oauthWindow) {
      window.location.assign(oauthUrl);
      return;
    }

    popupMonitor = setInterval(() => {
      if (!oauthWindow || oauthWindow.closed) {
        clearPopupMonitor();
        setTimeout(() => {
          reconcileAfterPopupClose();
        }, 1500);
      }
    }, 500);
  }

  async function refreshAccount() {
    if (!$authState.isAuthenticated || !canRefresh || !connection || isRefreshing || isLinking) {
      return;
    }

    if (platform === 'twitter') {
      await linkAccount({ refreshUsername: true });
      return;
    }

    isRefreshing = true;
    try {
      const response = await refreshHandlers[platform]();
      const updatedUser = await getCurrentUser();
      const updatedConnection = response.data?.[`${platform}_connection`];
      const username = updatedConnection?.platform_username || connection.platform_username;
      showSuccess(
        response.data?.changed
          ? `${platformLabel} username updated to ${username}`
          : `${platformLabel} username is already up to date`
      );
      onLinked(updatedUser);
    } catch (error) {
      const message = error?.response?.data?.error || `Failed to refresh ${platformLabel} username. Please try again.`;
      showError(message);
    } finally {
      isRefreshing = false;
    }
  }
</script>

{#if compact}
  <!-- Compact mode: small pill for Profile header -->
  {#if connection}
    {#if config.profileUrl}
      <a
        href={config.profileUrl(connection.platform_username)}
        target="_blank"
        rel="noopener noreferrer"
        class="social-pill social-pill-clickable"
        style="--brand-color: {config.color};"
        title={compactTitle}
      >
        <span class="social-pill-icon">{@html config.icon}</span>
        <span class="social-pill-name">{connection.platform_username}</span>
      </a>
    {:else}
      <button
        type="button"
        class="social-pill"
        class:discord-role-tooltip-wrap={platform === 'discord'}
        style="--brand-color: {config.color};"
        aria-label={compactTitle}
      >
        <span class="social-pill-icon">{@html config.icon}</span>
        <span class="social-pill-name">{connection.platform_username}</span>
        {#if platform === 'discord'}
          <div class="discord-role-tooltip">
            {#if hasDiscordLeaderboardStats}
              <div class="discord-xp-summary">
                {#if hasDiscordLevel}
                  <div class="discord-xp-stat">
                    <span class="discord-xp-label">Level</span>
                    <span class="discord-xp-value">{formatNumber(connection.mee6_level)}</span>
                  </div>
                {/if}
                {#if hasDiscordRank}
                  <div class="discord-xp-stat">
                    <span class="discord-xp-label">Rank</span>
                    <span class="discord-xp-value">#{formatNumber(connection.mee6_rank)}</span>
                  </div>
                {/if}
              </div>
            {/if}
            <span class="discord-role-heading">Roles</span>
            {#if discordRoles.length > 0}
              <div class="discord-role-list">
                {#each discordRoles as role}
                  <span class="discord-role-chip">
                    <span class="discord-role-dot" style="--role-color: {getDiscordRoleColor(role)}"></span>
                    <span class="discord-role-name">{role.name}</span>
                  </span>
                {/each}
              </div>
            {:else}
              <span class="discord-role-empty">Roles not synced yet</span>
            {/if}
          </div>
        {/if}
      </button>
    {/if}
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
        <span class="social-pill-prefix">Link</span>
        <span class="social-pill-name">{platformLabel}</span>
      {/if}
    </button>
  {/if}
{:else}
  <!-- Full mode: for ProfileEdit -->
  {#if connection}
    <div
      class="social-connected-row"
      style="background-color: {config.color};"
    >
      <div class="social-connected-identity">
        <span class="flex-shrink-0 opacity-90">{@html config.icon}</span>
        <span class="font-medium text-sm">{connection.platform_username}</span>
      </div>
      {#if canRefresh}
        <button
          type="button"
          class="social-refresh-btn"
          onclick={refreshAccount}
          disabled={isRefreshing}
          title="Refresh {platformLabel} username"
          aria-label="Refresh {platformLabel} username"
        >
          {#if isRefreshing}
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          {:else}
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 12a9 9 0 0 0-15-6.7L3 8"></path>
              <path d="M3 3v5h5"></path>
              <path d="M3 12a9 9 0 0 0 15 6.7l3-2.7"></path>
              <path d="M21 21v-5h-5"></path>
            </svg>
          {/if}
        </button>
      {/if}
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

  .social-connected-row {
    width: 100%;
    min-height: 44px;
    padding: 0.625rem 0.75rem 0.625rem 1rem;
    border-radius: 8px;
    color: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .social-connected-identity {
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 0.625rem;
  }

  .social-connected-identity span:last-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .social-refresh-btn {
    width: 30px;
    height: 30px;
    flex: 0 0 30px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.26);
    background: rgba(255, 255, 255, 0.12);
    color: white;
    cursor: pointer;
    transition: background-color 0.15s, border-color 0.15s, opacity 0.15s;
  }

  .social-refresh-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.42);
  }

  .social-refresh-btn:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }

  /* Compact pill (ProfileHeader) */
  .social-pill {
    position: relative;
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

  .social-pill.discord-role-tooltip-wrap {
    cursor: default;
    transition:
      transform 0.16s ease,
      border-color 0.16s ease,
      background-color 0.16s ease,
      box-shadow 0.16s ease;
  }

  .social-pill.discord-role-tooltip-wrap:hover,
  .social-pill.discord-role-tooltip-wrap:focus-visible {
    background: #fbfbff;
    border-color: #d8dafb;
    box-shadow: 0 6px 16px rgba(88, 101, 242, 0.12);
    outline: none;
    transform: translateY(-1px);
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

  .social-pill-clickable {
    cursor: pointer;
    text-decoration: none;
  }

  .social-pill-clickable:hover {
    background: #f7f7f7;
    border-color: var(--brand-color);
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
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .discord-role-tooltip {
    display: flex;
    position: absolute;
    left: calc(100% + 10px);
    top: 50%;
    transform: translate(4px, -50%) scale(0.98);
    width: max-content;
    min-width: 220px;
    max-width: min(360px, calc(100vw - 32px));
    background: #24242c;
    border: 1px solid #34343e;
    border-radius: 14px;
    padding: 16px;
    z-index: 80;
    flex-direction: column;
    gap: 12px;
    opacity: 0;
    pointer-events: none;
    visibility: hidden;
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
    transition:
      opacity 0.14s ease,
      transform 0.14s ease,
      visibility 0.14s ease;
  }

  .discord-role-tooltip::before {
    content: '';
    position: absolute;
    right: 100%;
    top: 50%;
    transform: translateY(-50%);
    border: 5px solid transparent;
    border-right-color: #24242c;
  }

  .discord-role-tooltip-wrap:hover .discord-role-tooltip,
  .discord-role-tooltip-wrap:focus-visible .discord-role-tooltip {
    opacity: 1;
    transform: translate(0, -50%) scale(1);
    visibility: visible;
  }

  .discord-role-heading {
    color: #f6f6f7;
    font-size: 14px;
    font-weight: 650;
    line-height: 1.1;
  }

  .discord-xp-summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .discord-xp-stat {
    min-width: 0;
    border: 1px solid #393943;
    border-radius: 8px;
    background: rgba(88, 101, 242, 0.16);
    padding: 9px 10px;
  }

  .discord-xp-label {
    display: block;
    color: #b5bac1;
    font-size: 11px;
    font-weight: 600;
    line-height: 1;
    text-transform: uppercase;
  }

  .discord-xp-value {
    display: block;
    margin-top: 5px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
  }

  .discord-role-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .discord-role-chip {
    min-width: 0;
    max-width: 100%;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border: 1px solid #393943;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.035);
    padding: 7px 10px;
    color: #f4f4f5;
    font-size: 13px;
    font-weight: 500;
    line-height: 1;
  }

  .discord-role-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .discord-role-dot {
    width: 12px;
    height: 12px;
    flex: 0 0 12px;
    border-radius: 999px;
    background: var(--role-color);
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.06);
  }

  .discord-role-empty {
    color: #b5bac1;
    font-size: 13px;
    line-height: 1.35;
  }

  @media (max-width: 767px) {
    .social-connect-btn {
      min-height: 40px;
      padding: 0.625rem 0.75rem;
      font-size: 0.8125rem;
      white-space: nowrap;
    }

    .social-connect-btn span:last-child {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .social-pill {
      width: 100%;
      min-width: 0;
      min-height: 32px;
      justify-content: center;
      padding: 0.375rem 0.4375rem;
      font-size: 0.71875rem;
      gap: 3px;
    }

    .social-pill-prefix {
      display: none;
    }
  }

  @media (hover: none) and (pointer: coarse) {
    .discord-role-tooltip-wrap:hover .discord-role-tooltip,
    .discord-role-tooltip-wrap:focus-visible .discord-role-tooltip {
      opacity: 0;
      visibility: hidden;
    }
  }
</style>
