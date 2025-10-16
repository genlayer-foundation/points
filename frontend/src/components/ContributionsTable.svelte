<script>
  import { format } from 'date-fns';
  import { push } from 'svelte-spa-router';
  import Badge from './Badge.svelte';
  import Avatar from './Avatar.svelte';
  import { contributionsAPI } from '../lib/api';

  let {
    title = 'Recent Contributions',
    subtitle = 'Latest contributions',
    userAddress = null,
    category = null,
    limit = 5,
    showViewAllButton = true,
    viewAllUrl = '/all-contributions',
    showParticipantColumn = true,
    autoLoad = true
  } = $props();

  // State
  let contributions = $state([]);
  let loading = $state(false);
  let error = $state(null);
  let expandedRows = $state(new Set());

  // Toggle row expansion
  function toggleRowExpansion(contributionId) {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(contributionId)) {
      newExpanded.delete(contributionId);
    } else {
      newExpanded.add(contributionId);
    }
    expandedRows = newExpanded;
  }

  // Format date for display
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }

  // Fetch contributions from API
  async function loadContributions() {
    loading = true;
    error = null;

    try {
      const params = {
        page: 1,
        page_size: limit,
        ordering: '-contribution_date',
        group_consecutive: false // Disable grouping to show individual contributions with evidence
      };

      // Add optional filters
      if (userAddress) {
        params.user_address = userAddress;
      }
      if (category) {
        params.category = category;
      }

      const response = await contributionsAPI.getContributions(params);
      contributions = response.data.results || [];
    } catch (err) {
      error = err.message || 'Failed to load contributions';
      contributions = [];
    } finally {
      loading = false;
    }
  }

  // Watch for prop changes and reload contributions
  $effect(() => {
    if (autoLoad && (userAddress !== null || category !== null || limit)) {
      loadContributions();
    }
  });

  // Export the load function for manual triggering
  export function reload() {
    loadContributions();
  }
</script>

<div class="bg-white shadow rounded-lg overflow-hidden">
  <!-- Header -->
  <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
    <div>
      <h2 class="text-lg font-semibold text-gray-900">{title}</h2>
      <p class="mt-1 text-sm text-gray-600">{subtitle}</p>
    </div>
    {#if showViewAllButton}
      <button
        onclick={() => push(viewAllUrl)}
        class="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors flex items-center gap-1"
      >
        View All
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    {/if}
  </div>

  {#if loading}
    <div class="p-8 text-center">
      <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      <p class="mt-2 text-sm text-gray-600">Loading contributions...</p>
    </div>
  {:else if error}
    <div class="p-8 text-center">
      <p class="text-red-600">{error}</p>
    </div>
  {:else if contributions.length === 0}
    <div class="p-8 text-center">
      <p class="text-gray-600">No contributions found</p>
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            {#if showParticipantColumn}
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Participant
              </th>
            {/if}
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th class="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Points
            </th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              <span class="mr-4">Evidence</span>
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {#each contributions as contribution, i}
            <tr class="{i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-gray-50 transition-colors">
              {#if showParticipantColumn}
                <td class="px-6 py-4 whitespace-nowrap">
                  {#if contribution.user_details}
                    <div class="flex items-center">
                      <div class="flex-shrink-0 mr-3">
                        <Avatar
                          user={contribution.user_details}
                          size="sm"
                          clickable={true}
                        />
                      </div>
                      <div>
                        <button
                          onclick={() => push(`/participant/${contribution.user_details.address}`)}
                          class="text-left hover:opacity-80 transition-opacity"
                        >
                          <div class="text-sm font-medium text-gray-900">
                            {contribution.user_details.name || 'Participant'}
                          </div>
                          <div class="text-xs text-gray-500">
                            {`${contribution.user_details.address.substring(0, 6)}...${contribution.user_details.address.substring(contribution.user_details.address.length - 4)}`}
                          </div>
                        </button>
                      </div>
                    </div>
                  {:else}
                    <span class="text-gray-500 text-sm">Unknown</span>
                  {/if}
                </td>
              {/if}
              <td class="px-6 py-4 whitespace-nowrap">
                <Badge
                  badge={{
                    id: contribution.contribution_type?.id || contribution.contribution_type,
                    name: contribution.contribution_type_name || contribution.contribution_type?.name || 'Unknown',
                    description: '',
                    points: 0,
                    actionId: contribution.contribution_type?.id || contribution.contribution_type,
                    actionName: contribution.contribution_type_name || contribution.contribution_type?.name || 'Unknown',
                    evidenceUrl: ''
                  }}
                  color="green"
                  clickable={true}
                />
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDate(contribution.contribution_date)}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-center">
                <div class="text-sm font-medium text-gray-900">
                  {contribution.frozen_global_points || contribution.points || 0}
                </div>
              </td>
              <td class="px-6 py-4 text-right">
                {#if (contribution.evidence_items && contribution.evidence_items.length > 0) || contribution.notes}
                  <button
                    onclick={() => toggleRowExpansion(contribution.id)}
                    class="flex items-center justify-end gap-2 w-full hover:opacity-80 transition-opacity"
                  >
                    <div class="flex items-center gap-2">
                      {#if contribution.evidence_items && contribution.evidence_items.length > 0}
                        <span class="inline-flex items-center px-2.5 py-1 text-xs font-medium text-primary-700 bg-primary-50 rounded-full">
                          {contribution.evidence_items.length} {contribution.evidence_items.length === 1 ? 'item' : 'items'}
                        </span>
                      {/if}
                      {#if contribution.notes}
                        <span class="inline-flex items-center px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 rounded-full">
                          Notes
                        </span>
                      {/if}
                    </div>
                    <svg
                      class="w-4 h-4 text-gray-500 transition-transform {expandedRows.has(contribution.id) ? 'rotate-90' : ''}"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                {:else}
                  <span class="text-gray-400 text-sm">—</span>
                {/if}
              </td>
            </tr>
            {#if expandedRows.has(contribution.id)}
              <tr class="{i % 2 === 0 ? 'bg-gray-50' : 'bg-white'}">
                <td colspan={showParticipantColumn ? 5 : 4} class="px-8 py-4">
                  <div class="space-y-4">
                    {#if contribution.notes}
                      <div>
                        <h4 class="text-sm font-semibold text-gray-700 mb-2">Notes</h4>
                        <p class="text-sm text-gray-600 whitespace-pre-wrap">{contribution.notes}</p>
                      </div>
                    {/if}

                    {#if contribution.evidence_items && contribution.evidence_items.length > 0}
                      <div>
                        <h4 class="text-sm font-semibold text-gray-700 mb-2">Evidence</h4>
                        <div class="flex flex-wrap gap-3">
                          {#each contribution.evidence_items as evidence}
                            {#if evidence.url || evidence.file_url}
                              <!-- Clickable evidence with URL or file -->
                              <a
                                href={evidence.url || evidence.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="group flex items-center gap-2 bg-gray-50 hover:bg-gray-100 rounded border border-gray-200 hover:border-primary-300 p-3 max-w-sm transition-all duration-200 cursor-pointer"
                              >
                                <div class="flex-shrink-0">
                                  {#if evidence.url}
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-primary-600 group-hover:text-primary-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                  {:else}
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-green-600 group-hover:text-green-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                  {/if}
                                </div>
                                <div class="flex-1 min-w-0">
                                  <p class="text-xs text-gray-700 group-hover:text-gray-900 line-clamp-2 transition-colors">
                                    {evidence.description || (evidence.url ? 'External Link' : 'Download File')}
                                  </p>
                                </div>
                                <div class="flex-shrink-0">
                                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-gray-400 group-hover:text-gray-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                                  </svg>
                                </div>
                              </a>
                            {:else}
                              <!-- Text-only evidence -->
                              <div class="flex items-center gap-2 bg-gray-50 rounded border border-gray-200 p-3 max-w-sm">
                                <div class="flex-shrink-0">
                                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                  </svg>
                                </div>
                                <div class="flex-1 min-w-0">
                                  <p class="text-xs text-gray-700 line-clamp-2">{evidence.description}</p>
                                </div>
                              </div>
                            {/if}
                          {/each}
                        </div>
                      </div>
                    {/if}

                    {#if !contribution.notes && (!contribution.evidence_items || contribution.evidence_items.length === 0)}
                      <p class="text-sm text-gray-500 italic">No additional details available</p>
                    {/if}
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>