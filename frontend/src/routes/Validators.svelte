<script>
  import { push } from 'svelte-spa-router';
  import { validatorsAPI } from '../lib/api';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Avatar from '../components/Avatar.svelte';

  // State variables
  let validatorWallets = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let stats = $state({
    total: 0,
    active: 0,
    quarantined: 0,
    banned: 0,
    inactive: 0
  });

  let previousCategory = null;

  // Fetch validators when component mounts or category changes
  $effect(() => {
    if ($currentCategory && $currentCategory !== previousCategory) {
      previousCategory = $currentCategory;
      fetchValidatorWallets();
    }
  });

  async function fetchValidatorWallets() {
    try {
      loading = true;
      error = null;

      const response = await validatorsAPI.getAllValidatorWallets();
      validatorWallets = response.data?.wallets || [];
      stats = response.data?.stats || {
        total: 0,
        active: 0,
        quarantined: 0,
        banned: 0,
        inactive: 0
      };

      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load validator wallets';
      loading = false;
    }
  }

  function getStatusClass(status) {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'quarantined':
        return 'bg-red-100 text-red-800';
      case 'banned':
        return 'bg-gray-100 text-gray-800';
      case 'inactive':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-500';
    }
  }

  function getStatusText(status) {
    switch (status) {
      case 'active':
        return 'Active';
      case 'quarantined':
        return 'Quarantined';
      case 'banned':
        return 'Banned';
      case 'inactive':
        return 'Inactive';
      default:
        return 'Unknown';
    }
  }

  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }

  function formatStake(stakeWei) {
    if (!stakeWei) return '0 GEN';
    try {
      const stake = BigInt(stakeWei);
      const gen = Number(stake / BigInt(10 ** 18));
      return `${gen.toLocaleString()} GEN`;
    } catch {
      return '0 GEN';
    }
  }
</script>

<div>
  <h1 class="text-2xl font-bold text-gray-900 mb-6">
    Participants
  </h1>

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
      <div class="px-4 py-5 sm:px-6 flex justify-between items-center">
        <div>
          <h3 class="text-lg leading-6 font-medium text-gray-900">
            Participants ({stats.total})
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            Active: {stats.active} |
            Quarantined: {stats.quarantined} |
            Banned: {stats.banned} |
            Inactive: {stats.inactive}
          </p>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Validator Address
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                vStake
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                dStake
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Operator
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each validatorWallets as wallet, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(wallet.status)}`}>
                    {getStatusText(wallet.status)}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <span class="text-gray-900 font-mono">
                      {truncateAddress(wallet.address)}
                    </span>
                    <a
                      href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${wallet.address}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-gray-400 hover:text-gray-600"
                      title="View in Explorer"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
                      </svg>
                    </a>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatStake(wallet.v_stake)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {formatStake(wallet.d_stake)}
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
                    {:else if wallet.logo_uri || wallet.moniker}
                      {#if wallet.logo_uri}
                        <div class="w-8 h-8 rounded-full overflow-hidden bg-gray-200 flex-shrink-0">
                          <img src={wallet.logo_uri} alt={wallet.moniker || 'Validator'} class="w-full h-full object-cover" />
                        </div>
                      {:else}
                        <div class="w-8 h-8 rounded-full bg-sky-500 flex items-center justify-center text-white font-semibold text-sm flex-shrink-0">
                          {wallet.moniker.substring(0, 2).toUpperCase()}
                        </div>
                      {/if}
                      <span class="text-gray-700">{wallet.moniker || truncateAddress(wallet.operator_address)}</span>
                    {:else}
                      <span class="text-gray-500 font-mono">{truncateAddress(wallet.operator_address)}</span>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      {#if validatorWallets.length === 0}
        <div class="px-6 py-8 text-center text-gray-500">
          No validator wallets found. Data will be available after the sync job runs.
        </div>
      {/if}
    </div>
  {/if}
</div>
