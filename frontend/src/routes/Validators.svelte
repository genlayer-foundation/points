<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import api, { usersAPI, leaderboardAPI } from '../lib/api';
  import { getBannedValidators } from '../lib/blockchain';
  import { currentCategory, categoryTheme } from '../stores/category.js';
  
  // State variables
  let validators = $state([]);
  let loading = $state(true);
  let error = $state(null);
  
  onMount(async () => {
    await fetchValidators();
  });
  
  // Re-fetch when category changes
  $effect(() => {
    if ($currentCategory) {
      fetchValidators();
    }
  });
  
  async function fetchValidators() {
    try {
      loading = true;
      error = null;
      
      // For validators category, fetch from blockchain
      if ($currentCategory === 'validator') {
        // Fetch active validators from backend and banned validators from blockchain in parallel
        const [activeRes, bannedValidators] = await Promise.all([
          api.get('/users/validators/'),
          getBannedValidators()
        ]);
        
        const activeValidators = activeRes.data;
      
      // Get all unique validator addresses
      const allAddresses = [...new Set([...activeValidators, ...bannedValidators])];
      
      // Prepare validators with status
      const validatorsWithStatus = allAddresses.map(address => ({
        address,
        isActive: activeValidators.includes(address),
        isBanned: bannedValidators.includes(address),
        user: null,
        score: null
      }));
      
        // Get user data for validators
        const usersRes = await usersAPI.getUsers();
        const users = usersRes.data.results || [];
        
        // Get leaderboard data for category
        const leaderboardParams = $currentCategory !== 'global' ? { category: $currentCategory } : {};
        const leaderboardRes = await leaderboardAPI.getLeaderboard(leaderboardParams);
        const leaderboardEntries = leaderboardRes.data || [];
      
        // Merge data
        validatorsWithStatus.forEach(validator => {
        // Find user
        const user = users.find(u => u.address && u.address.toLowerCase() === validator.address.toLowerCase());
        if (user) {
          validator.user = user;
          // Add validator info if present
          if (user.validator) {
            validator.nodeVersion = user.validator.node_version;
            validator.matchesTarget = user.validator.matches_target;
            validator.targetVersion = user.validator.target_version;
          }
        }
        
        // Find leaderboard entry
        const leaderboardEntry = leaderboardEntries.find(entry => {
          // The leaderboard entry has user_details object with the address
          const userAddress = entry.user_details?.address || entry.user?.address;
          return userAddress && userAddress.toLowerCase() === validator.address.toLowerCase();
        });
        if (leaderboardEntry) {
          validator.score = leaderboardEntry.total_points;
          validator.rank = leaderboardEntry.rank;
        }
      });
      
        // Sort by active first, then rank or address
        validators = validatorsWithStatus.sort((a, b) => {
        // Active validators first
        if (a.isActive !== b.isActive) {
          return a.isActive ? -1 : 1;
        }
        
        // Then by banned status
        if (a.isBanned !== b.isBanned) {
          return a.isBanned ? 1 : -1;
        }
        
        // Then by rank (if available)
        if (a.rank && b.rank) {
          return a.rank - b.rank;
        }
        
        // Then by score
        if (a.score !== b.score) {
          return b.score - a.score;
        }
        
        // Finally by address
        return a.address.localeCompare(b.address);
      });
      
        loading = false;
      } else {
        // For builders and other categories, fetch users with that profile type
        const usersRes = await usersAPI.getUsers();
        const allUsers = usersRes.data.results || [];
        
        // Filter users based on category
        let categoryUsers = [];
        if ($currentCategory === 'builder') {
          categoryUsers = allUsers.filter(u => u.builder);
        } else if ($currentCategory === 'steward') {
          categoryUsers = allUsers.filter(u => u.steward);
        } else {
          // For global, show all users
          categoryUsers = allUsers;
        }
        
        // Get leaderboard data for category
        const leaderboardParams = $currentCategory !== 'global' ? { category: $currentCategory } : {};
        const leaderboardRes = await leaderboardAPI.getLeaderboard(leaderboardParams);
        const leaderboardEntries = leaderboardRes.data || [];
        
        // Format users as validators structure for consistency
        validators = categoryUsers.map(user => {
          const leaderboardEntry = leaderboardEntries.find(entry => {
            const userAddress = entry.user_details?.address || entry.user?.address;
            return userAddress && userAddress.toLowerCase() === user.address?.toLowerCase();
          });
          
          return {
            address: user.address,
            isActive: true,
            isBanned: false,
            user: user,
            score: leaderboardEntry?.total_points || null,
            rank: leaderboardEntry?.rank || null
          };
        }).sort((a, b) => {
          // Sort by rank first if available
          if (a.rank && b.rank) {
            return a.rank - b.rank;
          }
          if (a.rank) return -1;
          if (b.rank) return 1;
          
          // Then by score
          if (a.score !== b.score) {
            return (b.score || 0) - (a.score || 0);
          }
          
          // Finally by address
          return (a.address || '').localeCompare(b.address || '');
        });
        
        loading = false;
      }
    } catch (err) {
      error = err.message || 'Failed to load participants';
      loading = false;
    }
  }
  
  function getStatusClass(validator) {
    if (validator.isBanned) return 'bg-red-100 text-red-800';
    if (validator.isActive) return 'bg-green-100 text-green-800';
    return 'bg-gray-100 text-gray-800';
  }
  
  function getStatusText(validator) {
    if (validator.isBanned) return 'Banned';
    if (validator.isActive) return 'Active';
    return 'Inactive';
  }
  
  function truncateAddress(address) {
    if (!address) return '';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  }
</script>

<div>
  <div class="mb-5">
    <a href="/" onclick={(e) => { e.preventDefault(); push('/'); }} class="text-primary-600 hover:text-primary-700">
      ← Back to Dashboard
    </a>
  </div>
  
  <h1 class="text-3xl font-bold text-gray-900 mb-5">
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
                  <a 
                    href={`/participant/${validator.address}`}
                    onclick={(e) => { e.preventDefault(); push(`/participant/${validator.address}`); }}
                    class="text-primary-600 hover:text-primary-800 font-mono"
                  >
                    {truncateAddress(validator.address)}
                  </a>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  {#if validator.user && validator.user.name}
                    <span class="text-gray-900">{validator.user.name}</span>
                  {:else}
                    <span class="text-gray-400">—</span>
                  {/if}
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