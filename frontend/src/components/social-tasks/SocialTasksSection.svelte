<script>
  // @ts-nocheck
  import { push } from 'svelte-spa-router';
  import { socialTasksAPI } from '../../lib/api.js';
  import { authState } from '../../lib/auth.js';
  import { currentCategory } from '../../stores/category.js';
  import { rgbaFromHex } from '../../lib/categoryPresentation.js';
  import { getCategoryAccent } from '../../lib/categoryColors.js';
  import { getTaskLabels } from '../../lib/socialTaskLabels.js';
  import SocialTaskCard from './SocialTaskCard.svelte';

  let { limit = 8 } = $props();

  let tasks = $state([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let error = $state('');
  let slider = $state(null);
  let requestSequence = 0;

  let labels = $derived(getTaskLabels($currentCategory));
  let accentColor = $derived(getCategoryAccent($currentCategory));
  let cornerGlowStyle = $derived(
    `background: radial-gradient(circle at 100% 100%, ${rgbaFromHex(accentColor, 0.28)} 0%, ${rgbaFromHex(accentColor, 0.08)} 35%, transparent 65%);`
  );

  async function fetchTasks(category) {
    const requestId = ++requestSequence;
    loading = true;
    error = '';
    try {
      // The 'global' contributions page uses the community labels and links
      // to /community/tasks, so fetch community tasks there too — mixing in
      // builder/validator tasks would mislabel them and "View all" would drop
      // them.
      const params = { category: category && category !== 'global' ? category : 'community' };
      const res = await socialTasksAPI.list(params);
      if (requestId !== requestSequence) return;
      // Backend already returns active first, then completed.
      const data = Array.isArray(res.data) ? res.data : [];
      totalCount = data.length;
      tasks = data.slice(0, limit);
    } catch (e) {
      if (requestId !== requestSequence) return;
      error = 'Could not load tasks.';
      tasks = [];
      totalCount = 0;
    } finally {
      if (requestId === requestSequence) loading = false;
    }
  }

  $effect(() => {
    const cat = $currentCategory;
    // Track auth so the list refetches with per-user statuses after an
    // in-place sign-in (the card's sign-in button does not remount the page).
    void $authState.isAuthenticated;
    fetchTasks(cat);
  });

  function onCompleted({ task, completion }) {
    // Prefer the server's re-serialized task (authoritative status and
    // frozen points_awarded) over patching the local copy.
    tasks = tasks.map((t) =>
      t.slug === task.slug
        ? completion?.task ?? {
            ...t,
            status: 'completed',
            points_awarded: completion?.points_awarded ?? t.points,
          }
        : t
    );
  }

  function scroll(direction) {
    slider?.scrollBy({ left: direction * 300, behavior: 'smooth' });
  }
</script>

<!-- Render only when there are tasks for this category: no skeleton flash on
     categories without tasks, no error banner for an auxiliary section (the
     full-page route still surfaces load errors). -->
{#if !loading && !error && tasks.length > 0}
  <section
    class="relative overflow-hidden rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8"
  >
    <!-- Subtle category-color glow in the bottom-right corner -->
    <div
      class="pointer-events-none absolute bottom-0 right-0 h-[260px] w-[280px]"
      style={cornerGlowStyle}
      aria-hidden="true"
    ></div>

    <div class="relative mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div class="flex flex-wrap items-center gap-3">
          <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
            {labels.title}
          </h2>
          <span
            class="inline-flex h-[25px] items-center rounded-full border border-[#e8ebf2] bg-white px-3 text-[12px] font-semibold text-[#506078]"
          >
            {totalCount} {totalCount === 1 ? 'task' : 'tasks'}
          </span>
        </div>
        <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
          {labels.subtitle}
        </p>
      </div>

      <div class="flex items-center gap-2">
        {#if tasks.length > 1}
          <button
            type="button"
            aria-label="Scroll social tasks left"
            onclick={() => scroll(-1)}
            class="hidden h-11 w-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] sm:inline-flex"
          >
            <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Scroll social tasks right"
            onclick={() => scroll(1)}
            class="hidden h-11 w-11 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] sm:inline-flex"
          >
            <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="h-5 w-5" />
          </button>
        {/if}

        <button
          type="button"
          onclick={() => push(labels.listPath)}
          class="inline-flex h-11 items-center justify-center gap-1.5 rounded-[8px] border border-[#dfe4ee] bg-white px-3 text-[13px] font-semibold text-[#111827] shadow-[0_8px_18px_rgba(31,42,68,0.06)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)]"
        >
          View all
          <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4" />
        </button>
      </div>
    </div>

    <div
      bind:this={slider}
      class="slider-scroll relative flex snap-x gap-3 overflow-x-auto pb-2"
    >
      {#each tasks as task (task.slug)}
        <div class="w-[280px] max-w-[82vw] flex-shrink-0 snap-start">
          <SocialTaskCard {task} {onCompleted} />
        </div>
      {/each}
    </div>
  </section>
{/if}

<style>
  .slider-scroll {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .slider-scroll::-webkit-scrollbar {
    display: none;
  }
</style>
