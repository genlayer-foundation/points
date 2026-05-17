<script>
  import { params, push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { API_BASE_URL } from '../lib/config.js';
  import { authState } from '../lib/auth.js';
  import { poapsAPI } from '../lib/api.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import PoapBadgeImage from '../components/poaps/PoapBadgeImage.svelte';

  /** @type {any} */
  let poap = $state(null);
  /** @type {any[]} */
  let claims = $state([]);
  let claimsCount = $state(0);
  let loading = $state(true);
  let claimsLoading = $state(false);
  let error = $state('');
  let claimPage = $state(1);
  let secret = $state('');
  let claiming = $state(false);
  let creatingSecret = $state(false);
  let generatingLinks = $state(false);
  /** @type {any[]} */
  let generatedLinks = $state([]);
  let showEdit = $state(false);
  let showManage = $state(false);
  let savingDrop = $state(false);
  /** @type {any} */
  let editForm = $state({
    title: '',
    description: '',
    artwork_url: '',
    event_start_at: '',
    event_end_at: '',
    status: 'active',
    max_claims: '',
  });
  let secretForm = $state({
    secret: '',
    starts_at: '',
    ends_at: '',
    max_claims: '',
    active: true,
  });
  let linkForm = $state({
    count: 1,
    max_uses: 1,
    expires_at: '',
    starts_at: '',
    ends_at: '',
  });

  const CLAIM_PAGE_SIZE = 10;

  let slug = $derived($params?.slug || '');
  let claimTotalPages = $derived(Math.max(1, Math.ceil(claimsCount / CLAIM_PAGE_SIZE)));
  let canClaim = $derived(Boolean(poap?.can_claim));
  let activeClaimDistributions = $derived((poap?.distributions || []).filter(distributionIsOpen));
  let hasSecretClaim = $derived(canClaim && activeClaimDistributions.some((distribution) => distribution.method === 'secret'));
  let hasMintLinkClaim = $derived(canClaim && activeClaimDistributions.some((distribution) => distribution.method === 'mint_link'));
  let collectorCount = $derived(poap?.claimed_count ?? claimsCount ?? 0);
  let statusLabel = $derived(poap?.status === 'active' ? 'Live' : poap?.status === 'draft' ? 'Draft' : 'Archived');
  let statusClass = $derived(
    poap?.status === 'active'
      ? 'border-[#d8f0df] bg-[#f2fbf5] text-[#167b48]'
      : poap?.status === 'draft'
        ? 'border-[#e6e6e6] bg-[#fafafa] text-[#6b6b6b]'
        : 'border-[#e7e0f8] bg-[#f4ecfd] text-[#7f52e1]'
  );
  let loadedSlug = $state('');

  /**
   * @param {string | Date | null | undefined} value
   * @param {string} [pattern]
   */
  function formatDate(value, pattern = 'MMM d, yyyy') {
    if (!value) return '';
    try {
      return format(new Date(value), pattern);
    } catch {
      return String(value);
    }
  }

  /** @param {number | null | undefined} value */
  function formatNumber(value) {
    return new Intl.NumberFormat('en-US').format(Number(value || 0));
  }

  /** @param {any} distribution */
  function distributionIsOpen(distribution) {
    if (!distribution?.active) return false;
    const now = Date.now();
    const startsAt = distribution.starts_at ? new Date(distribution.starts_at).getTime() : null;
    const endsAt = distribution.ends_at ? new Date(distribution.ends_at).getTime() : null;
    if (startsAt && startsAt > now) return false;
    if (endsAt && endsAt < now) return false;
    if (distribution.max_claims !== null && distribution.max_claims !== undefined && distribution.claimed_count >= distribution.max_claims) return false;
    return true;
  }

  /** @param {any} err */
  function isAuthError(err) {
    const statusCode = err?.response?.status;
    return statusCode === 401 || statusCode === 403;
  }

  /** @param {string | Date | null | undefined} value */
  function toDateTimeLocal(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return offsetDate.toISOString().slice(0, 16);
  }

  function openEdit() {
    if (!poap) return;
    editForm = {
      title: poap.title || '',
      description: poap.description || '',
      artwork_url: poap.artwork_url || '',
      event_start_at: toDateTimeLocal(poap.event_start_at),
      event_end_at: toDateTimeLocal(poap.event_end_at),
      status: poap.status || 'active',
      max_claims: poap.max_claims || '',
    };
    showEdit = true;
  }

  function signInForClaim() {
    sessionStorage.setItem('redirectAfterLogin', `/community/poaps/${slug}`);
    window.setTimeout(() => {
      const authButton = document.querySelector('[data-auth-button]');
      if (authButton instanceof HTMLElement) authButton.click();
    }, 0);
  }

  async function loadPoap() {
    if (!slug) return;
    loading = true;
    error = '';
    try {
      const response = await poapsAPI.get(slug);
      poap = response.data;
      showManage = false;
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      error = requestError.response?.data?.detail || 'Unable to load this POAP.';
    } finally {
      loading = false;
    }
  }

  /** @param {number} [page] */
  async function loadClaims(page = claimPage) {
    if (!slug) return;
    claimsLoading = true;
    claimPage = page;
    try {
      const response = await poapsAPI.getClaims(slug, {
        page,
        page_size: CLAIM_PAGE_SIZE,
      });
      claims = response.data?.results || response.data || [];
      claimsCount = response.data?.count ?? claims.length;
    } catch {
      claims = [];
      claimsCount = 0;
    } finally {
      claimsLoading = false;
    }
  }

  async function saveDrop() {
    if (!editForm.title || !editForm.event_start_at) {
      showError('Title and event start date are required.');
      return;
    }
    savingDrop = true;
    try {
      await poapsAPI.update(slug, {
        ...editForm,
        event_end_at: editForm.event_end_at || null,
        max_claims: editForm.max_claims ? Number(editForm.max_claims) : null,
      });
      showSuccess('POAP updated.');
      showEdit = false;
      await loadPoap();
    } catch (err) {
      const data = /** @type {any} */ (err).response?.data;
      showError(typeof data === 'string' ? data : data?.detail || data?.error || 'Unable to update POAP.');
    } finally {
      savingDrop = false;
    }
  }

  async function claimSecret() {
    if (!$authState.isAuthenticated) {
      signInForClaim();
      return;
    }
    if (!secret.trim()) {
      showError('Enter the secret phrase.');
      return;
    }
    claiming = true;
    try {
      await poapsAPI.claimSecret(slug, secret);
      showSuccess('POAP claimed.');
      secret = '';
      await Promise.all([loadPoap(), loadClaims(1)]);
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      if (isAuthError(requestError)) {
        authState.setAuthenticated(false, null);
        authState.resetVerification();
        signInForClaim();
        return;
      }
      showError(requestError.response?.data?.error || 'Unable to claim this POAP.');
      await Promise.all([loadPoap(), loadClaims(1)]);
    } finally {
      claiming = false;
    }
  }

  async function createSecretDistribution() {
    if (!secretForm.secret.trim()) {
      showError('Secret phrase is required.');
      return;
    }
    creatingSecret = true;
    try {
      await poapsAPI.createSecretDistribution(slug, {
        secret: secretForm.secret,
        starts_at: secretForm.starts_at || null,
        ends_at: secretForm.ends_at || null,
        max_claims: secretForm.max_claims ? Number(secretForm.max_claims) : null,
        active: secretForm.active,
      });
      showSuccess('Secret distribution created.');
      secretForm = { secret: '', starts_at: '', ends_at: '', max_claims: '', active: true };
      await loadPoap();
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      showError(requestError.response?.data?.detail || requestError.response?.data?.error || 'Unable to create distribution.');
    } finally {
      creatingSecret = false;
    }
  }

  async function generateLinks() {
    generatingLinks = true;
    generatedLinks = [];
    try {
      const response = await poapsAPI.generateMintLinks(slug, {
        count: Number(linkForm.count) || 1,
        max_uses: Number(linkForm.max_uses) || 1,
        expires_at: linkForm.expires_at || null,
        starts_at: linkForm.starts_at || null,
        ends_at: linkForm.ends_at || null,
      });
      generatedLinks = response.data?.links || [];
      showSuccess(`${response.data?.created || generatedLinks.length} mint link${generatedLinks.length === 1 ? '' : 's'} generated.`);
      await loadPoap();
    } catch (err) {
      const requestError = /** @type {any} */ (err);
      showError(requestError.response?.data?.detail || requestError.response?.data?.error || 'Unable to generate mint links.');
    } finally {
      generatingLinks = false;
    }
  }

  /** @param {any} link */
  function mintLinkUrl(link) {
    const path = typeof link === 'string' ? link : link?.hash_path || link?.path || '';
    if (!path) return window.location.origin;
    if (/^https?:\/\//.test(path)) return path;
    if (path.startsWith('/#/')) return `${window.location.origin}${path}`;
    if (path.startsWith('#/')) return `${window.location.origin}/${path}`;
    return `${window.location.origin}#${path.startsWith('/') ? path : `/${path}`}`;
  }

  /** @param {any} link */
  async function copyLink(link) {
    const absolute = mintLinkUrl(link);
    try {
      await navigator.clipboard.writeText(absolute);
      showSuccess('Link copied.');
    } catch {
      showError('Unable to copy link.');
    }
  }

  function downloadMintLinks() {
    window.open(`${API_BASE_URL}/api/v1/poaps/${slug}/mint-links/download/`, '_blank', 'noopener,noreferrer');
  }

  $effect(() => {
    if (slug && slug !== loadedSlug) {
      loadedSlug = slug;
      loadPoap();
      loadClaims(1);
    }
  });
</script>

<div class="-mx-3 -my-3 px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div class="space-y-6">
    <button class="inline-flex items-center gap-2 text-[14px] font-medium text-[#6b5bd6] hover:text-[#4c3dbd]" onclick={() => push('/community/poaps')}>
      <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6" /></svg>
      Back to POAPs
    </button>

    {#if loading}
      <div class="rounded-[10px] border border-white/70 bg-white/82 p-8 shadow-[0_18px_55px_rgba(38,48,75,0.13)] animate-pulse">
        <div class="h-[260px] rounded-[8px] bg-[#f2f2f2]"></div>
      </div>
    {:else if error}
      <div class="rounded-[8px] border border-[#f0d2d2] bg-[#fff7f7] p-5 text-[14px] text-[#9f2f2f]">{error}</div>
    {:else if poap}
      <section class="poap-detail-card">
        <div class="poap-detail-shell">
          <div class="poap-art-panel">
            <PoapBadgeImage src={poap.artwork_url} title={poap.title} size="lg" />
          </div>

          <div class="poap-copy">
            <h1>{poap.title}</h1>
            <div class="poap-date-line">
              <svg class="h-5 w-5 text-[#7f52e1]" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M7 2v2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2V2h-2v2H9V2H7Zm12 8v10H5V10h14Z" /></svg>
              <span>{formatDate(poap.event_start_at)}</span>
              {#if poap.event_end_at}<span>- {formatDate(poap.event_end_at)}</span>{/if}
            </div>
            {#if poap.description}
              <p>{poap.description}</p>
            {/if}
          </div>

          <aside class="poap-claim-rail">
            <div class="poap-status-row">
              <span class="rounded-full border px-3 py-1 text-[12px] font-semibold uppercase {statusClass}">{statusLabel}</span>
              {#if poap.has_claimed}
                <span class="rounded-full border border-[#d8f0df] bg-[#f2fbf5] px-3 py-1 text-[12px] font-semibold uppercase text-[#167b48]">Claimed</span>
              {/if}
              {#if poap.can_manage}
                <button class="rounded-full border border-[#d9d2ff] bg-white px-3 py-1 text-[12px] font-semibold text-[#6b5bd6] hover:bg-[#f7f4ff]" onclick={openEdit}>Edit</button>
                <button
                  class="rounded-full border border-[#d9d2ff] bg-white px-3 py-1 text-[12px] font-semibold text-[#6b5bd6] hover:bg-[#f7f4ff]"
                  onclick={() => (showManage = !showManage)}
                >
                  Distribution
                </button>
              {/if}
            </div>

            {#if poap.max_claims}
              <div class="poap-dropped-stat">
                <span class="text-[12px] font-bold uppercase text-[#5f5785]">Dropped</span>
                <span class="poap-stat-number">{formatNumber(poap.max_claims)}</span>
                <span class="text-[12px] font-bold uppercase text-[#5f5785]">POAP{poap.max_claims === 1 ? '' : 's'}</span>
              </div>
            {/if}

            {#if hasSecretClaim}
              <div class="poap-claim-tool poap-secret-tool">
                <div class="poap-secret-fields">
                  <input
                    bind:value={secret}
                    class="poap-secret-input"
                    placeholder="Enter secret phrase"
                    onkeydown={(event) => event.key === 'Enter' && claimSecret()}
                  />
                  <button class="poap-primary-button" disabled={claiming} onclick={claimSecret}>
                    {claiming ? 'Claiming...' : 'Claim'}
                  </button>
                </div>
              </div>
            {:else if hasMintLinkClaim}
              <div class="poap-claim-tool poap-link-tool">
                <span class="poap-link-icon">
                  <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.07 0l2.12-2.12a5 5 0 0 0-7.07-7.07L10.9 5.03" /><path d="M14 11a5 5 0 0 0-7.07 0L4.81 13.1a5 5 0 0 0 7.07 7.07l1.22-1.22" /></svg>
                </span>
                <span class="poap-link-title">Mint link required</span>
              </div>
            {/if}
          </aside>
        </div>
      </section>

      {#if poap.can_manage && showManage}
        <section class="rounded-[10px] border border-[#e8e3ff] bg-white p-5 shadow-[0_12px_34px_rgba(80,64,150,0.08)] sm:p-6">
          <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 class="text-[20px] font-semibold text-black">Distribution</h2>
              <p class="mt-1 text-[14px] text-[#777]">Create secret phrases or individual mint links for this POAP.</p>
            </div>
            <button class="rounded-[8px] border border-[#d9d2ff] px-3 py-2 text-[13px] font-medium text-[#6b5bd6] hover:bg-[#f7f4ff]" onclick={downloadMintLinks}>Download mint links</button>
          </div>

          <div class="grid gap-5 lg:grid-cols-2">
            <div class="rounded-[8px] border border-[#f0f0f0] p-4">
              <h3 class="text-[15px] font-semibold text-black">Secret phrase</h3>
              <div class="mt-4 grid gap-3">
                <input bind:value={secretForm.secret} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" placeholder="friend-scientist-natural" />
                <div class="grid gap-3 sm:grid-cols-2">
                  <input bind:value={secretForm.starts_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" />
                  <input bind:value={secretForm.ends_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" />
                </div>
                <input bind:value={secretForm.max_claims} type="number" min="1" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" placeholder="Max claims, optional" />
                <label class="flex items-center gap-2 text-[13px] text-[#555]"><input bind:checked={secretForm.active} type="checkbox" /> Active</label>
                <button class="h-10 rounded-[8px] bg-[#101010] px-4 text-[14px] font-medium text-white disabled:opacity-50" disabled={creatingSecret} onclick={createSecretDistribution}>
                  {creatingSecret ? 'Creating...' : 'Create secret'}
                </button>
              </div>
            </div>

            <div class="rounded-[8px] border border-[#f0f0f0] p-4">
              <h3 class="text-[15px] font-semibold text-black">Individual mint links</h3>
              <div class="mt-4 grid gap-3">
                <div class="grid gap-3 sm:grid-cols-2">
                  <label class="grid gap-1 text-[13px] text-[#555]">Links
                    <input bind:value={linkForm.count} type="number" min="1" max="500" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" />
                  </label>
                  <label class="grid gap-1 text-[13px] text-[#555]">Uses per link
                    <input bind:value={linkForm.max_uses} type="number" min="1" max="100" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" />
                  </label>
                </div>
                <input bind:value={linkForm.expires_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] outline-none focus:border-[#8d81e1]" />
                <button class="h-10 rounded-[8px] bg-[#101010] px-4 text-[14px] font-medium text-white disabled:opacity-50" disabled={generatingLinks} onclick={generateLinks}>
                  {generatingLinks ? 'Generating...' : 'Generate links'}
                </button>
              </div>
              {#if generatedLinks.length > 0}
                <div class="mt-4 max-h-44 overflow-auto rounded-[8px] bg-[#fafafa] p-3">
                  {#each generatedLinks as link}
                    <button class="mb-2 block w-full truncate rounded-[6px] border border-[#e6e6e6] bg-white px-3 py-2 text-left text-[12px] text-[#555] hover:border-[#d9d2ff]" onclick={() => copyLink(link)}>
                      {mintLinkUrl(link)}
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          </div>

          {#if poap.distributions?.length}
            <div class="mt-5 overflow-x-auto">
              <table class="min-w-full text-left text-[13px]">
                <thead class="text-[#777]">
                  <tr class="border-b border-[#ededed]">
                    <th class="py-2 pr-4 font-medium">Method</th>
                    <th class="py-2 pr-4 font-medium">Active</th>
                    <th class="py-2 pr-4 font-medium">Claims</th>
                    <th class="py-2 pr-4 font-medium">Window</th>
                    <th class="py-2 pr-4 font-medium">Links</th>
                  </tr>
                </thead>
                <tbody>
                  {#each poap.distributions as distribution}
                    <tr class="border-b border-[#f5f5f5]">
                      <td class="py-2 pr-4 text-black">{distribution.method}</td>
                      <td class="py-2 pr-4">{distribution.active ? 'Yes' : 'No'}</td>
                      <td class="py-2 pr-4">{distribution.claimed_count}{distribution.max_claims ? ` / ${distribution.max_claims}` : ''}</td>
                      <td class="py-2 pr-4">{distribution.starts_at ? formatDate(distribution.starts_at, 'MMM d, h:mm a') : 'Live'} - {distribution.ends_at ? formatDate(distribution.ends_at, 'MMM d, h:mm a') : 'No end'}</td>
                      <td class="py-2 pr-4">{distribution.mint_link_count || 0}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>
      {/if}

      <section class="poap-collectors-card">
        <div class="poap-collectors-header">
          <h2>
            <span class="poap-collectors-number">{formatNumber(collectorCount)}</span>
            <span>Collector{collectorCount === 1 ? '' : 's'}</span>
          </h2>
        </div>

        {#if claimsLoading}
          <div class="space-y-2">
            {#each Array(5) as _}
              <div class="h-14 rounded-[8px] bg-[#f5f5f5] animate-pulse"></div>
            {/each}
          </div>
        {:else if claims.length === 0}
          <div class="poap-empty-collectors">No claims yet.</div>
        {:else}
          <div class="poap-collector-table">
            <div class="poap-collector-row poap-collector-row-head">
              <span>Collector</span>
              <span>Wallet</span>
              <span>Claimed</span>
            </div>
            {#each claims as claim (claim.id)}
              <div class="poap-collector-row">
                <div class="poap-collector-user">
                  {#if claim.user_details?.profile_image_url}
                    <img src={claim.user_details.profile_image_url} alt="" class="h-10 w-10 rounded-full object-cover" />
                  {:else}
                    <div class="flex h-10 w-10 items-center justify-center rounded-full bg-[#f4ecfd] text-[13px] font-semibold text-[#7f52e1]">
                      {(claim.user_details?.name || 'U').slice(0, 1).toUpperCase()}
                    </div>
                  {/if}
                  <div class="min-w-0">
                    <button class="truncate text-[14px] font-medium text-black hover:underline" onclick={() => push(`/participant/${claim.user_details.address}`)}>
                      {claim.user_details.name || `${claim.user_details.address.slice(0, 6)}...${claim.user_details.address.slice(-4)}`}
                    </button>
                  </div>
                </div>
                <span class="poap-wallet-cell">
                  {#if claim.user_details?.address}
                    {claim.user_details.address.slice(0, 6)}...{claim.user_details.address.slice(-4)}
                  {:else}
                    -
                  {/if}
                </span>
                <span class="poap-date-cell">{formatDate(claim.claimed_at, 'MMM d, yyyy')}</span>
              </div>
            {/each}
          </div>

          {#if claimsCount > CLAIM_PAGE_SIZE}
            <div class="mt-5 flex items-center justify-end gap-2">
              <button class="h-9 rounded-[8px] border border-[#e6e6e6] px-3 text-[13px] disabled:opacity-40" disabled={claimPage <= 1} onclick={() => loadClaims(claimPage - 1)}>Previous</button>
              <span class="text-[13px] text-[#777]">Page {claimPage} of {claimTotalPages}</span>
              <button class="h-9 rounded-[8px] border border-[#e6e6e6] px-3 text-[13px] disabled:opacity-40" disabled={claimPage >= claimTotalPages} onclick={() => loadClaims(claimPage + 1)}>Next</button>
            </div>
          {/if}
        {/if}
      </section>
    {/if}
  </div>
</div>

{#if showEdit}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" role="dialog" aria-modal="true">
    <div class="w-full max-w-2xl rounded-[10px] bg-white p-6 shadow-[0_24px_80px_rgba(0,0,0,0.24)]">
      <div class="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 class="text-[22px] font-semibold text-black">Edit POAP</h2>
          <p class="mt-1 text-[14px] text-[#777]">Update badge metadata and availability.</p>
        </div>
        <button class="rounded-full p-2 hover:bg-[#f5f5f5]" onclick={() => (showEdit = false)} aria-label="Close">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="grid gap-4">
        <label class="grid gap-1 text-[13px] font-medium text-[#555]">Title
          <input bind:value={editForm.title} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" />
        </label>
        <label class="grid gap-1 text-[13px] font-medium text-[#555]">Artwork URL
          <input bind:value={editForm.artwork_url} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" placeholder="https://..." />
        </label>
        <label class="grid gap-1 text-[13px] font-medium text-[#555]">Description
          <textarea bind:value={editForm.description} class="min-h-[96px] rounded-[8px] border border-[#e6e6e6] p-3 text-[14px] text-black outline-none focus:border-[#8d81e1]"></textarea>
        </label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Event start
            <input bind:value={editForm.event_start_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" />
          </label>
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Event end
            <input bind:value={editForm.event_end_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" />
          </label>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Status
            <select bind:value={editForm.status} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]">
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Max claims
            <input bind:value={editForm.max_claims} type="number" min="1" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" placeholder="Unlimited" />
          </label>
        </div>
      </div>
      <div class="mt-6 flex justify-end gap-2">
        <button class="h-10 rounded-[8px] border border-[#e6e6e6] px-4 text-[14px] font-medium text-[#555]" onclick={() => (showEdit = false)}>Cancel</button>
        <button class="h-10 rounded-[8px] bg-[#101010] px-4 text-[14px] font-medium text-white disabled:opacity-50" disabled={savingDrop} onclick={saveDrop}>
          {savingDrop ? 'Saving...' : 'Save POAP'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .poap-detail-card {
    background: rgba(255, 255, 255, 0.94);
    border: 1.5px solid rgba(127, 82, 225, 0.34);
    border-radius: 20px;
    box-shadow: 0 18px 48px rgba(80, 64, 150, 0.1);
    margin-left: auto;
    margin-right: auto;
    max-width: 900px;
    padding: 12px;
  }

  .poap-detail-shell {
    align-items: stretch;
    display: grid;
    gap: 18px;
    grid-template-columns: 190px minmax(0, 1fr) 210px;
  }

  .poap-art-panel {
    align-items: center;
    background: #f6f2ff;
    border-radius: 16px;
    display: flex;
    justify-content: center;
    min-height: 168px;
    padding: 14px;
  }

  .poap-copy {
    min-width: 0;
    padding: 10px 0;
  }

  .poap-copy h1 {
    color: #151329;
    font-family: var(--font-display, inherit);
    font-size: clamp(24px, 2.6vw, 34px);
    font-weight: 750;
    letter-spacing: 0;
    line-height: 1.12;
    margin: 4px 0 0;
  }

  .poap-date-line {
    align-items: center;
    color: #4f5572;
    display: flex;
    flex-wrap: wrap;
    font-size: 13px;
    font-weight: 650;
    gap: 8px;
    margin-top: 12px;
  }

  .poap-date-line svg {
    background: #f2edff;
    border-radius: 7px;
    padding: 3px;
  }

  .poap-copy p {
    color: #3f4b5f;
    font-size: 14px;
    line-height: 22px;
    margin: 16px 0 0;
    max-width: 720px;
    white-space: pre-wrap;
  }

  .poap-claim-rail {
    align-items: flex-end;
    border-left: 1px solid rgba(127, 82, 225, 0.14);
    display: flex;
    flex-direction: column;
    gap: 10px;
    justify-content: flex-start;
    padding: 10px 0 10px 18px;
  }

  .poap-status-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
  }

  .poap-dropped-stat,
  .poap-claim-tool {
    align-items: center;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 243, 255, 0.88));
    border: 1px solid rgba(127, 82, 225, 0.18);
    border-radius: 14px;
    box-shadow: 0 10px 22px rgba(80, 64, 150, 0.08);
    gap: 10px;
    padding: 10px 14px;
  }

  .poap-dropped-stat,
  .poap-link-tool {
    display: inline-flex;
    justify-content: flex-end;
  }

  .poap-claim-tool {
    width: 100%;
  }

  .poap-link-tool {
    color: #101010;
    font-size: 14px;
    font-weight: 750;
    line-height: 18px;
    text-align: left;
  }

  .poap-link-icon {
    align-items: center;
    background: #fff;
    border-radius: 999px;
    color: #7f52e1;
    display: inline-flex;
    flex: 0 0 auto;
    height: 30px;
    justify-content: center;
    width: 30px;
  }

  .poap-link-title {
    min-width: 0;
  }

  .poap-secret-fields {
    display: grid;
    gap: 10px;
  }

  .poap-secret-input {
    background: #fff;
    border: 1px solid #d9d2ff;
    border-radius: 10px;
    font-size: 14px;
    height: 44px;
    min-width: 0;
    outline: none;
    padding: 0 12px;
  }

  .poap-secret-input:focus {
    border-color: #8d81e1;
    box-shadow: 0 0 0 3px rgba(127, 82, 225, 0.1);
  }

  .poap-primary-button {
    background: #7f52e1;
    border: 0;
    border-radius: 10px;
    color: #fff;
    font-size: 14px;
    font-weight: 650;
    height: 44px;
    padding: 0 16px;
  }

  .poap-primary-button:disabled {
    opacity: 0.5;
  }

  .poap-collectors-card {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(127, 82, 225, 0.14);
    border-radius: 18px;
    box-shadow: 0 14px 38px rgba(38, 48, 75, 0.06);
    margin-left: auto;
    margin-right: auto;
    max-width: 900px;
    padding: 24px;
  }

  .poap-collectors-header {
    border-bottom: 1px solid #f0ecff;
    margin-bottom: 18px;
    padding-bottom: 16px;
  }

  .poap-collectors-header h2 {
    align-items: center;
    color: #51658d;
    display: flex;
    gap: 12px;
    font-size: 18px;
    font-weight: 850;
    letter-spacing: 0;
    margin: 0;
    text-transform: uppercase;
  }

  .poap-empty-collectors {
    background: #fbfaff;
    border: 1px solid #f0ecff;
    border-radius: 12px;
    color: #777;
    font-size: 14px;
    padding: 32px;
    text-align: center;
  }

  .poap-collector-table {
    display: grid;
    gap: 4px;
  }

  .poap-collector-row {
    align-items: center;
    border-radius: 8px;
    color: #303852;
    display: grid;
    gap: 14px;
    grid-template-columns: minmax(0, 1.35fr) minmax(120px, 0.8fr) 140px;
    min-height: 48px;
    padding: 8px 12px;
  }

  .poap-collector-row:not(.poap-collector-row-head):nth-child(odd) {
    background: #f5f1ff;
  }

  .poap-collector-row-head {
    color: #6f7894;
    font-size: 12px;
    font-weight: 800;
    min-height: 32px;
    text-transform: uppercase;
  }

  .poap-collector-user {
    align-items: center;
    display: flex;
    gap: 12px;
    min-width: 0;
  }

  .poap-wallet-cell,
  .poap-date-cell {
    color: #6b7285;
    font-size: 12px;
    min-width: 0;
  }

  .poap-date-cell {
    justify-self: end;
  }

  .poap-stat-number,
  .poap-collectors-number {
    color: #d9c9ff;
    font-family: var(--font-display, inherit);
    font-weight: 850;
    letter-spacing: 0;
    line-height: 1;
    text-shadow:
      1px 1px 0 #2f426a,
      2px 2px 0 rgba(127, 82, 225, 0.35),
      0 10px 22px rgba(127, 82, 225, 0.16);
    -webkit-text-stroke: 0.8px #51658d;
  }

  .poap-stat-number {
    font-size: clamp(28px, 2.6vw, 38px);
  }

  .poap-collectors-number {
    font-size: clamp(28px, 3vw, 38px);
  }

  @media (max-width: 1279px) {
    .poap-detail-shell {
      grid-template-columns: 190px minmax(0, 1fr);
    }

    .poap-claim-rail {
      align-items: stretch;
      border-left: 0;
      border-top: 1px solid rgba(127, 82, 225, 0.14);
      grid-column: 1 / -1;
      padding: 18px 0 0;
    }

    .poap-status-row {
      justify-content: flex-start;
    }

    .poap-dropped-stat {
      justify-content: center;
    }
  }

  @media (max-width: 760px) {
    .poap-detail-card,
    .poap-collectors-card {
      border-radius: 14px;
      padding: 14px;
    }

    .poap-detail-shell,
    .poap-collector-row {
      grid-template-columns: 1fr;
    }

    .poap-art-panel {
      min-height: 156px;
    }

    .poap-copy {
      padding: 0;
    }

    .poap-copy h1 {
      font-size: 30px;
    }

    .poap-date-cell {
      justify-self: start;
    }

    .poap-collector-row-head {
      display: none;
    }
  }
</style>
