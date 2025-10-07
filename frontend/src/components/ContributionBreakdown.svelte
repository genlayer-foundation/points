<script>
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { format } from 'date-fns';

  let {
    contributionTypes = [],
    colorTheme = 'sky',
    userAddress = null
  } = $props();

  const getBgColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-50' :
    colorTheme === 'green' ? 'bg-green-50' :
    'bg-sky-50'
  );

  const getBorderColor = $derived(
    colorTheme === 'orange' ? 'border-orange-200' :
    colorTheme === 'green' ? 'border-green-200' :
    'border-sky-200'
  );

  const getPointsBgColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-100 text-orange-800' :
    colorTheme === 'green' ? 'bg-green-100 text-green-800' :
    'bg-sky-100 text-sky-800'
  );

  const getDotColor = $derived(
    colorTheme === 'orange' ? 'bg-orange-500' :
    colorTheme === 'green' ? 'bg-green-500' :
    'bg-sky-500'
  );

  const getHoverColor = $derived(
    colorTheme === 'orange' ? 'hover:text-orange-600' :
    colorTheme === 'green' ? 'hover:text-green-600' :
    'hover:text-sky-600'
  );

  // State for expanded types and their contributions
  let expandedTypes = $state(new Set());
  let typeContributions = $state({});
  let loadingTypes = $state(new Set());

  // Function to toggle expansion and fetch contributions
  async function toggleExpanded(typeId) {
    // If we don't have a user address, navigate to the contribution type page
    if (!userAddress) {
      push(`/contribution-type/${typeId}`);
      return;
    }

    if (expandedTypes.has(typeId)) {
      // Collapse
      const newExpanded = new Set(expandedTypes);
      newExpanded.delete(typeId);
      expandedTypes = newExpanded;
    } else {
      // Expand and fetch contributions if not already loaded
      const newExpanded = new Set(expandedTypes);
      newExpanded.add(typeId);
      expandedTypes = newExpanded;

      // Fetch contributions if not already loaded
      if (!typeContributions[typeId]) {
        const newLoading = new Set(loadingTypes);
        newLoading.add(typeId);
        loadingTypes = newLoading;

        try {
          const response = await contributionsAPI.getContributions({
            user_address: userAddress,
            contribution_type: typeId,
            ordering: '-contribution_date',
            page_size: 100 // Get all contributions for this type
          });

          typeContributions = {
            ...typeContributions,
            [typeId]: response.data.results || []
          };
        } catch (error) {
          typeContributions = {
            ...typeContributions,
            [typeId]: []
          };
        } finally {
          const newLoading = new Set(loadingTypes);
          newLoading.delete(typeId);
          loadingTypes = newLoading;
        }
      }
    }
  }

  // Format date helper
  function formatDate(dateString) {
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch (e) {
      return dateString;
    }
  }
</script>

{#if contributionTypes && contributionTypes.length > 0}
  <div>
    <div class="mb-4">
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        Contribution Breakdown
      </h3>
      <p class="mt-1 text-sm text-gray-500">
        Points distribution across contribution types
      </p>
    </div>
    
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {#each contributionTypes as type}
        {@const isExpanded = expandedTypes.has(type.id)}
        {@const isLoading = loadingTypes.has(type.id)}
        {@const contributions = typeContributions[type.id] || []}

        <div class="{getBgColor} border {getBorderColor} rounded-lg p-4 hover:shadow-md transition-shadow">
          <div class="flex flex-col h-full">
            <div class="flex items-start justify-between mb-3">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <div class="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 {getDotColor}">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 6v12m6-6H6"></path>
                  </svg>
                </div>
                <h3 class="text-sm font-semibold text-gray-900 truncate">
                  <button
                    class="{getHoverColor} transition-colors flex items-center gap-1"
                    onclick={() => toggleExpanded(type.id)}
                  >
                    {type.name}
                    {#if userAddress}
                      <svg
                        class="w-4 h-4 transition-transform duration-200 {isExpanded ? 'rotate-180' : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    {/if}
                  </button>
                </h3>
              </div>
              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium font-heading {getPointsBgColor} ml-2 flex-shrink-0">
                {type.total_points} pts
              </span>
            </div>

            <div class="text-xs text-gray-500 mb-2">
              {#if type.count > 1}
                × {type.count} contributions
              {:else}
                × 1 contribution
              {/if}
            </div>

            <!-- Expanded content with contributions and evidence -->
            {#if isExpanded && userAddress}
              <div class="mt-3 pt-3 border-t {getBorderColor}">
                {#if isLoading}
                  <div class="flex justify-center py-2">
                    <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-gray-600"></div>
                  </div>
                {:else if contributions.length > 0}
                  <div class="space-y-2 max-h-60 overflow-y-auto">
                    {#each contributions as contribution}
                      <div class="text-xs space-y-1 pb-2 border-b {getBorderColor} last:border-b-0">
                        <div class="flex justify-between items-start">
                          <div class="flex-1">
                            {#if contribution.notes}
                              <div class="font-medium text-gray-700">{contribution.notes}</div>
                            {/if}
                            <div class="text-gray-500">{formatDate(contribution.contribution_date)}</div>
                          </div>
                          <div class="text-gray-700 font-medium ml-2">{contribution.frozen_global_points || contribution.points} pts</div>
                        </div>

                        {#if contribution.evidence_items && contribution.evidence_items.length > 0}
                          <div class="mt-1">
                            {#each contribution.evidence_items as evidence}
                              <div class="flex items-center gap-1">
                                <span class="text-gray-500">Evidence:</span>
                                {#if evidence.url}
                                  <a
                                    href={evidence.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    class="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline"
                                  >
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                    </svg>
                                    {evidence.description || 'View Link'}
                                  </a>
                                {/if}
                                {#if evidence.file_url}
                                  <a
                                    href={evidence.file_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    class="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline"
                                  >
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                    Download File
                                  </a>
                                {/if}
                              </div>
                            {/each}
                          </div>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {:else}
                  <p class="text-xs text-gray-500">No contributions found</p>
                {/if}
              </div>
            {/if}

            <div class="flex items-center gap-2 mt-auto">
              <div class="flex-1 bg-gray-200 rounded-full h-2">
                <div
                  class="h-2 rounded-full transition-all duration-300"
                  class:bg-purple-500={type.percentage >= 40}
                  class:bg-blue-500={type.percentage >= 25 && type.percentage < 40}
                  class:bg-green-500={type.percentage >= 10 && type.percentage < 25}
                  class:bg-gray-400={type.percentage < 10}
                  style={`width: ${type.percentage || 0}%`}
                ></div>
              </div>
              <span class="text-xs text-gray-600 font-medium min-w-[2.5rem] text-right">
                {type.percentage != null ? type.percentage.toFixed(0) : 0}%
              </span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  </div>
{/if}