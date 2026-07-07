<script>
  import { onMount, onDestroy } from 'svelte';
  import { replace, querystring } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI, contributionsAPI } from '../lib/api.js';
  import Pagination from '../components/Pagination.svelte';
  import StewardSearchBar from '../components/StewardSearchBar.svelte';
  import { showSuccess, showError } from '../lib/toastStore';
  import { parseSearch } from '../lib/searchParser.js';
  import { xpSearchToParams } from '../lib/xpSearchToParams.js';
  import { stewardPermissions } from '../lib/stewardPermissions.js';

  let rows = $state([]);
  let contributionTypes = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = $state(10);
  let statusFilter = $state('pending');
  let searchQuery = $state('');
  let busyRows = $state(new Set());
  let permissionsMap = $state({});
  let requestId = 0;

  let canAccessDiscordXP = $derived(
    contributionTypes.some(type =>
      (permissionsMap[String(type.id)] || []).includes('accept')
    )
  );

  const FILTERS = [
    { value: 'pending', label: 'Needs XP' },
    { value: 'distributed', label: 'Distributed' },
    { value: 'all', label: 'All' }
  ];

  // Set once unmounted, so a load that finishes after the user leaves doesn't
  // sync the URL (which would navigate them back here).
  let destroyed = false;
  onDestroy(() => { destroyed = true; });

  onMount(async () => {
    if (!$authState.isAuthenticated) {
      replace('/');
      return;
    }

    const params = new URLSearchParams($querystring);
    if (params.has('status')) statusFilter = normalizeStatusFilter(params.get('status'));
    if (params.has('q')) searchQuery = params.get('q');

    await loadContributionTypes();
    await loadPermissions();
    if (!canAccessDiscordXP) {
      error = 'You do not have permission to manage Discord XP for community contributions';
      loading = false;
      return;
    }
    await loadXP();
  });

  async function loadContributionTypes() {
    try {
      const response = await contributionsAPI.getAllContributionTypes({ category: 'community' });
      contributionTypes = response.data || [];
    } catch (err) {
      contributionTypes = [];
    }
  }

  async function loadPermissions() {
    try {
      await stewardPermissions.load();
      stewardPermissions.subscribe(value => {
        permissionsMap = value || {};
      })();
    } catch (err) {
      permissionsMap = {};
    }
  }

  function updateURL() {
    const params = new URLSearchParams();
    if (statusFilter) params.set('status', statusFilter);
    if (searchQuery) params.set('q', searchQuery);
    const suffix = params.toString() ? `?${params.toString()}` : '';
    const target = `/stewards/discord-xp${suffix}`;
    // Reflect filters in the URL without navigating/re-rendering (see
    // StewardSubmissions for why router replace() is wrong here).
    if (window.location.pathname + window.location.search !== target) {
      window.history.replaceState({}, '', target);
    }
  }

  async function loadXP() {
    if (destroyed) return; // unmounted mid-load — don't fetch or touch the URL
    const id = ++requestId;
    loading = true;
    error = null;

    try {
      updateURL();
      const parsed = parseSearch(searchQuery);
      const params = xpSearchToParams(parsed, { contributionTypes });

      if (statusFilter && statusFilter !== 'all') {
        params.status = statusFilter;
      }

      params.page = currentPage;
      params.page_size = pageSize;

      const response = await stewardAPI.getDiscordXP(params);
      if (id !== requestId) return;

      rows = response.data.results || [];
      totalCount = response.data.count || 0;

      if (rows.length === 0 && currentPage > 1 && totalCount > 0) {
        currentPage -= 1;
        return loadXP();
      }
    } catch (err) {
      if (id !== requestId) return;
      if (err.response?.status === 404 && currentPage > 1) {
        currentPage -= 1;
        return loadXP();
      }
      error = err.response?.status === 403
        ? 'You do not have permission to access steward tools'
        : 'Failed to load Discord XP';
    } finally {
      if (id === requestId) {
        loading = false;
      }
    }
  }

  function handlePageChange(event) {
    currentPage = event.detail;
    loadXP();
  }

  function handlePageSizeChange(event) {
    pageSize = event.detail;
    currentPage = 1;
    loadXP();
  }

  function handleFilterChange(value) {
    statusFilter = value;
    currentPage = 1;
    loadXP();
  }

  function normalizeStatusFilter(value) {
    const normalized = String(value || '').replace('-', '_');
    return FILTERS.some(filter => filter.value === normalized) ? normalized : 'pending';
  }

  function handleSearchChange(query) {
    searchQuery = query;
    currentPage = 1;
    loadXP();
  }

  function displayName(row) {
    return row.contributor?.name || shorten(row.contributor?.address) || 'Unknown contributor';
  }

  function discordName(row) {
    if (!row.discord) return 'No Discord linked';
    return row.discord.guild_nick || row.discord.platform_username || 'Discord linked';
  }

  function contributionTitle(row) {
    return row.contribution_title || row.social_task?.name || row.contribution_type?.name || `Contribution #${row.contribution}`;
  }

  function entryTypeLabel(row) {
    if (row.source === 'social_task') return 'Social task';
    return row.contribution_type?.name || 'Community';
  }

  function statusLabel(status) {
    const labels = {
      pending: 'Pending',
      distributed: 'Distributed',
      needs_review: 'Points changed'
    };
    return labels[status] || status;
  }

  function statusClass(status) {
    const classes = {
      pending: 'bg-amber-50 text-amber-700 border-amber-200',
      distributed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      needs_review: 'bg-slate-100 text-slate-700 border-slate-300'
    };
    return classes[status] || 'bg-gray-50 text-gray-700 border-gray-200';
  }

  function copyLabel(row) {
    if (!row.discord) return 'No Discord linked';
    if (row.status === 'needs_review') return 'Points changed';
    if ((row.pending_amount || 0) <= 0) return 'Distributed';
    return 'Copy command';
  }

  function frozenPoints(row) {
    return row.frozen_global_points ?? row.community_points ?? 0;
  }

  function canCopy(row) {
    return Boolean(row.discord) &&
      row.status !== 'needs_review' &&
      (row.pending_amount || 0) > 0 &&
      !busyRows.has(row.id);
  }

  function canMarkDistributed(row) {
    return Boolean(row.discord) &&
      row.status !== 'needs_review' &&
      (row.pending_amount || 0) > 0 &&
      !busyRows.has(row.id);
  }

  function canUnset(row) {
    return (row.awarded_amount || 0) > 0 && !busyRows.has(row.id);
  }

  async function copyCommand(row) {
    if (!canCopy(row)) return;

    busyRows.add(row.id);
    busyRows = new Set(busyRows);

    try {
      await navigator.clipboard.writeText(row.command);
      const response = await stewardAPI.recordDiscordXPCopy(row.id);
      updateRow(response.data);
      showSuccess('XP command copied');
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to copy XP command');
    } finally {
      busyRows.delete(row.id);
      busyRows = new Set(busyRows);
    }
  }

  async function markDistributed(row) {
    if (!canMarkDistributed(row)) return;

    busyRows.add(row.id);
    busyRows = new Set(busyRows);

    try {
      const response = await stewardAPI.markDiscordXPDistributed(row.id);
      await applyServerRow(response.data);
      showSuccess('Marked as distributed');
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to mark distributed');
    } finally {
      busyRows.delete(row.id);
      busyRows = new Set(busyRows);
    }
  }

  async function unsetDistributed(row) {
    if (!canUnset(row)) return;

    busyRows.add(row.id);
    busyRows = new Set(busyRows);

    try {
      const response = await stewardAPI.unsetDiscordXPDistributed(row.id);
      await applyServerRow(response.data);
      showSuccess('Distribution flag unset');
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to unset distribution flag');
    } finally {
      busyRows.delete(row.id);
      busyRows = new Set(busyRows);
    }
  }

  function updateRow(nextRow) {
    rows = rows.map(row => row.id === nextRow.id ? nextRow : row);
  }

  function rowMatchesActiveStatus(row) {
    return statusFilter === 'all' || row.status === statusFilter;
  }

  async function applyServerRow(nextRow) {
    const existing = rows.find(row => row.id === nextRow.id);
    if (!existing) return;

    if (rowMatchesActiveStatus(nextRow)) {
      updateRow(nextRow);
      return;
    }

    rows = rows.filter(row => row.id !== nextRow.id);
    totalCount = Math.max(0, totalCount - 1);

    if (rows.length === 0 && totalCount > 0) {
      currentPage = Math.min(currentPage, Math.max(1, Math.ceil(totalCount / pageSize)));
      await loadXP();
    }
  }

  function formatDate(value) {
    if (!value) return 'No date';
    try {
      return new Date(value).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch (err) {
      return 'No date';
    }
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString();
  }

  function shorten(value) {
    if (!value) return '';
    return value.length > 14 ? `${value.slice(0, 6)}...${value.slice(-4)}` : value;
  }
</script>

<div class="min-h-screen bg-[#f7f8f7] px-4 py-6 sm:px-6 lg:px-8">
  <div class="mx-auto max-w-7xl space-y-5">
    <div class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-normal text-gray-950">Discord XP</h1>
        <div class="mt-1 text-sm text-gray-600">{formatNumber(totalCount)} community XP {totalCount === 1 ? 'entry' : 'entries'}</div>
      </div>
      <div class="flex flex-wrap gap-2">
        {#each FILTERS as filter}
          <button
            type="button"
            onclick={() => handleFilterChange(filter.value)}
            class="rounded-md border px-3 py-1.5 text-sm font-medium transition-colors {statusFilter === filter.value ? 'border-[#19A663] bg-[#e6f7ed] text-[#0f7d49]' : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'}"
          >
            {filter.label}
          </button>
        {/each}
      </div>
    </div>

    <div class="flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm md:flex-row md:items-center">
      <StewardSearchBar
        variant="xp"
        bind:value={searchQuery}
        {contributionTypes}
        placeholder="from:alice type:community-call sort:-points..."
        onSearch={handleSearchChange}
      />
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <div class="h-12 w-12 animate-spin rounded-full border-b-2 border-[#19A663]"></div>
      </div>
    {:else if error}
      <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    {:else if rows.length === 0}
      <div class="rounded-lg border border-gray-200 bg-white py-12 text-center text-sm text-gray-600 shadow-sm">
        No Discord XP rows found.
      </div>
    {:else}
      {#if totalCount > pageSize}
        <Pagination
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 25, 50]}
          showPageSize={true}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      {/if}

      <div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Contributor</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Contribution</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Community Points</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Status</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 bg-white">
              {#each rows as row (row.id)}
                <tr class="hover:bg-gray-50">
                  <td class="px-4 py-3 align-top">
                    <div class="font-medium text-gray-950">{displayName(row)}</div>
                    <div class="mt-0.5 text-sm {row.discord ? 'text-gray-600' : 'text-gray-400'}">{discordName(row)}</div>
                  </td>
                  <td class="max-w-md px-4 py-3 align-top">
                    <div class="line-clamp-2 font-medium text-gray-900">{contributionTitle(row)}</div>
                    <div class="mt-1 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                      <span>{entryTypeLabel(row)}</span>
                      <span class="text-gray-300">/</span>
                      <span>{formatDate(row.contribution_date)}</span>
                    </div>
                    {#if row.last_copied_at}
                      <div class="mt-1 text-xs text-gray-400">Copied {formatDate(row.last_copied_at)}</div>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-right align-top font-medium tabular-nums text-gray-900">{formatNumber(frozenPoints(row))}</td>
                  <td class="px-4 py-3 align-top">
                    <span class="inline-flex rounded-full border px-2.5 py-1 text-xs font-medium {statusClass(row.status)}">
                      {statusLabel(row.status)}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right align-top">
                    <div class="flex min-w-[260px] justify-end gap-2">
                      {#if row.status === 'distributed' || row.status === 'needs_review'}
                        <button
                          type="button"
                          onclick={() => unsetDistributed(row)}
                          disabled={!canUnset(row)}
                          class="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-700 transition-colors hover:border-gray-400 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
                        >
                          {busyRows.has(row.id) ? 'Updating...' : 'Unset flag'}
                        </button>
                      {:else}
                        <button
                          type="button"
                          onclick={() => copyCommand(row)}
                          disabled={!canCopy(row)}
                          class="rounded-md border px-3 py-1.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400 {canCopy(row) ? 'border-[#19A663] bg-white text-[#0f7d49] hover:bg-[#e6f7ed]' : ''}"
                        >
                          {busyRows.has(row.id) ? 'Working...' : copyLabel(row)}
                        </button>
                        <button
                          type="button"
                          onclick={() => markDistributed(row)}
                          disabled={!canMarkDistributed(row)}
                          class="rounded-md border px-3 py-1.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400 {canMarkDistributed(row) ? 'border-[#19A663] bg-[#19A663] text-white hover:bg-[#148c53]' : ''}"
                        >
                          Flag distributed
                        </button>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>

      {#if totalCount > pageSize}
        <Pagination
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 25, 50]}
          showPageSize={true}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      {/if}
    {/if}
  </div>
</div>
