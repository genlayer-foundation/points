<script>
  import { push } from 'svelte-spa-router';
  import { validatorsAPI } from '../lib/api';
  import Avatar from '../components/Avatar.svelte';
  import { showSuccess } from '../lib/toastStore';

  /**
   * @typedef {Object} ShameReason
   * @property {string} network
   * @property {string} type
   * @property {string} label
   * @property {string} status
   * @property {number | null | undefined} days_in_shame
   * @property {string | null | undefined} node_version
   * @property {string | null | undefined} target_version
   */
  /**
   * @typedef {Object} ValidatorNetwork
   * @property {string} network
   * @property {string | null | undefined} moniker
   */
  /**
   * @typedef {Object} ValidatorRow
   * @property {string} status
   * @property {string | null | undefined} name
   * @property {string | null | undefined} logo_uri
   * @property {string | null | undefined} operator_address
   * @property {any} operator_user
   * @property {ValidatorNetwork[]} networks
   * @property {ShameReason[]} shame_reasons
   */
  /**
   * @typedef {Object} ShameEntry
   * @property {string} network
   * @property {string} text
   * @property {string} status
   * @property {number | null | undefined} days_in_shame
   * @property {string[]} details
   */

  /** @type {ValidatorRow[]} */
  let validators = $state([]);
  let stats = $state({ total: 0, on: 0, shame: 0, warning: 0 });
  /** @type {string | null} */
  let lastCheckAt = $state(null);
  let loading = $state(true);
  /** @type {string | null} */
  let error = $state(null);

  $effect(() => {
    fetchWallOfShame();
  });

  async function fetchWallOfShame() {
    try {
      loading = true;
      error = null;
      const response = await validatorsAPI.getWallOfShame();
      /** @type {ValidatorRow[]} */
      const rows = response.data?.validators || [];
      validators = rows.filter((validator) => validator.status !== 'unknown');
      const responseStats = response.data?.stats || {};
      stats = {
        total: validators.length,
        on: responseStats.on || 0,
        shame: responseStats.shame || 0,
        warning: responseStats.warning || 0,
      };
      lastCheckAt = response.data?.last_grafana_check_at || null;
      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load Wall of Shame';
      loading = false;
    }
  }

  /** @param {string | null | undefined} address */
  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }

  /** @param {string} value */
  function rowStatusClass(value) {
    if (value === 'on') return 'bg-green-100 text-green-800';
    if (value === 'shame') return 'bg-red-100 text-red-800';
    if (value === 'warning') return 'bg-amber-100 text-amber-800';
    return 'bg-gray-100 text-gray-600';
  }

  /** @param {string} value */
  function statusText(value) {
    if (value === 'on') return 'ON';
    if (value === 'shame') return 'SHAME';
    if (value === 'warning') return 'WARNING';
    return '';
  }

  /** @param {ShameEntry} entry */
  function entryClass(entry) {
    if (entry.status === 'shame') return 'bg-red-50 text-red-800 ring-red-200';
    if (entry.status === 'warning') return 'bg-amber-50 text-amber-800 ring-amber-200';
    return 'bg-gray-50 text-gray-700 ring-gray-200';
  }

  /** @param {number} days */
  function daysClass(days) {
    if (days >= 7) return 'bg-red-200 text-red-950';
    if (days >= 3) return 'bg-orange-200 text-orange-950';
    return 'bg-amber-200 text-amber-950';
  }

  /** @param {number | null | undefined} days */
  function formatDays(days) {
    if (days === null || days === undefined) return '';
    if (days === 0) return 'today';
    if (days === 1) return '1d';
    return `${days}d`;
  }

  /** @param {ShameReason} reason */
  function reasonDetail(reason) {
    if (reason.type !== 'version') return '';
    const current = reason.node_version || 'missing';
    const target = reason.target_version || 'target unknown';
    return `${current} -> ${target}`;
  }

  /** @param {string} network */
  function networkText(network) {
    if (network === 'asimov') return 'asimov';
    if (network === 'bradbury') return 'bradbury';
    return network || 'unknown';
  }

  /** @param {ValidatorRow} validator */
  function shameEntries(validator) {
    /** @type {Array<{ network: string, reasons: ShameReason[] }>} */
    const grouped = [];
    for (const reason of validator.shame_reasons || []) {
      let group = grouped.find((item) => item.network === reason.network);
      if (!group) {
        group = { network: reason.network, reasons: [] };
        grouped.push(group);
      }
      group.reasons.push(reason);
    }

    /** @type {ShameEntry[]} */
    const entries = [];
    for (const group of grouped) {
      const labels = group.reasons.map((reason) => reason.label);
      const details = group.reasons
        .map((reason) => reasonDetail(reason))
        .filter(Boolean);
      const shameReasons = group.reasons.filter((reason) => reason.status === 'shame');
      const days = shameReasons
        .map((reason) => reason.days_in_shame)
        .filter((days) => days !== null && days !== undefined);
      entries.push({
        network: group.network,
        text: `${networkText(group.network)}: ${labels.join(' + ')}`,
        status: shameReasons.length ? 'shame' : group.reasons[0]?.status || 'unknown',
        days_in_shame: days.length ? Math.max(...days) : null,
        details,
      });
    }
    return entries;
  }

  /** @param {ValidatorRow} validator */
  function validatorMonikers(validator) {
    const monikers = (validator.networks || [])
      /** @param {ValidatorNetwork} network */
      .map((network) => network.moniker)
      .filter(Boolean);
    return [...new Set(monikers)].join(' / ');
  }

  /** @param {string | null | undefined} iso */
  function formatRelative(iso) {
    if (!iso) return 'never';
    const ts = new Date(iso).getTime();
    if (Number.isNaN(ts)) return 'never';
    const diffSec = Math.round((Date.now() - ts) / 1000);
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.round(diffSec / 60);
    if (diffMin < 60) return `${diffMin} min ago`;
    const diffHr = Math.round(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.round(diffHr / 24);
    return `${diffDay}d ago`;
  }
</script>

<div>
  <h1 class="text-2xl font-bold text-gray-900 mb-6">Wall of Shame</h1>

  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
      {error}
    </div>
  {:else}
    <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-8">
      <div class="px-4 py-5 sm:px-6 flex flex-wrap items-center justify-between gap-y-2">
        <div>
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            Active Validators ({stats.total})
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            ON: {stats.on} | SHAME: {stats.shame} | Warning: {stats.warning || 0}
          </p>
        </div>
        <p class="text-xs text-gray-500">
          Last checked: {formatRelative(lastCheckAt)}
        </p>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Validator
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Operator
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Shame
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each validators as validator, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    {#if validator.logo_uri}
                      <div class="w-8 h-8 rounded-full overflow-hidden bg-gray-200 flex-shrink-0">
                        <img src={validator.logo_uri} alt={validator.name || 'Validator'} class="w-full h-full object-cover" />
                      </div>
                    {:else if validator.name}
                      <div class="w-8 h-8 rounded-full bg-sky-500 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                        {validator.name.substring(0, 2).toUpperCase()}
                      </div>
                    {/if}
                    <div class="flex flex-col">
                      <span class="text-gray-900 font-medium">{validator.name || '(unnamed)'}</span>
                      <div class="flex flex-wrap items-center gap-1.5 mt-1">
                        {#if validatorMonikers(validator)}
                          <span class="text-gray-500 text-xs">{validatorMonikers(validator)}</span>
                        {/if}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    {#if validator.operator_user}
                      <Avatar
                        user={validator.operator_user}
                        size="sm"
                        clickable={true}
                      />
                      <a
                        href={`/participant/${validator.operator_user.address}`}
                        onclick={(e) => { e.preventDefault(); push(`/participant/${validator.operator_user.address}`); }}
                        class="text-primary-600 hover:text-primary-800"
                      >
                        {validator.operator_user.name || truncateAddress(validator.operator_user.address)}
                      </a>
                    {:else}
                      <span class="text-gray-500 font-mono text-sm">{truncateAddress(validator.operator_address)}</span>
                    {/if}
                    <button
                      onclick={() => {
                        navigator.clipboard.writeText(validator.operator_address || '');
                        showSuccess('Address copied to clipboard!');
                      }}
                      aria-label="Copy operator address"
                      title="Copy operator address"
                      class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                      </svg>
                    </button>
                  </div>
                </td>
                <td class="px-6 py-4 min-w-[360px]">
                  <div class="flex flex-col gap-2">
                    <div>
                      <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${rowStatusClass(validator.status)}`}>
                        {statusText(validator.status)}
                      </span>
                    </div>

                    {#if validator.shame_reasons?.length}
                      <div class="flex flex-wrap items-center gap-x-1.5 gap-y-1.5">
                        {#each shameEntries(validator) as entry, index}
                          <span class={`inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium ring-1 ${entryClass(entry)}`}>
                            <span>{entry.text}</span>
                            {#if entry.details.length}
                              <span class="font-mono text-[11px] opacity-75">{entry.details.join(' / ')}</span>
                            {/if}
                            {#if entry.status === 'shame' && entry.days_in_shame !== null && entry.days_in_shame !== undefined}
                              <span class={`rounded px-1.5 py-0.5 text-[11px] font-semibold ${daysClass(entry.days_in_shame)}`}>
                                {formatDays(entry.days_in_shame)}
                              </span>
                            {:else if entry.status === 'warning'}
                              <span class="rounded bg-amber-200 px-1.5 py-0.5 text-[11px] font-semibold text-amber-950">
                                grace
                              </span>
                            {/if}
                          </span>
                          {#if index < shameEntries(validator).length - 1}
                            <span class="text-sm text-gray-400">,</span>
                          {/if}
                        {/each}
                      </div>
                    {:else}
                      <span class="text-sm text-gray-500">No shame reasons.</span>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if validators.length === 0}
        <div class="px-6 py-8 text-center text-gray-500">
          No validators to show.
        </div>
      {/if}
    </div>
  {/if}
</div>
