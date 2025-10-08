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

  // Configure marked options for security and links
  const renderer = new marked.Renderer();
  // In marked v5+, the renderer receives a token object
  renderer.link = function({ href, title, text }) {
    // Handle undefined/null href values
    const safeHref = href || '#';
    return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer"${title ? ` title="${title}"` : ''}>${text}</a>`;
  };

  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false,
    renderer: renderer
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
    margin-bottom: 1rem;
    line-height: 1.5;
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
    margin-top: 1rem;
    margin-bottom: 0.5rem;
  }

  .prose :global(ul),
  .prose :global(ol) {
    margin-top: 0.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem 1.5rem;
    list-style-type: disc;
    background-color: rgba(0, 0, 0, 0.02);
    border-radius: 0.375rem;
  }

  .prose :global(ol) {
    list-style-type: decimal;
  }

  .prose :global(li) {
    margin-top: 0.25rem;
    margin-bottom: 0.25rem;
    display: list-item;
    line-height: 1.4;
  }

  .prose :global(a) {
    color: #ea580c;
    text-decoration: underline;
  }

  .prose :global(a:hover) {
    color: #c2410c;
  }

  .prose :global(code) {
    background-color: rgba(0, 0, 0, 0.06);
    padding: 0.25rem 0.5rem;
    border-radius: 0.375rem;
    font-size: 0.875em;
  }

  .prose :global(blockquote) {
    border-left: 3px solid rgba(0, 0, 0, 0.1);
    padding: 0.75rem 1rem;
    margin-top: 0.5rem;
    margin-bottom: 1rem;
    margin-left: 0;
    margin-right: 0;
    font-style: italic;
    background-color: rgba(0, 0, 0, 0.02);
    border-radius: 0.375rem;
  }
</style>

{#if !loading && missions.length > 0}
  {@const colors = getPioneerContributionsColors($currentCategory)}

  <!-- Card container with dividers -->
  <div class="bg-white border border-gray-200 border-l-4 {colors.containerBorderLeft} shadow-sm overflow-hidden rounded-lg mb-6">
    <!-- Header -->
    <div class="px-4 py-5 sm:px-6 bg-white border-b border-gray-200">
      <div class="flex items-center">
        <Icons name="sparkle" size="md" className="{colors.headerIcon} mr-2" />
        <h2 class="text-xl font-bold text-gray-900">Missions (time-limited)</h2>
      </div>
      <p class="mt-1 text-sm text-gray-600 leading-snug">
        Time limited contributions for the GenLayer Ecosystem. <br>Earn extra points, be showcased and climb the leaderboard.
      </p>
    </div>

    <!-- Missions with dividers -->
    {#each missions as mission}
      {@const isExpanded = expandedMissions.has(mission.id)}
      {@const hasLongText = needsExpansion(mission.description)}

      <div class="px-4 py-3 border-b last:border-b-0 hover:bg-gray-50 transition-colors">
        <!-- Title row with badges and submit button -->
        <div class="flex items-center gap-3 mb-2 flex-wrap">
          <h3 class="text-base font-bold font-heading text-gray-900">{mission.name}</h3>

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
              size="sm"
              bold={false}
              clickable={true}
            />
          {/if}

          {#if mission.end_date && countdowns[mission.id]}
            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
              {countdowns[mission.id]}
            </span>
          {:else}
            <span class="text-xs text-gray-600">Ongoing</span>
          {/if}

          <button
            onclick={() => push(`/submit-contribution?type=${mission.contribution_type}`)}
            class="ml-auto flex-shrink-0 text-sm font-normal {colors.titleText} {colors.titleTextHover} transition-colors"
          >
            Submit →
          </button>
        </div>

        <!-- Description -->
        <div class="text-sm text-gray-600 prose prose-sm max-w-3xl">
          {#if hasLongText && !isExpanded}
            <div class="line-clamp-2">
              {@html renderMarkdown(truncateText(mission.description, DESCRIPTION_CHAR_LIMIT))}
            </div>
          {:else}
            {@html renderMarkdown(mission.description)}
          {/if}
        </div>

        <!-- Read more button -->
        {#if hasLongText}
          <button
            onclick={() => toggleMissionExpanded(mission.id)}
            class="mt-1.5 inline-flex items-center text-sm {colors.titleText} {colors.titleTextHover} font-medium"
          >
            {isExpanded ? 'Show less' : 'Read more'}
            <svg
              class="ml-1 h-4 w-4 transition-transform duration-200 {isExpanded ? 'rotate-180' : ''}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        {/if}
      </div>
    {/each}
  </div>
{:else if loading}
  <!-- Loading state -->
  <div class="mb-4">
    <div class="flex items-center">
      <div class="h-6 w-6 bg-gray-300 rounded animate-pulse mr-2"></div>
      <div class="h-6 w-32 bg-gray-300 rounded animate-pulse"></div>
    </div>
    <div class="mt-2 h-4 w-64 bg-gray-200 rounded animate-pulse"></div>
  </div>
  <div class="space-y-3">
    <div class="bg-white border border-gray-200 rounded-lg p-4">
      <div class="h-4 bg-gray-200 rounded animate-pulse mb-2"></div>
      <div class="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
    </div>
  </div>
{/if}