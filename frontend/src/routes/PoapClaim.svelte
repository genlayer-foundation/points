<script>
  import { onMount, onDestroy } from 'svelte';
  import { params, push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { poapsAPI } from '../lib/api.js';
  import { clearPoapClaimRedirect } from '../lib/poapRedirect.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import SocialLink from '../components/SocialLink.svelte';
  import PoapBadgeImage from '../components/poaps/PoapBadgeImage.svelte';

  let status = $state('idle');
  let message = $state('Preparing claim...');
  /** @type {any} */
  let drop = $state(null);
  let attempted = $state(false);

  let routeToken = $derived($params?.token || '');
  let token = $derived(routeToken || tokenFromUrl());
  let requiresDiscordLink = $derived(
    status === 'error' && message.toLowerCase().includes('discord')
  );
  let discordConnection = $derived($userStore.user?.discord_connection || null);

  function tokenFromUrl() {
    if (typeof window === 'undefined') return '';
    const pathMatch = window.location.pathname.match(/^\/claim\/poap\/([^/?#]+)/);
    const rawToken = pathMatch?.[1] || '';
    try {
      return decodeURIComponent(rawToken);
    } catch {
      return rawToken;
    }
  }

  /** @param {any} err */
  function isDiscordLinkError(err) {
    return err?.response?.status === 403
      && String(err?.response?.data?.error || '').toLowerCase().includes('discord');
  }

  /** @param {any} err */
  function isAuthError(err) {
    const statusCode = err?.response?.status;
    if (isDiscordLinkError(err)) return false;
    return statusCode === 401 || statusCode === 403;
  }

  function requestLogin() {
    const claimToken = token;
    if (!claimToken) {
      status = 'error';
      message = 'This mint link is missing its claim token.';
      showError(message);
      return;
    }
    sessionStorage.setItem('redirectAfterLogin', `/claim/poap/${claimToken}`);
    window.setTimeout(() => {
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton instanceof HTMLElement) authButton.click();
    }, 0);
  }

  async function claim() {
    if (attempted || !$authState.isAuthenticated) return;
    const claimToken = token;
    if (!claimToken) {
      status = 'error';
      message = 'This mint link is missing its claim token.';
      showError(message);
      return;
    }
    attempted = true;
    status = 'claiming';
    message = 'Claiming your POAP...';
    try {
      const response = await poapsAPI.claimLink(claimToken);
      drop = response.data?.drop;
      clearPoapClaimRedirect(claimToken);
      status = 'claimed';
      message = 'POAP claimed. Opening the details...';
      showSuccess('POAP claimed.');
      if (drop?.slug) {
        window.setTimeout(() => {
          // Don't redirect if the user already navigated away mid-claim.
          if (!destroyed) push(`/community/poaps/${drop.slug}`);
        }, 900);
      }
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      if (isAuthError(requestError)) {
        attempted = false;
        status = 'auth';
        message = 'Connect your wallet to claim this POAP.';
        authState.setAuthenticated(false, null);
        authState.resetVerification();
        requestLogin();
        return;
      }
      if (!isDiscordLinkError(requestError)) {
        clearPoapClaimRedirect(claimToken);
      }
      status = 'error';
      message = requestError.response?.data?.error || 'This mint link is invalid or no longer available.';
      showError(message);
    }
  }

  /** @param {any} updatedUser */
  function handleDiscordLinked(updatedUser) {
    if (updatedUser) userStore.setUser(updatedUser);
    if (!token) return;
    attempted = false;
    status = 'claiming';
    message = 'Claiming your POAP...';
    window.setTimeout(() => {
      claim();
    }, 0);
  }

  // Set once unmounted, so the post-claim redirect doesn't fire after leaving.
  let destroyed = false;
  onDestroy(() => { destroyed = true; });

  onMount(() => {
    if (!$authState.isAuthenticated) {
      status = 'auth';
      message = 'Connect your wallet to claim this POAP.';
      requestLogin();
    } else {
      claim();
    }
  });

  $effect(() => {
    if ($authState.isAuthenticated && status === 'auth') {
      claim();
    }
  });

  $effect(() => {
    if ($authState.isAuthenticated && !$userStore.user && !$userStore.loading) {
      userStore.loadUser().catch(() => {});
    }
  });

  function heading() {
    if (status === 'claimed') return 'POAP claimed';
    if (requiresDiscordLink) return 'Link Discord';
    if (status === 'error') return 'Mint link not available';
    if (status === 'auth') return 'Connect wallet';
    return 'Claim POAP';
  }

  function statusText() {
    if (status === 'claimed') return 'Claimed';
    if (requiresDiscordLink) return 'Discord required';
    if (status === 'error') return 'Unavailable';
    if (status === 'claiming') return 'Claiming';
    if (status === 'auth') return 'Wallet required';
    return 'Mint link';
  }
</script>

<div class="poap-claim-page">
  <section class:error={status === 'error'} class:claimed={status === 'claimed'} class="poap-claim-card">
    <div class="poap-claim-art">
      <PoapBadgeImage src={drop?.artwork_url} title={drop?.title || 'POAP'} size="lg" claimed={status === 'claimed'} />
    </div>

    <div class="poap-claim-copy">
      <span class="poap-claim-status">{statusText()}</span>
      <h1>{heading()}</h1>
      <p>{message}</p>

      {#if drop}
        <div class="poap-claim-drop">{drop.title}</div>
      {/if}

      <div class="poap-claim-actions">
        {#if status === 'auth'}
          <button class="poap-primary-action" onclick={requestLogin}>Connect wallet</button>
        {:else if status === 'claimed' && drop?.slug}
          <button class="poap-primary-action" onclick={() => push(`/community/poaps/${drop.slug}`)}>View POAP</button>
        {:else if requiresDiscordLink}
          <div class="poap-discord-gate">
            <SocialLink
              platform="discord"
              platformLabel="Discord"
              connection={discordConnection}
              initiateUrl="/api/auth/discord/"
              onLinked={handleDiscordLinked}
            />
          </div>
        {:else if status === 'error'}
          <button class="poap-secondary-action" onclick={() => push('/community/poaps')}>Browse POAPs</button>
        {/if}
      </div>
    </div>
  </section>
</div>

<style>
  .poap-claim-page {
    align-items: center;
    display: flex;
    justify-content: center;
    min-height: calc(100vh - 120px);
    padding: 48px 16px;
  }

  .poap-claim-card {
    align-items: center;
    background: rgba(255, 255, 255, 0.96);
    border: 1.5px solid rgba(127, 82, 225, 0.28);
    border-radius: 22px;
    box-shadow: 0 20px 58px rgba(38, 48, 75, 0.12);
    display: grid;
    gap: 26px;
    grid-template-columns: 178px minmax(0, 1fr);
    max-width: 650px;
    padding: 18px;
    width: 100%;
  }

  .poap-claim-card.error {
    border-color: rgba(202, 190, 255, 0.62);
  }

  .poap-claim-card.claimed {
    border-color: rgba(25, 166, 99, 0.28);
  }

  .poap-claim-art {
    align-items: center;
    background: #f8f5ff;
    border-radius: 18px;
    display: flex;
    justify-content: center;
    min-height: 178px;
  }

  .poap-claim-copy {
    min-width: 0;
    padding: 8px 8px 8px 0;
  }

  .poap-claim-status {
    background: #fbfaff;
    border: 1px solid #e8e3ff;
    border-radius: 999px;
    color: #5f5785;
    display: inline-flex;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1;
    padding: 7px 10px;
    text-transform: uppercase;
  }

  .poap-claim-card.claimed .poap-claim-status {
    background: #f2fbf5;
    border-color: #d8f0df;
    color: #167b48;
  }

  .poap-claim-copy h1 {
    color: #151329;
    font-family: var(--font-display, inherit);
    font-size: clamp(28px, 4vw, 42px);
    font-weight: 780;
    letter-spacing: 0;
    line-height: 1.04;
    margin: 16px 0 0;
  }

  .poap-claim-copy p {
    color: #4f5572;
    font-size: 15px;
    line-height: 23px;
    margin: 12px 0 0;
  }

  .poap-claim-drop {
    background: #fff;
    border: 1px solid rgba(127, 82, 225, 0.16);
    border-radius: 14px;
    color: #101010;
    font-size: 14px;
    font-weight: 700;
    line-height: 18px;
    margin-top: 18px;
    padding: 12px 14px;
  }

  .poap-claim-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 22px;
  }

  .poap-discord-gate {
    width: min(100%, 260px);
  }

  .poap-primary-action,
  .poap-secondary-action {
    border-radius: 12px;
    font-size: 14px;
    font-weight: 700;
    height: 42px;
    padding: 0 16px;
  }

  .poap-primary-action {
    background: #7f52e1;
    color: #fff;
  }

  .poap-secondary-action {
    background: #fff;
    border: 1px solid #d9d2ff;
    color: #6b5bd6;
  }

  @media (max-width: 640px) {
    .poap-claim-card {
      grid-template-columns: 1fr;
      max-width: 420px;
    }

    .poap-claim-copy {
      padding: 0 4px 6px;
      text-align: center;
    }

    .poap-claim-actions {
      justify-content: center;
    }
  }
</style>
