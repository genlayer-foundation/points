<script>
  import { ethers } from 'ethers';
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { getCurrentUser, poapsAPI } from '../lib/api.js';
  import {
    authState,
    getNonce,
    setWalletAccountChangeHandlingSuppressed,
    verifyAuth,
  } from '../lib/auth.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import SocialLink from '../components/SocialLink.svelte';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';

  /** @type {any} */
  let currentUser = $state(null);
  let loading = $state(true);
  let verifying = $state(false);
  let verifiedAddress = $state('');
  /** @type {any} */
  let result = $state(null);
  let pageError = $state('');

  const poapGradientStyle = getCategoryGradientStyle('community', '#7f52e1');

  let portalAddress = $derived(currentUser?.address || $authState.address || '');
  let isAuthenticated = $derived(Boolean($authState.isAuthenticated && portalAddress));

  /** @param {string | null | undefined} value */
  function truncateAddress(value) {
    if (!value) return '-';
    return `${value.slice(0, 6)}...${value.slice(-4)}`;
  }

  function requestLogin() {
    sessionStorage.setItem('redirectAfterLogin', '/community/poaps/recover');
    window.setTimeout(() => {
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton instanceof HTMLElement) authButton.click();
    }, 0);
  }

  async function loadCurrentUser() {
    loading = true;
    pageError = '';
    try {
      authState.resetVerification();
      const authenticated = await verifyAuth();
      if (!authenticated) {
        currentUser = null;
        return;
      }
      currentUser = await getCurrentUser();
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      pageError = requestError.response?.data?.error || 'Unable to load your portal account.';
      currentUser = null;
    } finally {
      loading = false;
    }
  }

  /** @param {any} provider */
  async function requestRecoveryWallet(provider) {
    try {
      await provider.request({
        method: 'wallet_requestPermissions',
        params: [{ eth_accounts: {} }],
      });
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      const unsupportedMethod = requestError?.code === -32601 || /not supported|unsupported/i.test(requestError?.message || '');
      if (!unsupportedMethod) throw requestError;
    }

    let accounts = await provider.request({ method: 'eth_accounts' });
    if (!accounts || accounts.length === 0) {
      accounts = await provider.request({ method: 'eth_requestAccounts' });
    }
    if (!accounts || accounts.length === 0) {
      throw new Error('No wallet account selected.');
    }
    return ethers.getAddress(accounts[0]);
  }

  /** @param {any} provider */
  async function getChainId(provider) {
    try {
      const chainIdHex = await provider.request({ method: 'eth_chainId' });
      return chainIdHex ? parseInt(chainIdHex, 16) : 1;
    } catch {
      return 1;
    }
  }

  /**
   * @param {string} address
   * @param {string} nonce
   * @param {number} chainId
   */
  function buildRecoveryMessage(address, nonce, chainId) {
    const domain = window.location.host;
    const origin = window.location.origin;
    return `${domain} wants you to verify a wallet for GenLayer POAP recovery:
${address}

This signature only proves ownership of this wallet for attaching legacy POAPs to your current portal account. It will not sign you into the portal or change your account.

Portal Account: ${portalAddress}
URI: ${origin}
Version: 1
Chain ID: ${chainId}
Nonce: ${nonce}
Issued At: ${new Date().toISOString()}`;
  }

  /** @param {any} err */
  function isAuthError(err) {
    const statusCode = err?.response?.status;
    return statusCode === 401 || statusCode === 403;
  }

  async function verifyPoapWallet() {
    if (!isAuthenticated) {
      requestLogin();
      return;
    }
    if (!window.ethereum) {
      showError('No wallet detected. Please install or open your wallet.');
      return;
    }

    verifying = true;
    result = null;
    pageError = '';
    setWalletAccountChangeHandlingSuppressed(true);

    try {
      const provider = window.ethereum;
      const address = await requestRecoveryWallet(provider);
      verifiedAddress = address;
      const nonce = await getNonce('poap_recovery');
      const chainId = await getChainId(provider);
      const message = buildRecoveryMessage(address, nonce, chainId);
      const ethersProvider = new ethers.BrowserProvider(provider);
      const signer = await ethersProvider.getSigner(address);
      const signature = await signer.signMessage(message);

      const response = await poapsAPI.verifyWallet({
        address,
        message,
        signature,
      });
      result = response.data;
      if (portalAddress) {
        authState.setAuthenticated(true, portalAddress);
      }
      const count = response.data?.attached_count || 0;
      const skipped = response.data?.skipped_existing_drop_count || 0;
      showSuccess(
        count > 0
          ? `${count} POAP${count === 1 ? '' : 's'} recovered.`
          : skipped > 0
            ? 'Wallet verified. Matching POAPs were already on this account.'
            : 'Wallet verified. No new POAPs found.'
      );
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      if (isAuthError(requestError)) {
        authState.setAuthenticated(false, null);
        authState.resetVerification();
        requestLogin();
        return;
      }
      const message =
        requestError.response?.data?.error ||
        requestError.message ||
        'Unable to verify this wallet.';
      showError(message);
    } finally {
      verifying = false;
      window.setTimeout(() => setWalletAccountChangeHandlingSuppressed(false), 600);
    }
  }

  /** @param {any} updatedUser */
  function handleDiscordLinked(updatedUser) {
    currentUser = updatedUser;
  }

  onMount(() => {
    loadCurrentUser();
  });
</script>

<div class="relative -mx-3 -my-3 min-h-[calc(100vh-64px)] overflow-hidden bg-white px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[250px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={poapGradientStyle}></div>
    <div class="absolute inset-0 bg-white/48"></div>
  </div>

  <div class="relative z-10 mx-auto max-w-[980px] space-y-6">
    <button class="inline-flex items-center gap-2 text-[14px] font-medium text-[#6b5bd6] hover:text-[#4c3dbd]" onclick={() => push('/community/poaps')}>
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6" /></svg>
      Back to POAPs
    </button>

    <header class="flex min-w-0 items-start gap-3">
      <div class="mt-1 shrink-0">
        <CategoryIcon category="community" mode="hexagon" />
      </div>
      <div class="min-w-0">
        <h1 class="font-display text-[30px] font-semibold leading-none text-black sm:text-[38px] md:text-[44px]" style="letter-spacing: -1px;">Recover POAPs</h1>
        <p class="mt-2 max-w-[640px] text-[14px] leading-6 text-[#3f4b5f] sm:text-[15px]">
          Verify another wallet you control to attach legacy GenLayer POAPs to your current portal account.
        </p>
      </div>
    </header>

    {#if loading}
      <section class="rounded-[14px] border border-white/70 bg-white/86 p-6 shadow-[0_16px_42px_rgba(38,48,75,0.1)] animate-pulse">
        <div class="h-5 w-44 rounded bg-[#eee8ff]"></div>
        <div class="mt-5 grid gap-4 md:grid-cols-2">
          <div class="h-36 rounded-[12px] bg-[#f6f3ff]"></div>
          <div class="h-36 rounded-[12px] bg-[#f6f3ff]"></div>
        </div>
      </section>
    {:else if pageError}
      <section class="rounded-[12px] border border-[#f0d2d2] bg-[#fff7f7] p-5 text-[14px] text-[#9f2f2f]">{pageError}</section>
    {:else if !isAuthenticated}
      <section class="poap-recovery-card">
        <div>
          <p class="poap-kicker">Portal account</p>
          <h2>Sign in to recover POAPs</h2>
          <p class="poap-muted">You need to be connected to the portal first. The recovery wallet will only be used to prove ownership.</p>
        </div>
        <button class="poap-primary-action" onclick={requestLogin}>Connect portal wallet</button>
      </section>
    {:else}
      <section class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div class="poap-recovery-card">
          <div class="poap-card-heading">
            <span class="poap-icon">
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M19 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-2" />
                <path d="M16 12h6" />
                <path d="m19 9 3 3-3 3" />
              </svg>
            </span>
            <div>
              <p class="poap-kicker">Current portal wallet</p>
              <h2>{truncateAddress(portalAddress)}</h2>
            </div>
          </div>

          <div class="poap-verify-box">
            <div>
              <p class="poap-kicker">Recovery wallet</p>
              <p class="poap-muted">Select and sign with the wallet that originally collected the POAPs.</p>
            </div>
            <button class="poap-primary-action" disabled={verifying} onclick={verifyPoapWallet}>
              {verifying ? 'Verifying...' : 'Verify POAP wallet'}
            </button>
          </div>
        </div>

        <aside class="poap-recovery-card">
          <div class="poap-card-heading">
            <span class="poap-icon discord">
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M20.3 4.4a19.8 19.8 0 0 0-4.9-1.5l-.1.1c-.2.4-.4.8-.6 1.2a18.5 18.5 0 0 0-5.5 0c-.2-.4-.4-.9-.6-1.2l-.1-.1a19.7 19.7 0 0 0-4.9 1.5C.5 9 .1 13.5.5 18l.1.1a19.9 19.9 0 0 0 6 3c.1 0 .1 0 .2-.1.5-.6.9-1.3 1.2-2-.7-.2-1.3-.5-1.9-.9-.1-.1-.1-.1 0-.2l.4-.3h.1a13.2 13.2 0 0 0 12.1 0h.1l.4.3c.1.1.1.2 0 .2-.6.3-1.2.6-1.9.9.4.7.8 1.4 1.2 2 .1.1.1.1.2.1a19.9 19.9 0 0 0 6-3l.1-.1c.5-5.2-.8-9.7-3.5-13.6ZM8.1 15.3c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Zm8 0c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Z"/>
              </svg>
            </span>
            <div>
              <p class="poap-kicker">Optional</p>
              <h2>Discord</h2>
            </div>
          </div>
          <p class="poap-muted">Discord can stay linked for community context, but it does not block wallet recovery.</p>
          <div class="mt-4">
            <SocialLink
              platform="discord"
              platformLabel="Discord"
              connection={currentUser?.discord_connection}
              initiateUrl="/api/auth/discord/"
              onLinked={handleDiscordLinked}
              allowUsernameRefresh={true}
            />
          </div>
        </aside>
      </section>

      {#if result}
        <section class="poap-result-card">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p class="poap-kicker">Verified wallet</p>
              <h2>{truncateAddress(result.verified_address || verifiedAddress)}</h2>
            </div>
            <div class="poap-count-pill">
              <span>{result.attached_count || 0}</span>
              <span>Recovered</span>
            </div>
          </div>

          {#if result.attached_count > 0}
            <div class="poap-recovered-grid">
              {#each result.attached_poaps as claim (claim.id)}
                <button class="poap-recovered-item" type="button" onclick={() => push(`/community/poaps/${claim.drop.slug}`)}>
                  {#if claim.drop.artwork_url}
                    <img src={claim.drop.artwork_url} alt="" loading="lazy" />
                  {:else}
                    <span>{(claim.drop.title || 'POAP').slice(0, 2).toUpperCase()}</span>
                  {/if}
                  <strong>{claim.drop.title}</strong>
                </button>
              {/each}
            </div>
          {:else if result.skipped_existing_drop_count > 0}
            <div class="poap-empty-result">
              Matching POAPs were found for this wallet, but your portal account already has those drops.
            </div>
          {:else}
            <div class="poap-empty-result">
              No new unmatched POAPs were found for this wallet.
            </div>
          {/if}
        </section>
      {/if}
    {/if}
  </div>
</div>

<style>
  .poap-recovery-card,
  .poap-result-card {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(127, 82, 225, 0.16);
    border-radius: 16px;
    box-shadow: 0 16px 42px rgba(38, 48, 75, 0.08);
    padding: 22px;
  }

  .poap-card-heading {
    align-items: center;
    display: flex;
    gap: 12px;
  }

  .poap-icon {
    align-items: center;
    background: #f4ecfd;
    border: 1px solid #e7ddff;
    border-radius: 12px;
    color: #7f52e1;
    display: inline-flex;
    height: 42px;
    justify-content: center;
    width: 42px;
  }

  .poap-icon.discord {
    background: #eef0ff;
    border-color: #dfe3ff;
    color: #5865f2;
  }

  .poap-kicker {
    color: #7f52e1;
    font-size: 12px;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1;
    margin: 0 0 6px;
    text-transform: uppercase;
  }

  h2 {
    color: #101010;
    font-size: 20px;
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.15;
    margin: 0;
  }

  .poap-muted {
    color: #536079;
    font-size: 14px;
    line-height: 22px;
    margin: 8px 0 0;
  }

  .poap-verify-box {
    align-items: center;
    border-top: 1px solid #f0ecff;
    display: flex;
    gap: 16px;
    justify-content: space-between;
    margin-top: 18px;
    padding-top: 18px;
  }

  .poap-primary-action {
    background: #7f52e1;
    border: 0;
    border-radius: 10px;
    color: #fff;
    cursor: pointer;
    flex: 0 0 auto;
    font-size: 14px;
    font-weight: 700;
    height: 42px;
    padding: 0 16px;
    transition: background-color 150ms ease, opacity 150ms ease;
  }

  .poap-primary-action:hover:not(:disabled) {
    background: #6b43c7;
  }

  .poap-primary-action:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }

  .poap-count-pill {
    align-items: center;
    background: #f4ecfd;
    border: 1px solid #e5dcff;
    border-radius: 999px;
    color: #5d46bf;
    display: inline-flex;
    flex: 0 0 auto;
    font-size: 12px;
    font-weight: 800;
    gap: 8px;
    padding: 8px 12px;
    text-transform: uppercase;
  }

  .poap-count-pill span:first-child {
    color: #101010;
    font-size: 18px;
  }

  .poap-recovered-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    margin-top: 22px;
  }

  .poap-recovered-item {
    align-items: center;
    background: transparent;
    border: 0;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 0;
    padding: 0;
    text-align: center;
  }

  .poap-recovered-item img,
  .poap-recovered-item > span {
    align-items: center;
    background: #f4ecfd;
    border: 1px solid #e7ddff;
    border-radius: 999px;
    display: inline-flex;
    height: 104px;
    justify-content: center;
    object-fit: cover;
    width: 104px;
  }

  .poap-recovered-item strong {
    color: #151329;
    display: -webkit-box;
    font-size: 13px;
    font-weight: 650;
    line-height: 18px;
    max-width: 120px;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }

  .poap-empty-result {
    background: #fbfaff;
    border: 1px solid #f0ecff;
    border-radius: 12px;
    color: #6d7282;
    font-size: 14px;
    margin-top: 20px;
    padding: 22px;
    text-align: center;
  }

  @media (max-width: 720px) {
    .poap-verify-box {
      align-items: stretch;
      flex-direction: column;
    }

    .poap-primary-action {
      width: 100%;
    }
  }
</style>
