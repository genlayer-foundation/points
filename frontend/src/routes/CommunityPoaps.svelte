<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { poapsAPI } from '../lib/api.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import PoapCollectionWall from '../components/poaps/PoapCollectionWall.svelte';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';

  let loading = $state(true);
  /** @type {any[]} */
  let poaps = $state([]);
  let count = $state(0);
  let search = $state('');
  let monthFilter = $state('');
  let permissions = $state({ can_manage_poaps: false });
  let showCreate = $state(false);
  let creating = $state(false);
  /** @type {any} */
  let createForm = $state({
    title: '',
    description: '',
    artwork_url: '',
    event_start_at: '',
    event_end_at: '',
    status: 'active',
    max_claims: '',
  });

  const PAGE_SIZE = 100;

  async function loadPoaps() {
    loading = true;
    try {
      /** @type {Record<string, any>} */
      const params = {
        page: 1,
        page_size: PAGE_SIZE,
        ordering: '-event_start_at',
      };
      if (search.trim()) params.search = search.trim();
      if (monthFilter) params.month = monthFilter;
      const response = await poapsAPI.list(params);
      const data = response.data || {};
      if (Array.isArray(data)) {
        poaps = data;
        count = data.length;
        return;
      }

      const results = [...(data.results || [])];
      const total = data.count ?? results.length;
      let nextPage = 2;
      let hasNext = Boolean(data.next);

      while (hasNext && results.length < total) {
        const nextResponse = await poapsAPI.list({ ...params, page: nextPage });
        const nextData = nextResponse.data || {};
        results.push(...(nextData.results || []));
        hasNext = Boolean(nextData.next);
        nextPage += 1;
      }

      poaps = results;
      count = total;
    } catch (err) {
      const error = /** @type {any} */ (err);
      showError(error.response?.data?.error || 'Unable to load POAPs');
      poaps = [];
      count = 0;
    } finally {
      loading = false;
    }
  }

  async function loadPermissions() {
    try {
      const response = await poapsAPI.permissions();
      permissions = response.data || { can_manage_poaps: false };
    } catch {
      permissions = { can_manage_poaps: false };
    }
  }

  function clearFilters() {
    search = '';
    monthFilter = '';
    loadPoaps();
  }

  async function createPoap() {
    if (!createForm.title || !createForm.event_start_at) {
      showError('Title and event start date are required.');
      return;
    }
    creating = true;
    try {
      const payload = {
        ...createForm,
        max_claims: createForm.max_claims ? Number(createForm.max_claims) : null,
        event_end_at: createForm.event_end_at || null,
      };
      const response = await poapsAPI.create(payload);
      showSuccess('POAP created.');
      showCreate = false;
      createForm = {
        title: '',
        description: '',
        artwork_url: '',
        event_start_at: '',
        event_end_at: '',
        status: 'active',
        max_claims: '',
      };
      push(`/community/poaps/${response.data.slug}`);
    } catch (err) {
      const data = /** @type {any} */ (err).response?.data;
      showError(typeof data === 'string' ? data : data?.detail || data?.error || 'Unable to create POAP.');
    } finally {
      creating = false;
    }
  }

  onMount(() => {
    loadPermissions();
    loadPoaps();
  });
</script>

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div class="absolute inset-x-0 top-0 h-[260px] pointer-events-none overflow-hidden" style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);">
    <img src="/assets/illustrations/welcome-gradient.png" alt="" class="absolute inset-0 h-full w-full object-cover opacity-60" />
    <div class="absolute inset-0 bg-white/35"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
      <div class="flex min-w-0 items-start gap-3">
        <div class="mt-1 shrink-0">
          <CategoryIcon category="community" mode="hexagon" size={44} />
        </div>
        <div class="min-w-0">
          <h1 class="font-display text-[34px] font-semibold leading-none text-black sm:text-[40px] md:text-[46px]" style="letter-spacing: -1px;">POAPs</h1>
          <p class="mt-2 text-[14px] text-[#3f4b5f] sm:text-[15px]">Browse GenLayer POAPs.</p>
        </div>
      </div>

      <div class="flex w-full flex-col gap-3 xl:w-auto xl:items-end">
        <div class="flex w-full flex-col gap-2 md:flex-row xl:justify-end">
          <label class="relative md:w-[300px]">
            <span class="sr-only">Search POAPs</span>
            <input
              bind:value={search}
              class="h-10 w-full rounded-[8px] border border-[#e6e6e6] bg-white px-4 pr-10 text-[14px] text-black outline-none transition-colors placeholder:text-[#999] focus:border-[#8d81e1]"
              placeholder="Search POAPs"
              onkeydown={(event) => event.key === 'Enter' && loadPoaps()}
            />
            <button
              class="absolute right-1.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-[6px] text-[#8d81e1] hover:bg-[#f4ecfd]"
              onclick={() => loadPoaps()}
              aria-label="Search POAPs"
            >
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
              </svg>
            </button>
          </label>

          <input
            bind:value={monthFilter}
            type="month"
            class="h-10 rounded-[8px] border border-[#e6e6e6] bg-white px-3 text-[14px] outline-none focus:border-[#8d81e1] md:w-[150px]"
            onchange={() => loadPoaps()}
          />

          {#if search || monthFilter}
            <button
              class="h-10 rounded-[8px] border border-[#e6e6e6] bg-white px-3 text-[13px] font-medium text-[#555] transition-colors hover:bg-[#f7f7f7]"
              onclick={clearFilters}
            >
              Reset
            </button>
          {/if}

          {#if permissions.can_manage_poaps}
            <button
              class="inline-flex h-10 items-center justify-center rounded-[24px] bg-[#101010] px-4 text-[14px] font-medium text-white transition-colors hover:bg-black"
              onclick={() => (showCreate = true)}
            >
              New POAP
            </button>
          {/if}
        </div>
      </div>
    </header>

    <section class="space-y-6">
      {#if loading}
        <div class="space-y-8 animate-pulse">
          <div class="h-8 w-56 rounded bg-[#eee8ff]"></div>
          <div class="grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-6">
            {#each Array(12) as _}
              <div class="flex flex-col items-center gap-3">
                <div class="h-28 w-28 rounded-full bg-white shadow-[0_14px_30px_rgba(38,48,75,0.08)] sm:h-36 sm:w-36"></div>
                <div class="h-3 w-24 rounded bg-[#eee]"></div>
              </div>
            {/each}
          </div>
        </div>
      {:else if poaps.length === 0}
        <div class="rounded-[8px] border border-[#f0f0f0] bg-white p-12 text-center">
          <p class="text-[15px] font-medium text-black">No POAPs found</p>
          <p class="mt-1 text-[14px] text-[#7a7a7a]">Try changing the filters or check back after the next community event.</p>
        </div>
      {:else}
        <PoapCollectionWall items={poaps} density="large" showCaptions={false} showOpenBadge={true} />
      {/if}
    </section>
  </div>
</div>

{#if showCreate}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" role="dialog" aria-modal="true">
    <div class="w-full max-w-2xl rounded-[10px] bg-white p-6 shadow-[0_24px_80px_rgba(0,0,0,0.24)]">
      <div class="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 class="text-[22px] font-semibold text-black">New POAP</h2>
          <p class="mt-1 text-[14px] text-[#777]">Create the badge first, then add distribution methods on the detail page.</p>
        </div>
        <button class="rounded-full p-2 hover:bg-[#f5f5f5]" onclick={() => (showCreate = false)} aria-label="Close">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="grid gap-4">
        <label class="grid gap-1 text-[13px] font-medium text-[#555]">Title
          <input bind:value={createForm.title} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" />
        </label>
        <label class="grid gap-1 text-[13px] font-medium text-[#555]">Artwork URL
          <input bind:value={createForm.artwork_url} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" placeholder="https://..." />
        </label>
        <label class="grid gap-1 text-[13px] font-medium text-[#555]">Description
          <textarea bind:value={createForm.description} class="min-h-[96px] rounded-[8px] border border-[#e6e6e6] p-3 text-[14px] text-black outline-none focus:border-[#8d81e1]"></textarea>
        </label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Event start
            <input bind:value={createForm.event_start_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" />
          </label>
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Event end
            <input bind:value={createForm.event_end_at} type="datetime-local" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" />
          </label>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Status
            <select bind:value={createForm.status} class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]">
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label class="grid gap-1 text-[13px] font-medium text-[#555]">Max claims
            <input bind:value={createForm.max_claims} type="number" min="1" class="h-10 rounded-[8px] border border-[#e6e6e6] px-3 text-[14px] text-black outline-none focus:border-[#8d81e1]" placeholder="Unlimited" />
          </label>
        </div>
      </div>
      <div class="mt-6 flex justify-end gap-2">
        <button class="h-10 rounded-[8px] border border-[#e6e6e6] px-4 text-[14px] font-medium text-[#555]" onclick={() => (showCreate = false)}>Cancel</button>
        <button class="h-10 rounded-[8px] bg-[#101010] px-4 text-[14px] font-medium text-white disabled:opacity-50" disabled={creating} onclick={createPoap}>
          {creating ? 'Creating...' : 'Create POAP'}
        </button>
      </div>
    </div>
  </div>
{/if}
