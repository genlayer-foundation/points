<script>
  import { push } from 'svelte-spa-router';
  import { validatorsAPI } from '../lib/api';
  import Avatar from '../components/Avatar.svelte';
  import { showSuccess } from '../lib/toastStore';

  let wallets = $state([]);
  let stats = $state({ total: 0, on: 0, shame: 0, unknown: 0 });
  let lastCheckAt = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let selectedNetwork = $state('all');

  $effect(() => {
    const _network = selectedNetwork;
    fetchWallOfShame();
  });

  async function fetchWallOfShame() {
    try {
      loading = true;
      error = null;
      const params = {};
      if (selectedNetwork !== 'all') {
        params.network = selectedNetwork;
      }
      const response = await validatorsAPI.getWallOfShame(params);
      wallets = response.data?.wallets || [];
      stats = response.data?.stats || { total: 0, on: 0, shame: 0, unknown: 0 };
      lastCheckAt = response.data?.last_grafana_check_at || null;
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load Wall of Shame';
      loading = false;
    }
  }

  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }

  function statusClass(value) {
    if (value === 'on') return 'bg-green-100 text-green-800';
    if (value === 'shame') return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-500';
  }

  function statusText(value) {
    if (value === 'on') return 'ON';
    if (value === 'shame') return 'SHAME';
    return '—';
  }

  function networkBadgeClass(network) {
    if (network === 'asimov') return 'bg-blue-100 text-blue-800';
    if (network === 'bradbury') return 'bg-purple-100 text-purple-800';
    return 'bg-gray-100 text-gray-800';
  }

  function networkLabel(network) {
    if (network === 'asimov') return 'Asimov';
    if (network === 'bradbury') return 'Bradbury';
    return network || 'Unknown';
  }

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
    <div class="flex space-x-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
      <button
        class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {selectedNetwork === 'all' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'}"
        onclick={() => (selectedNetwork = 'all')}
      >
        All Networks
      </button>
      <button
        class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {selectedNetwork === 'asimov' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'}"
        onclick={() => (selectedNetwork = 'asimov')}
      >
        Asimov
      </button>
      <button
        class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {selectedNetwork === 'bradbury' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'}"
        onclick={() => (selectedNetwork = 'bradbury')}
      >
        Bradbury
      </button>
    </div>

    <div class="bg-white shadow overflow-hidden sm:rounded-lg mb-8">
      <div class="px-4 py-5 sm:px-6 flex flex-wrap items-center justify-between gap-y-2">
        <div>
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            Active Validators ({stats.total})
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            ON: {stats.on} | SHAME: {stats.shame} | Unknown: {stats.unknown}
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
                Metrics
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Logs
              </th>
              <th scope="col" class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Network
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Validator
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Operator
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each wallets as wallet, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClass(wallet.metrics_status)}`}>
                    {statusText(wallet.metrics_status)}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClass(wallet.logs_status)}`}>
                    {statusText(wallet.logs_status)}
                  </span>
                </td>
                <td class="px-4 py-3 whitespace-nowrap">
                  <span class={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${networkBadgeClass(wallet.network)}`}>
                    {networkLabel(wallet.network)}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    {#if wallet.logo_uri}
                      <div class="w-8 h-8 rounded-full overflow-hidden bg-gray-200 flex-shrink-0">
                        <img src={wallet.logo_uri} alt={wallet.moniker || 'Validator'} class="w-full h-full object-cover" />
                      </div>
                    {:else if wallet.moniker}
                      <div class="w-8 h-8 rounded-full bg-sky-500 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                        {wallet.moniker.substring(0, 2).toUpperCase()}
                      </div>
                    {/if}
                    <div class="flex flex-col">
                      <span class="text-gray-900 font-medium">{wallet.moniker || '(unnamed)'}</span>
                      <div class="flex items-center gap-2 mt-0.5">
                        <span class="text-gray-500 font-mono text-xs">{truncateAddress(wallet.address)}</span>
                        <button
                          onclick={() => {
                            navigator.clipboard.writeText(wallet.address);
                            showSuccess('Address copied to clipboard!');
                          }}
                          title="Copy validator address"
                          class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors"
                        >
                          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                          </svg>
                        </button>
                        {#if wallet.explorer_url}
                          <a
                            href={`${wallet.explorer_url}/address/${wallet.address}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-gray-400 hover:text-gray-600"
                            title="View in Explorer"
                          >
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                            </svg>
                          </a>
                        {/if}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    {#if wallet.operator_user}
                      <Avatar
                        user={wallet.operator_user}
                        size="sm"
                        clickable={true}
                      />
                      <a
                        href={`/participant/${wallet.operator_user.address}`}
                        onclick={(e) => { e.preventDefault(); push(`/participant/${wallet.operator_user.address}`); }}
                        class="text-primary-600 hover:text-primary-800"
                      >
                        {wallet.operator_user.name || truncateAddress(wallet.operator_user.address)}
                      </a>
                    {:else}
                      <span class="text-gray-500 font-mono text-sm">{truncateAddress(wallet.operator_address)}</span>
                    {/if}
                    <button
                      onclick={() => {
                        navigator.clipboard.writeText(wallet.operator_address);
                        showSuccess('Address copied to clipboard!');
                      }}
                      title="Copy operator address"
                      class="p-1 text-gray-400 hover:text-gray-600 rounded hover:bg-gray-100 transition-colors"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if wallets.length === 0}
        <div class="px-6 py-8 text-center text-gray-500">
          No active validators found. Data will appear after the next Grafana sync.
        </div>
      {/if}
    </div>
  {/if}
</div>
