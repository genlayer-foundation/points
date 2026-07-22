<script>
  // @ts-nocheck
  import { socialTasksAPI } from '../lib/api.js';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { hasReadOnlyRoleSectionAccess } from '../lib/roleState.js';
  import { currentCategory } from '../stores/category.js';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';
  import { getCategoryAccent } from '../lib/categoryColors.js';
  import { getTaskLabels } from '../lib/socialTaskLabels.js';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';
  import SocialTaskCard from '../components/social-tasks/SocialTaskCard.svelte';

  let activeTab = $state('open');
  let search = $state('');
  let allTasks = $state(/** @type {any[]} */ ([]));
  let loading = $state(true);
  let error = $state('');
  let requestSequence = 0;

  let labels = $derived(getTaskLabels($currentCategory));
  let pageCategory = $derived(
    $currentCategory && $currentCategory !== 'global' ? $currentCategory : 'community'
  );
  let isRoleSectionReadOnly = $derived(
    hasReadOnlyRoleSectionAccess($userStore.user, pageCategory)
  );
  let accentColor = $derived(getCategoryAccent(pageCategory));
  let pageGradientStyle = $derived(getCategoryGradientStyle(pageCategory, accentColor));

  let openTasks = $derived(allTasks.filter((t) => t.status !== 'completed'));
  let completedTasks = $derived(allTasks.filter((t) => t.status === 'completed'));
  let counts = $derived({ open: openTasks.length, completed: completedTasks.length });

  let baseTasks = $derived(activeTab === 'completed' ? completedTasks : openTasks);
  let filteredTasks = $derived.by(() => {
    const term = search.trim().toLowerCase();
    if (!term) return baseTasks;
    return baseTasks.filter((t) =>
      [t.name, t.description, t.cta_text].some((field) =>
        String(field || '').toLowerCase().includes(term)
      )
    );
  });

  async function loadTasks(category) {
    const requestId = ++requestSequence;
    loading = true;
    error = '';
    try {
      /** @type {Record<string, string>} */
      const params = {};
      if (category && category !== 'global') params.category = category;
      const res = await socialTasksAPI.list(params);
      if (requestId !== requestSequence) return;
      allTasks = Array.isArray(res.data) ? res.data : [];
    } catch (e) {
      if (requestId !== requestSequence) return;
      error = 'Could not load tasks.';
      allTasks = [];
    } finally {
      if (requestId === requestSequence) loading = false;
    }
  }

  $effect(() => {
    const cat = $currentCategory;
    // Track auth so the list refetches with per-user statuses after an
    // in-place sign-in (the card's sign-in button does not remount the page).
    void $authState.isAuthenticated;
    loadTasks(cat);
  });

  function onCompleted({ task, completion }) {
    // Prefer the server's re-serialized task (authoritative status and
    // frozen points_awarded) over patching the local copy.
    allTasks = allTasks.map((t) =>
      t.slug === task.slug
        ? completion?.task ?? {
            ...t,
            status: 'completed',
            points_awarded: completion?.points_awarded ?? t.points,
          }
        : t
    );
  }

  const tabs = [
    { key: 'open', label: 'Open' },
    { key: 'completed', label: 'Completed' },
  ];
</script>

<div class="relative -mx-3 -my-3 min-h-[calc(100vh-64px)] overflow-hidden bg-white px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[220px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={pageGradientStyle}></div>
    <div class="absolute inset-0 bg-white/55"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
      <div class="flex min-w-0 items-start gap-3">
        <div class="mt-1 shrink-0">
          <CategoryIcon category={pageCategory} mode="hexagon" />
        </div>
        <div class="min-w-0">
          <h1
            class="font-display text-[34px] font-semibold leading-none text-black sm:text-[40px] md:text-[46px]"
            style="letter-spacing: -1px;"
          >
            {labels.title}
          </h1>
          {#if isRoleSectionReadOnly}
            <span class="mt-3 inline-flex min-h-7 items-center rounded-full border border-[#cdddf8] bg-[#edf4ff] px-3 text-[11px] font-semibold text-[#245ca8]">
              View-only access
            </span>
          {/if}
          <p class="mt-2 text-[14px] text-[#3f4b5f] sm:text-[15px]">{labels.subtitle}</p>
        </div>
      </div>

      <div class="flex w-full flex-col gap-2 md:flex-row xl:w-auto xl:items-center xl:justify-end">
        <label class="relative md:w-[300px]">
          <span class="sr-only">Search tasks</span>
          <input
            bind:value={search}
            class="h-10 w-full rounded-[8px] border border-[#e6e6e6] bg-white px-4 pr-10 text-[14px] text-black outline-none transition-colors placeholder:text-[#999] focus:border-[var(--task-accent)]"
            style="--task-accent: {accentColor}"
            placeholder="Search tasks"
          />
          <span
            class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#999]"
            aria-hidden="true"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
          </span>
        </label>
      </div>
    </header>

    <!-- Tabs -->
    <div class="flex w-fit gap-1 rounded-full border border-[#e6e6e6] bg-white p-1">
      {#each tabs as tab (tab.key)}
        <button
          type="button"
          onclick={() => (activeTab = tab.key)}
          aria-pressed={activeTab === tab.key}
          class="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-[13px] font-medium transition-colors {activeTab === tab.key ? 'bg-black text-white' : 'text-[#506078] hover:text-black'}"
        >
          {tab.label}
          <span
            class="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[11px] font-semibold {activeTab === tab.key ? 'bg-white/15 text-white' : 'bg-[#f1f1f4] text-[#506078]'}"
          >
            {counts[tab.key]}
          </span>
        </button>
      {/each}
    </div>

    <!-- Grid -->
    {#if loading}
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each Array(8) as _, i (i)}
          <div class="h-[160px] rounded-[8px] border border-[#f0f0f0] bg-white p-4">
            <div class="flex items-start justify-between">
              <div class="h-3 w-2/3 rounded bg-[#f1f1f1] animate-pulse"></div>
              <div class="h-4 w-12 rounded-full bg-[#f1f1f1] animate-pulse"></div>
            </div>
            <div class="mt-3 h-2.5 w-full rounded bg-[#f1f1f1] animate-pulse"></div>
            <div class="mt-1.5 h-2.5 w-5/6 rounded bg-[#f1f1f1] animate-pulse"></div>
          </div>
        {/each}
      </div>
    {:else if error}
      <div class="rounded-[8px] border border-red-100 bg-red-50 p-5">
        <p class="text-[13px] text-red-700">{error}</p>
      </div>
    {:else if filteredTasks.length === 0}
      <div class="rounded-[8px] border border-[#f0f0f0] bg-white p-12 text-center">
        <p class="text-[15px] font-medium text-black">
          {#if search.trim()}
            No tasks match "{search}"
          {:else if activeTab === 'completed'}
            No completed tasks yet
          {:else}
            Nothing to do right now
          {/if}
        </p>
        <p class="mt-1 text-[14px] text-[#7a7a7a]">
          {#if search.trim()}
            Try a different keyword or clear the search.
          {:else if activeTab === 'completed'}
            Complete a task and it will show up here.
          {:else}
            Check back soon for new tasks.
          {/if}
        </p>
      </div>
    {:else}
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {#each filteredTasks as task (task.slug)}
          <SocialTaskCard {task} {onCompleted} readOnly={isRoleSectionReadOnly} />
        {/each}
      </div>
    {/if}
  </div>
</div>
