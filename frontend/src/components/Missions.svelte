<script>
  import { onMount, onDestroy } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { marked } from 'marked';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { getPioneerContributionsColors } from '../lib/categoryColors.js';
  import Icons from './Icons.svelte';
  import Badge from './Badge.svelte';

  // State
  let missions = $state([]);
  let loading = $state(true);
  let countdowns = $state({});
  let countdownInterval = null;
  let expandedMissions = $state(new Set());

  // Character limit for truncating description
  const DESCRIPTION_CHAR_LIMIT = 150;

  // Configure marked options for security
  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
  });

  async function fetchMissions() {
    try {
      loading = true;
      const response = await contributionsAPI.getMissions({
        category: $currentCategory !== 'global' ? $currentCategory : undefined
      });

      if (response.data?.results !== undefined) {
        missions = response.data.results || [];
      } else {
        missions = response.data || [];
      }

      // Sort by nearest end date
      missions.sort((a, b) => {
        if (!a.end_date && !b.end_date) return 0;
        if (!a.end_date) return 1;
        if (!b.end_date) return -1;
        return new Date(a.end_date) - new Date(b.end_date);
      });

      // Initialize countdowns
      updateCountdowns();
    } catch (err) {
      console.error('Error loading missions:', err);
      missions = [];
    } finally {
      loading = false;
    }
  }

  function updateCountdowns() {
    const newCountdowns = {};
    missions.forEach(mission => {
      if (mission.end_date) {
        newCountdowns[mission.id] = getCountdown(mission.end_date);
      }
    });
    countdowns = newCountdowns;
  }

  function getCountdown(endDate) {
    if (!endDate) return null;

    const now = new Date();
    const end = new Date(endDate);
    const diffMs = end - now;

    if (diffMs <= 0) return 'Ended';

    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      return `${days}d ${hours}h`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  }

  function toggleMissionExpanded(missionId) {
    const newExpanded = new Set(expandedMissions);
    if (newExpanded.has(missionId)) {
      newExpanded.delete(missionId);
    } else {
      newExpanded.add(missionId);
    }
    expandedMissions = newExpanded;
  }

  function renderMarkdown(text) {
    if (!text) return '';
    try {
      return marked.parse(text);
    } catch (error) {
      console.error('Error parsing markdown:', error);
      return text;
    }
  }

  function needsExpansion(text) {
    return text && text.length > DESCRIPTION_CHAR_LIMIT;
  }

  function truncateText(text, limit) {
    if (!text || text.length <= limit) return text;
    return text.substring(0, limit) + '...';
  }

  onMount(() => {
    fetchMissions();
    // Update countdown every minute
    countdownInterval = setInterval(updateCountdowns, 60000);
  });

  onDestroy(() => {
    if (countdownInterval) {
      clearInterval(countdownInterval);
    }
  });

  $effect(() => {
    if ($currentCategory) {
      fetchMissions();
    }
  });
</script>

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .prose :global(p) {
    margin-top: 0;
    margin-bottom: 0.5rem;
  }
  
  .prose :global(p:last-child) {
    margin-bottom: 0;
  }

  .prose :global(strong) {
    font-weight: 600;
  }

  .prose :global(em) {
    font-style: italic;
  }

  .prose :global(h1),
  .prose :global(h2),
  .prose :global(h3),
  .prose :global(h4),
  .prose :global(h5),
  .prose :global(h6) {
    font-weight: 600;
    margin-top: 0.5rem;
    margin-bottom: 0.25rem;
  }

  .prose :global(ul),
  .prose :global(ol) {
    margin-top: 0.25rem;
    margin-bottom: 0.25rem;
    padding-left: 1.5rem;
  }

  .prose :global(li) {
    margin-top: 0.125rem;
    margin-bottom: 0.125rem;
  }

  .prose :global(code) {
    background-color: rgba(0, 0, 0, 0.05);
    padding: 0.125rem 0.25rem;
    border-radius: 0.25rem;
    font-size: 0.875em;
  }

  .prose :global(blockquote) {
    border-left: 3px solid rgba(0, 0, 0, 0.1);
    padding-left: 1rem;
    margin-left: 0;
    margin-right: 0;
    font-style: italic;
  }
</style>

{#if !loading && missions.length > 0}
  {@const colors = getPioneerContributionsColors($currentCategory)}

  <!-- Active Highlights Section - Pioneer Contributions Style -->
  <div class="{colors.containerBg} border {colors.containerBorder} shadow overflow-hidden rounded-lg mb-6">
    <div class="px-4 py-5 sm:px-6 {colors.headerBg} border-b {colors.headerBorder}">
      <div class="flex items-center">
        <Icons name="sparkle" size="md" className="{colors.headerIcon} mr-2" />
        <h3 class="text-lg leading-6 font-medium {colors.headerText}">
          Missions
        </h3>
      </div>
      <p class="mt-1 max-w-2xl text-sm {colors.descriptionText}">
        Special missions to contribute and earn points right now.
      </p>
    </div>

    <div class="bg-white">
      <table class="min-w-full divide-y {colors.tableBorder}">
        <thead class="{colors.tableHeaderBg}">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium {colors.tableHeaderText} uppercase tracking-wider">
              Mission
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium {colors.tableHeaderText} uppercase tracking-wider">
              Contribution Type
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium {colors.tableHeaderText} uppercase tracking-wider">
              Description
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium {colors.tableHeaderText} uppercase tracking-wider">
              Time Left
            </th>
            <th scope="col" class="px-6 py-3 text-right text-xs font-medium {colors.tableHeaderText} uppercase tracking-wider">
              Action
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y {colors.tableBorder}">
          {#each missions as mission, i}
            {@const isExpanded = expandedMissions.has(mission.id)}
            {@const hasLongText = needsExpansion(mission.description)}
            <tr class="{colors.tableHeaderBg}">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm font-bold {colors.titleText}">
                  {mission.name}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                {#if mission.contribution_type_details}
                  <Badge
                    badge={{
                      id: mission.contribution_type,
                      name: mission.contribution_type_details.name,
                      description: mission.contribution_type_details.description || '',
                      points: 0,
                      actionId: mission.contribution_type,
                      actionName: mission.contribution_type_details.name,
                      evidenceUrl: ''
                    }}
                    color={colors.badgeColor}
                    clickable={true}
                  />
                {:else}
                  <span class="text-sm {colors.contentText}">-</span>
                {/if}
              </td>
              <td class="px-6 py-4">
                <div class="flex items-start">
                  <div class="flex-1 text-sm {colors.contentText} prose prose-sm max-w-md">
                    {#if hasLongText && !isExpanded}
                      <div class="line-clamp-2">
                        {@html renderMarkdown(truncateText(mission.description, DESCRIPTION_CHAR_LIMIT))}
                      </div>
                    {:else}
                      {@html renderMarkdown(mission.description)}
                    {/if}
                  </div>
                  {#if hasLongText}
                    <button
                      onclick={() => toggleMissionExpanded(mission.id)}
                      class="ml-2 flex-shrink-0 text-gray-400 hover:text-gray-600"
                      aria-label="Toggle description"
                    >
                      <svg
                        class="h-4 w-4 transition-transform duration-200 {isExpanded ? 'rotate-180' : ''}"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  {/if}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                {#if mission.end_date && countdowns[mission.id]}
                  <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                    {countdowns[mission.id]}
                  </span>
                {:else}
                  <span class="text-sm {colors.contentText}">Ongoing</span>
                {/if}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right">
                <button
                  onclick={() => push(`/submit-contribution?type=${mission.contribution_type}`)}
                  class="inline-flex items-center text-sm font-medium {colors.titleText} hover:opacity-80"
                >
                  Submit
                  <svg class="ml-1 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>
{:else if loading}
  {@const colors = getPioneerContributionsColors($currentCategory)}
  <!-- Loading state -->
  <div class="{colors.containerBg} border {colors.containerBorder} shadow overflow-hidden rounded-lg mb-6">
    <div class="px-4 py-5 sm:px-6 {colors.headerBg} border-b {colors.headerBorder}">
      <div class="flex items-center">
        <div class="h-6 w-6 bg-gray-300 rounded animate-pulse mr-2"></div>
        <div class="h-6 w-32 bg-gray-300 rounded animate-pulse"></div>
      </div>
      <div class="mt-2 h-4 w-64 bg-gray-200 rounded animate-pulse"></div>
    </div>
    <div class="bg-white p-6">
      <div class="space-y-3">
        <div class="h-4 bg-gray-200 rounded animate-pulse"></div>
        <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
      </div>
    </div>
  </div>
{/if}