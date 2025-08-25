<script>
  import { push } from 'svelte-spa-router';
  import { fetchValidatorsData, getValidatorStatus } from '../lib/validators';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  import Avatar from '../components/Avatar.svelte';
  
  // State variables
  let validators = $state([]);
  let loading = $state(true);
  let error = $state(null);
  let stats = $state({});
  
  let previousCategory = null;
  
  // Fetch validators when component mounts or category changes
  $effect(() => {
    if ($currentCategory && $currentCategory !== previousCategory) {
      previousCategory = $currentCategory;
      fetchValidators();
    }
  });
  
  async function fetchValidators() {
    try {
      loading = true;
      error = null;
      
      // Define callback for when RPC data is ready
      const handleRpcDataReady = (enhancedData) => {
        // Update validators with enhanced RPC data
        if ($currentCategory === 'validator') {
          validators = enhancedData.validators;
        } else {
          validators = enhancedData.validators.filter(v => {
            if (!v.user) return false;
            if ($currentCategory === 'builder') {
              return v.user.builder !== null;
            }
            if ($currentCategory === 'steward') {
              return v.user.steward !== null;
            }
            return false;
          });
        }
        stats = enhancedData.stats;
      };
      
      // Use the shared validators utility with callback
      const result = await fetchValidatorsData($currentCategory, handleRpcDataReady);
      
      // Show initial data immediately
      if ($currentCategory === 'validator') {
        validators = result.validators;
      } else {
        validators = result.validators.filter(v => {
          if (!v.user) return false;
          if ($currentCategory === 'builder') {
            return v.user.builder !== null;
          }
          if ($currentCategory === 'steward') {
            return v.user.steward !== null;
          }
          return false;
        });
      }
      
      stats = result.stats;
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load participants';
      loading = false;
    }
  }
  
  function getStatusClass(validator) {
    return getValidatorStatus(validator).class;
  }
  
  function getStatusText(validator) {
    return getValidatorStatus(validator).text;
  }
  
  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }
</script>

<div>
  <h1 class="text-2xl font-bold text-gray-900 mb-6">
    {$currentCategory === 'builder' ? 'GenLayer Builders' : 
     $currentCategory === 'validator' ? 'GenLayer Validators' :
     'GenLayer Participants'}
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
            {$currentCategory === 'builder' ? 'Builders' : 
             $currentCategory === 'validator' ? 'Validators' :
             'Participants'} ({validators.length})
          </h3>
          <p class="mt-1 max-w-2xl text-sm text-gray-500">
            {#if $currentCategory === 'validator'}
              Active: {validators.filter(v => v.isActive).length} | 
              Banned: {validators.filter(v => v.isBanned).length} | 
              Inactive: {validators.filter(v => !v.isActive && !v.isBanned).length} | 
              Up to date: {validators.filter(v => v.matchesTarget).length}/{validators.filter(v => v.targetVersion).length}
            {:else}
              Total participants in {$currentCategory} category
            {/if}
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
                Address
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              {#if $currentCategory === 'validator'}
                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Node Version
                </th>
              {/if}
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Score
              </th>
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rank
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            {#each validators as validator, i}
              <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td class="px-6 py-4 whitespace-nowrap">
                  <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusClass(validator)}`}>
                    {getStatusText(validator)}
                  </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <a 
                      href={`/participant/${validator.address}`}
                      onclick={(e) => { e.preventDefault(); push(`/participant/${validator.address}`); }}
                      class="text-primary-600 hover:text-primary-800 font-mono"
                    >
                      {truncateAddress(validator.address)}
                    </a>
                    <a 
                      href={`${import.meta.env.VITE_EXPLORER_URL || 'https://explorer-asimov.genlayer.com'}/address/${validator.address}`}
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
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-3">
                    {#if validator.user}
                      <Avatar 
                        user={validator.user}
                        size="sm"
                        clickable={true}
                      />
                      <span class="text-gray-900">{validator.user.name || 'Unnamed'}</span>
                    {:else}
                      <span class="text-gray-400">—</span>
                    {/if}
                  </div>
                </td>
                {#if $currentCategory === 'validator'}
                  <td class="px-6 py-4 whitespace-nowrap">
                    {#if validator.nodeVersion}
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-sm">{validator.nodeVersion}</span>
                      {#if validator.matchesTarget}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <svg class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                          </svg>
                          Current
                        </span>
                      {:else if validator.targetVersion}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                          <svg class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
                          </svg>
                          Outdated
                        </span>
                      {/if}
                    </div>
                  {:else if validator.targetVersion}
                    <span class="text-gray-400 text-sm">
                      Not set
                      <span class="text-xs text-amber-600 ml-1">(Target: {validator.targetVersion})</span>
                    </span>
                  {:else}
                    <span class="text-gray-400">—</span>
                  {/if}
                  </td>
                {/if}
                <td class="px-6 py-4 whitespace-nowrap text-gray-900 font-medium">
                  {#if validator.user}
                    {validator.score || '—'}
                  {:else}
                    <span class="text-gray-400">—</span>
                  {/if}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  {#if validator.rank}
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800">
                      #{validator.rank}
                    </span>
                  {:else}
                    <span class="text-gray-400">—</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>