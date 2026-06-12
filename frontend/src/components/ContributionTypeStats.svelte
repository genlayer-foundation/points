<script>
  import { push } from 'svelte-spa-router';
  import { contributionsAPI } from '../lib/api';
  import { currentCategory } from '../stores/category.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';
  import { getCategoryAccent, getCategoryPillColors } from '../lib/categoryColors.js';
  import { rgbaFromHex } from '../lib/categoryPresentation.js';

  let typeStats = $state(/** @type {any[]} */ ([]));
  let loading = $state(true);
  let error = $state(/** @type {string | null} */ (null));

  let activeCategory = $derived($currentCategory || 'global');
  let accentColor = $derived(getCategoryAccent(activeCategory));
  let pillColors = $derived(getCategoryPillColors(activeCategory));
  let cornerGlowStyle = $derived(
    `background: radial-gradient(circle at 100% 100%, ${rgbaFromHex(accentColor, 0.28)} 0%, ${rgbaFromHex(accentColor, 0.08)} 35%, transparent 65%);`
  );

  // Derived state: include submittable types plus non-submittable types explicitly marked
  // to show in contributions (e.g. informational / mission-host types). Sort by points desc.
  let submittableTypes = $derived(
    typeStats
      .filter((stats) => stats.is_submittable || stats.show_in_contributions)
      .sort((a, b) => {
        const aMaxPoints = (a.max_points || 0) * (a.current_multiplier || 1);
        const bMaxPoints = (b.max_points || 0) * (b.current_multiplier || 1);
        return bMaxPoints - aMaxPoints;
      })
  );

  $effect(() => {
    fetchTypeStatistics(activeCategory);
  });

  async function fetchTypeStatistics(category = activeCategory) {
    try {
      loading = true;
      error = null;

      /** @type {Record<string, string>} */
      const params = {};
      if (category !== 'global') {
        params.category = category;
      }

      const res = await contributionsAPI.getContributionTypeStatistics(params);
      typeStats = res.data || [];
      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load contribution type statistics';
      loading = false;
    }
  }

  function formatNumber(value) {
    return Number(value || 0).toLocaleString();
  }

  function formatPoints(stats) {
    if (stats?.min_points == null || stats?.max_points == null || stats?.current_multiplier == null) {
      return '0 pts';
    }

    const min = Math.round(stats.min_points * stats.current_multiplier);
    const max = Math.round(stats.max_points * stats.current_multiplier);
    return min === max ? `${min} pts` : `${min}-${max} pts`;
  }

  function renderMarkdown(text) {
    if (!text) return '';
    return parseMarkdown(text);
  }

  function cardGradientStyle() {
    return `background: linear-gradient(180deg, ${rgbaFromHex(accentColor, 0.95)} 0%, ${rgbaFromHex(accentColor, 0.28)} 58%, ${rgbaFromHex(accentColor, 0.06)} 100%);`;
  }

  function handleCardClick(event, stats) {
    if (event.target.closest('button') || event.target.closest('a')) return;
    push(`/contribution-type/${stats.id}`);
  }

  function handleCardKeydown(event, stats) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleCardClick(event, stats);
    }
  }

</script>

{#snippet typeSkeleton()}
  <div class="relative overflow-hidden rounded-[8px] border border-[#eef1f6] bg-white p-4 pl-5 shadow-[0_8px_18px_rgba(31,42,68,0.05)] sm:p-5 sm:pl-6">
    <div class="absolute inset-y-0 left-0 w-1.5 bg-[#f1f1f1] sk-shimmer"></div>
    <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap gap-2">
          <div class="h-5 w-16 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
          <div class="h-5 w-20 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        </div>
        <div class="mt-3 h-5 w-3/5 rounded bg-[#f1f1f1] sk-shimmer"></div>
        <div class="mt-3 space-y-2">
          <div class="h-3 w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
          <div class="h-3 w-11/12 rounded bg-[#f1f1f1] sk-shimmer"></div>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-1.5 lg:w-[260px]">
        <div class="h-12 rounded-[8px] bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-12 rounded-[8px] bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-12 rounded-[8px] bg-[#f1f1f1] sk-shimmer"></div>
      </div>
    </div>
  </div>
{/snippet}

<section class="relative overflow-hidden rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
  <div
    class="pointer-events-none absolute bottom-0 right-0 h-[260px] w-[280px]"
    style={cornerGlowStyle}
    aria-hidden="true"
  ></div>

  <div class="relative mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <div class="flex flex-wrap items-center gap-3">
        <h2 class="text-[22px] sm:text-[25px] font-semibold font-display text-black leading-none">
          Contribution Types
        </h2>
        {#if !loading && !error}
          <span class="inline-flex h-[25px] items-center rounded-full border border-[#e8ebf2] bg-white px-3 text-[12px] font-semibold text-[#506078]">
            {submittableTypes.length} open
          </span>
        {/if}
      </div>
      <p class="mt-2 text-[13px] sm:text-[14px] text-[#506078]">
        Open-ended contribution paths for builders, validators, and community members.
      </p>
    </div>

  </div>

  {#if loading}
    <div class="relative space-y-3">
      {#each Array(4) as _}
        {@render typeSkeleton()}
      {/each}
    </div>
  {:else if error}
    <div class="relative rounded-[8px] border border-red-100 bg-red-50 p-5">
      <h3 class="text-[14px] font-semibold text-red-800">Error loading contribution types</h3>
      <p class="mt-1 text-[13px] text-red-700">{error}</p>
    </div>
  {:else if submittableTypes.length === 0}
    <div class="relative rounded-[8px] border border-dashed border-[#dfe4ee] bg-white/70 p-8 text-center">
      <h3 class="text-[15px] font-semibold text-black">No contribution types available</h3>
      <p class="mt-1 text-[13px] text-[#6b6b6b]">Open calls will appear here when they are available.</p>
    </div>
  {:else}
    <div class="relative space-y-3">
      {#each submittableTypes as stats (stats.id)}
        <div
          class="group relative flex w-full cursor-pointer flex-col gap-4 overflow-hidden rounded-[8px] border border-[#eef1f6] bg-white p-4 pl-5 shadow-[0_8px_18px_rgba(31,42,68,0.05)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_28px_rgba(31,42,68,0.10)] lg:flex-row lg:items-stretch lg:justify-between sm:p-4 sm:pl-6"
          onclick={(event) => handleCardClick(event, stats)}
          onkeydown={(event) => handleCardKeydown(event, stats)}
          role="link"
          tabindex="0"
        >
          <div class="absolute inset-y-0 left-0 w-1.5" style={cardGradientStyle()} aria-hidden="true"></div>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <span class="inline-flex h-[24px] items-center rounded-full bg-[#f7f8fb] px-2.5 text-[11px] font-semibold uppercase text-[#667085]">
                Open call
              </span>
              <span
                class="inline-flex h-[24px] items-center rounded-full px-2.5 text-[12px] font-semibold"
                style="background: {pillColors.pillBg}; color: {pillColors.pillText};"
              >
                {formatPoints(stats)}
              </span>
              {#if stats.count === 0}
                <span class="inline-flex h-[24px] items-center rounded-full bg-amber-100 px-2.5 text-[12px] font-semibold text-amber-800">
                  Pioneer opportunity
                </span>
              {:else}
                <span class="inline-flex h-[24px] items-center rounded-full border border-[#e8ebf2] bg-white px-2.5 text-[12px] font-semibold text-[#506078]">
                  {formatNumber(stats.participants_count)} {Number(stats.participants_count) === 1 ? 'contributor' : 'contributors'}
                </span>
              {/if}
            </div>

            <div class="mt-3 min-w-0">
              <h3 class="line-clamp-2 text-[16px] font-semibold leading-snug text-black sm:text-[17px]">
                  {stats.name}
              </h3>

              {#if stats.description}
                <div class="markdown-preview mt-2 text-[13px] leading-5 text-[#6b6b6b]">
                  {@html renderMarkdown(stats.description)}
                </div>
              {:else}
                <p class="mt-2 text-[13px] leading-5 text-[#98a2b3]">
                  No description available.
                </p>
              {/if}
            </div>
          </div>

          <div class="grid gap-2 border-t border-[#eef1f6] pt-3 lg:w-[300px] lg:border-l lg:border-t-0 lg:pl-3 lg:pt-0">
            <div class="grid grid-cols-3 gap-1.5">
              <div class="rounded-[8px] border border-[#eef1f6] bg-[#fafafa] px-2 py-1.5">
                <p class="text-[10px] font-semibold uppercase text-[#98a2b3]">Accepted</p>
                <p class="mt-0.5 text-[13px] font-semibold text-black">{formatNumber(stats.count)}</p>
              </div>
              <div class="rounded-[8px] border border-[#eef1f6] bg-[#fafafa] px-2 py-1.5">
                <p class="text-[10px] font-semibold uppercase text-[#98a2b3]">Earned</p>
                <p class="mt-0.5 text-[13px] font-semibold text-black">{formatNumber(stats.total_points_given)} pts</p>
              </div>
              <div class="rounded-[8px] border border-[#eef1f6] bg-[#fafafa] px-2 py-1.5">
                <p class="text-[10px] font-semibold uppercase text-[#98a2b3]">Contributors</p>
                <p class="mt-0.5 text-[13px] font-semibold text-black">{formatNumber(stats.participants_count)}</p>
              </div>
            </div>

            <div class="flex items-center justify-end gap-2">
              <button
                type="button"
                onclick={(event) => { event.stopPropagation(); push(`/contribution-type/${stats.id}`); }}
                class="inline-flex h-8 items-center justify-center rounded-[8px] border border-[#dfe4ee] bg-white px-2.5 text-[12px] font-semibold text-[#506078] transition hover:border-black hover:text-black"
              >
                Details
              </button>
              {#if stats.is_submittable}
                <button
                  type="button"
                  onclick={(event) => { event.stopPropagation(); push(`/submit-contribution?type=${stats.id}`); }}
                  class="inline-flex h-8 items-center justify-center rounded-[8px] bg-black px-2.5 text-[12px] font-semibold text-white transition hover:-translate-y-0.5 hover:shadow-[0_10px_18px_rgba(31,42,68,0.14)]"
                >
                  Submit
                </button>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>

<style>
  .sk-shimmer {
    background-image: linear-gradient(
      90deg,
      rgba(241, 241, 241, 1) 0%,
      rgba(228, 228, 228, 1) 50%,
      rgba(241, 241, 241, 1) 100%
    );
    background-size: 200% 100%;
    animation: sk-shimmer 1.4s ease-in-out infinite;
  }

  @keyframes sk-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  .markdown-preview {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .markdown-preview :global(p),
  .markdown-preview :global(ul),
  .markdown-preview :global(ol),
  .markdown-preview :global(blockquote),
  .markdown-preview :global(pre),
  .markdown-preview :global(table),
  .markdown-preview :global(thead),
  .markdown-preview :global(tbody),
  .markdown-preview :global(tr),
  .markdown-preview :global(th),
  .markdown-preview :global(td),
  .markdown-preview :global(h1),
  .markdown-preview :global(h2),
  .markdown-preview :global(h3),
  .markdown-preview :global(h4),
  .markdown-preview :global(h5),
  .markdown-preview :global(h6) {
    display: inline;
    margin: 0;
    padding: 0;
    font-size: inherit;
    line-height: inherit;
    font-weight: inherit;
  }

  .markdown-preview :global(li) {
    display: inline;
  }

  .markdown-preview :global(li + li)::before {
    content: ' / ';
  }

  .markdown-preview :global(img),
  .markdown-preview :global(hr) {
    display: none;
  }

  .markdown-preview :global(a) {
    color: inherit;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .markdown-preview :global(strong) {
    font-weight: 600;
  }

  .markdown-preview :global(code) {
    border-radius: 4px;
    background: rgba(0, 0, 0, 0.06);
    padding: 0 4px;
    font-size: 0.95em;
  }
</style>
