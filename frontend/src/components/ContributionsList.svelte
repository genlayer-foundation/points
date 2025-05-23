<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import Badge from './Badge.svelte';
  
  export let contributions = [];
  export let loading = false;
  export let error = null;
  export let showUser = true;
  
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
</script>

<div class="bg-white shadow overflow-hidden rounded-lg">
  <div class="px-4 py-5 sm:px-6">
    <h3 class="text-lg leading-6 font-medium text-gray-900">
      Contributions
    </h3>
    <p class="mt-1 max-w-2xl text-sm text-gray-500">
      Recent contributions with points and multipliers
    </p>
  </div>
  
  {#if loading}
    <div class="flex justify-center items-center p-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="p-6 text-center text-red-500">
      Failed to load contributions: {error}
    </div>
  {:else if contributions.length === 0}
    <div class="p-6 text-center text-gray-500">
      No contributions found.
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            {#if showUser}
              <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Contributor
              </th>
            {/if}
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Base Points
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Multiplier
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Global Points
            </th>
            <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Evidence
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#each contributions as contribution, i}
            <tr class={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              {#if showUser}
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-900">
                      <a href={`/participant/${contribution.user_details?.address || contribution.user?.address || contribution.address || ''}`} onclick={(e) => { e.preventDefault(); push(`/participant/${contribution.user_details?.address || contribution.user?.address || contribution.address || ''}`); }}>
                        {contribution.user_details?.name || contribution.user.name || contribution.user_details?.email || contribution.user.email}
                      </a>
                    </div>
                  </div>
                </td>
              {/if}
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge
                  badge={{
                    id: contribution.contribution_type?.id || contribution.contribution_type,
                    name: contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type',
                    description: contribution.contribution_type_description || contribution.contribution_type?.description || '',
                    points: 0,
                    actionId: contribution.contribution_type?.id || contribution.contribution_type,
                    actionName: contribution.contribution_type_name || (contribution.contribution_type?.name) || 'Unknown Type',
                    evidenceUrl: ''
                  }}
                  color="green"
                  clickable={true}
                />
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(contribution.contribution_date)}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {contribution.points}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {contribution.multiplier_at_creation}x
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-medium text-gray-900">{contribution.frozen_global_points}</div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                {#if contribution.evidence_url}
                  <a href={contribution.evidence_url} target="_blank" rel="noopener noreferrer" class="text-primary-600 hover:text-primary-900">
                    View
                  </a>
                {:else}
                  <span class="text-gray-400">None</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>