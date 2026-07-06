<script>
  import { push } from 'svelte-spa-router';
  import { validatorsAPI } from '../lib/api';
  import Avatar from '../components/Avatar.svelte';
  import { showSuccess, showError } from '../lib/toastStore';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';

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
   * @property {{ label: string, detail: string }[]} reasons
   * @property {string} status
   * @property {number | null | undefined} days_in_shame
   */

  const SHAME_ACCENT = '#3a7ce7';

  /** @type {ValidatorRow[]} */
  let validators = $state([]);
  let stats = $state({ total: 0, shame: 0, warning: 0 });
  /** @type {string | null} */
  let lastCheckAt = $state(null);
  let loading = $state(true);
  /** @type {string | null} */
  let error = $state(null);
  /** @type {Set<string>} */
  let expandedValidatorKeys = $state(new Set());
  let gradientStyle = $derived(getCategoryGradientStyle('validator', SHAME_ACCENT));

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
      validators = rows.filter(shouldShowValidator);
      stats = {
        total: validators.length,
        shame: validators.filter((validator) => validator.status === 'shame').length,
        warning: validators.filter((validator) => validator.status === 'warning').length,
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
  function statusText(value) {
    if (value === 'shame') return 'SHAME';
    if (value === 'warning') return 'WARNING';
    return 'ATTENTION';
  }

  /** @param {string} value */
  function sealClass(value) {
    if (value === 'warning') return 'border-amber-400 text-amber-600 bg-amber-50/80';
    return 'border-red-600 text-red-600 bg-red-50/80';
  }

  /** @param {string} network */
  function networkBadgeClass(network) {
    if (network === 'asimov') return 'border-blue-200 bg-blue-50 text-blue-700';
    if (network === 'bradbury') return 'border-violet-200 bg-violet-50 text-violet-700';
    return 'border-[#dfe4ee] bg-[#f3f5f9] text-[#506078]';
  }

  /** @param {string} network */
  function networkDayClass(network) {
    if (network === 'asimov') return 'bg-blue-600 text-white';
    if (network === 'bradbury') return 'bg-violet-600 text-white';
    return 'bg-[#111827] text-white';
  }

  /** @param {ShameEntry} entry */
  function entryClass(entry) {
    if (entry.status === 'shame') return 'border-red-100 bg-red-50 text-red-900';
    if (entry.status === 'warning') return 'border-amber-100 bg-amber-50 text-amber-950';
    return 'border-[#e8ebf2] bg-[#f8fafc] text-[#506078]';
  }

  /** @param {number} days */
  function daysClass(days) {
    if (days >= 7) return 'bg-red-600 text-white';
    if (days >= 3) return 'bg-orange-500 text-white';
    return 'bg-amber-300 text-[#3a2500]';
  }

  /** @param {number | null | undefined} days */
  function formatDays(days) {
    if (days === null || days === undefined) return '';
    if (days === 0) return 'today';
    if (days === 1) return '1d';
    return `${days}d`;
  }

  /** @param {ShameReason} reason */
  function isActionableReason(reason) {
    const label = (reason.label || '').toLowerCase();
    const hasActionStatus = reason.status === 'shame' || reason.status === 'warning';
    return hasActionStatus && !label.includes('no shame');
  }

  /** @param {ValidatorRow} validator */
  function shouldShowValidator(validator) {
    if (validator.status === 'unknown' || validator.status === 'on') return false;
    return (validator.shame_reasons || []).some(isActionableReason);
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
    if (network === 'asimov') return 'Asimov';
    if (network === 'bradbury') return 'Bradbury';
    return network || 'unknown';
  }

  /** @param {ValidatorRow} validator */
  function shameEntries(validator) {
    /** @type {Array<{ network: string, reasons: ShameReason[] }>} */
    const grouped = [];
    for (const reason of validator.shame_reasons || []) {
      if (!isActionableReason(reason)) continue;
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
      const reasons = group.reasons
        .map((reason) => ({
          label: reason.label,
          detail: reasonDetail(reason),
        }))
        .filter((reason) => reason.label);
      const shameReasons = group.reasons.filter((reason) => reason.status === 'shame');
      const days = shameReasons
        .map((reason) => reason.days_in_shame)
        .filter((days) => days !== null && days !== undefined);
      entries.push({
        network: group.network,
        reasons,
        status: shameReasons.length ? 'shame' : group.reasons[0]?.status || 'unknown',
        days_in_shame: days.length ? Math.max(...days) : null,
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

  /** @param {ValidatorRow} validator */
  function validatorInitials(validator) {
    const name = validator.name || validatorMonikers(validator) || 'Validator';
    return name.substring(0, 2).toUpperCase();
  }

  /** @param {ValidatorRow} validator */
  function operatorDisplayName(validator) {
    return validator.operator_user?.name || validator.name || validatorMonikers(validator) || '(unnamed)';
  }

  /** @param {ValidatorRow} validator */
  function operatorDisplayAddress(validator) {
    return validator.operator_address || validator.operator_user?.address || '';
  }

  /**
   * @param {ValidatorRow} validator
   * @param {number} index
   */
  function validatorKey(validator, index) {
    return validator.operator_address || validator.name || `validator-${index}`;
  }

  /**
   * @param {ValidatorRow} validator
   * @param {number} index
   */
  function isExpanded(validator, index) {
    return expandedValidatorKeys.has(validatorKey(validator, index));
  }

  /**
   * @param {ValidatorRow} validator
   * @param {number} index
   */
  function toggleExpanded(validator, index) {
    const key = validatorKey(validator, index);
    const next = new Set(expandedValidatorKeys);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    expandedValidatorKeys = next;
  }

  /** @param {ShameEntry[]} entries */
  function issueCount(entries) {
    return entries.reduce((total, entry) => total + entry.reasons.length, 0);
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

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[320px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={gradientStyle}></div>
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div class="space-y-2">
        <div class="flex items-start gap-3">
          <div class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[12px] bg-gradient-to-br from-[#8f7bff] to-[#6f8cff] shadow-[0_8px_18px_rgba(90,96,125,0.18)]">
            <img src="/assets/icons/shield-white.svg" alt="" class="h-5 w-5" />
          </div>
          <h1 class="min-w-0 break-words text-[34px] sm:text-[40px] md:text-[46px] font-semibold font-display text-black leading-none">
            Wall of Shame
          </h1>
        </div>
        <p class="max-w-2xl text-[14px] sm:text-[15px] text-[#3f4b5f]">
          Validators currently flagged by network health checks.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <div class="rounded-[8px] border border-white/70 bg-white/82 px-3 py-2 shadow-[0_8px_22px_rgba(31,42,68,0.08)] backdrop-blur-md">
          <div class="text-[11px] font-semibold uppercase text-[#7b8798]">Validators</div>
          <div class="text-[18px] font-semibold text-[#111827]">{stats.total}</div>
        </div>
        <div class="rounded-[8px] border border-white/70 bg-white/82 px-3 py-2 shadow-[0_8px_22px_rgba(31,42,68,0.08)] backdrop-blur-md">
          <div class="text-[11px] font-semibold uppercase text-[#7b8798]">Shame</div>
          <div class="text-[18px] font-semibold text-red-600">{stats.shame}</div>
        </div>
        <div class="rounded-[8px] border border-white/70 bg-white/82 px-3 py-2 shadow-[0_8px_22px_rgba(31,42,68,0.08)] backdrop-blur-md">
          <div class="text-[11px] font-semibold uppercase text-[#7b8798]">Warning</div>
          <div class="text-[18px] font-semibold text-amber-600">{stats.warning}</div>
        </div>
      </div>
    </header>

    <section class="rounded-[10px] border border-white/70 bg-white/78 p-5 sm:p-7 md:p-8 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md">
      {#if loading}
        <div class="space-y-4">
          <div class="h-6 w-44 rounded-full bg-[#f2f3f7] animate-pulse"></div>
          <div class="h-[360px] rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)] animate-pulse"></div>
        </div>
      {:else if error}
        <div class="rounded-[8px] border border-red-100 bg-red-50 p-5">
          <h3 class="text-[14px] font-semibold text-red-800">Error loading wall of shame</h3>
          <p class="mt-1 text-[13px] text-red-700">{error}</p>
        </div>
      {:else}
        <div class="space-y-4">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="text-[18px] font-semibold leading-6 text-black">Validators Requiring Attention</h2>
              <p class="mt-1 text-[13px] text-[#6b7280]">
                One row per validator. Network issues are grouped inside each row.
              </p>
            </div>
            <p class="text-[12px] font-medium text-[#7b8798]">
              Last checked: {formatRelative(lastCheckAt)}
            </p>
          </div>

          <div class="overflow-hidden rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
            {#if validators.length === 0}
              <div class="p-8 text-center text-[14px] text-[#6b7280]">
                No validators currently require attention.
              </div>
            {:else}
              <div class="space-y-3 bg-[#f8fafc] p-3 sm:p-4">
                {#each validators as validator, index}
                  {@const entries = shameEntries(validator)}
                  {@const expanded = isExpanded(validator, index)}
                  {@const totalIssues = issueCount(entries)}
                  <article class="overflow-hidden rounded-[8px] border border-[#e2e7f0] bg-white shadow-[0_10px_26px_rgba(31,42,68,0.08)]">
                    <div class="p-4 sm:p-5">
                      <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_160px] lg:items-center">
                        <div class="flex min-w-0 items-center gap-3">
                          {#if validator.operator_user}
                            <Avatar
                              user={validator.operator_user}
                              size="md"
                              clickable={true}
                            />
                          {:else if validator.logo_uri}
                            <div class="h-12 w-12 flex-shrink-0 overflow-hidden rounded-full bg-[#f3f5f9]">
                              <img src={validator.logo_uri} alt={operatorDisplayName(validator)} class="h-full w-full object-cover" />
                            </div>
                          {:else}
                            <div class="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-[#111827] text-[14px] font-semibold text-white">
                              {validatorInitials(validator)}
                            </div>
                          {/if}
                          <div class="min-w-0">
                            {#if validator.operator_user}
                              <a
                                href={`/participant/${validator.operator_user.id ?? validator.operator_user.address}`}
                                onclick={(e) => { e.preventDefault(); push(`/participant/${validator.operator_user.id ?? validator.operator_user.address}`); }}
                                class="block break-words text-[16px] font-semibold leading-6 text-[#111827] transition-colors hover:text-black"
                              >
                                {operatorDisplayName(validator)}
                              </a>
                            {:else}
                              <div class="break-words text-[16px] font-semibold leading-6 text-[#111827]">{operatorDisplayName(validator)}</div>
                            {/if}
                            <div class="mt-2 flex min-w-0 flex-wrap items-center gap-2">
                              <code class="min-w-0 truncate font-mono text-[12px] leading-5 text-[#7b8798]">{truncateAddress(operatorDisplayAddress(validator))}</code>
                              <button
                                onclick={async () => {
                                  try {
                                    await navigator.clipboard.writeText(operatorDisplayAddress(validator));
                                    showSuccess('Address copied to clipboard!');
                                  } catch {
                                    showError('Failed to copy address to clipboard.');
                                  }
                                }}
                                aria-label="Copy wallet address"
                                title="Copy wallet address"
                                class="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-[7px] border border-[#e8ebf2] bg-white text-[#7b8798] transition hover:border-[#d4dbea] hover:text-[#111827]"
                              >
                                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                                </svg>
                              </button>
                              {#each entries as entry}
                                <span class={`inline-flex min-h-7 items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${networkBadgeClass(entry.network)}`}>
                                  <span>{networkText(entry.network)}</span>
                                  {#if entry.status === 'shame' && entry.days_in_shame !== null && entry.days_in_shame !== undefined}
                                    <span class={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${networkDayClass(entry.network)}`}>
                                      {formatDays(entry.days_in_shame)}
                                    </span>
                                  {:else if entry.status === 'warning'}
                                    <span class={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${networkDayClass(entry.network)}`}>
                                      Grace
                                    </span>
                                  {/if}
                                </span>
                              {/each}
                            </div>
                            {#if validatorMonikers(validator)}
                              <div class="mt-1 truncate text-[12px] leading-5 text-[#9aa4b2]">{validatorMonikers(validator)}</div>
                            {/if}
                          </div>
                        </div>

                        <div class="flex flex-row items-center gap-3 sm:justify-between lg:flex-col lg:justify-center lg:gap-2">
                          <div class={`rotate-[-7deg] rounded-[6px] border-2 px-4 py-2 text-[18px] font-black uppercase leading-none tracking-normal shadow-[0_6px_18px_rgba(31,42,68,0.08)] ${sealClass(validator.status)}`}>
                            {statusText(validator.status)}
                          </div>
                          <button
                            type="button"
                            onclick={() => toggleExpanded(validator, index)}
                            class="inline-flex min-h-9 w-full items-center justify-center gap-2 rounded-[8px] border border-[#dfe4ee] bg-white px-3 text-[12px] font-semibold text-[#111827] shadow-[0_6px_14px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_10px_22px_rgba(31,42,68,0.11)] sm:w-auto lg:w-full"
                            aria-expanded={expanded}
                          >
                            {expanded ? `Hide reasons (${totalIssues})` : `View reasons (${totalIssues})`}
                            <svg class={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>

                    {#if expanded}
                      <div class="border-t border-[#eef1f6] bg-[#fbfcff] px-4 py-4 sm:px-5">
                        <div class="space-y-2">
                          {#each entries as entry}
                            <div class={`rounded-[8px] border p-3 ${entryClass(entry)}`}>
                              <div class="flex flex-wrap items-center gap-2">
                                <span class="text-[13px] font-semibold">{networkText(entry.network)}</span>
                                {#if entry.status === 'shame' && entry.days_in_shame !== null && entry.days_in_shame !== undefined}
                                  <span class={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${daysClass(entry.days_in_shame)}`}>
                                    {formatDays(entry.days_in_shame)}
                                  </span>
                                {:else if entry.status === 'warning'}
                                  <span class="rounded-full bg-amber-300 px-2 py-0.5 text-[11px] font-semibold text-[#3a2500]">
                                    Grace
                                  </span>
                                {/if}
                              </div>

                              <div class="mt-3 space-y-2">
                                {#each entry.reasons as reason}
                                  <div class="rounded-[7px] bg-white/80 px-3 py-2 ring-1 ring-black/5">
                                    <div class="text-[13px] font-semibold leading-5 text-inherit">
                                      {reason.label}
                                    </div>
                                    {#if reason.detail}
                                      <div class="mt-1 break-words font-mono text-[12px] leading-5 text-current opacity-80">
                                        {reason.detail}
                                      </div>
                                    {/if}
                                  </div>
                                {/each}
                              </div>
                            </div>
                          {/each}
                        </div>
                      </div>
                    {/if}
                  </article>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </section>
  </div>
</div>
