<script>
  import HighlightCard from './HighlightCard.svelte';

  let {
    highlights = [],
    loading = false,
    cardWidth = 300,
    cardHeight = 180,
    skeletonCount = 5,
    emptyTitle = 'No highlights yet',
    emptyMessage = 'Submit impactful or pioneering work and a steward may highlight it.',
    emptyAction = undefined, // optional snippet (e.g., a CTA button)
  } = $props();

  let scrollerEl = $state(null);
  let canLeft = $state(false);
  let canRight = $state(false);

  function updateArrows() {
    if (!scrollerEl) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollerEl;
    canLeft = scrollLeft > 4;
    canRight = scrollLeft + clientWidth < scrollWidth - 4;
  }

  function scrollBy(direction) {
    if (!scrollerEl) return;
    scrollerEl.scrollBy({
      left: direction * Math.round(scrollerEl.clientWidth * 0.8),
      behavior: 'smooth',
    });
  }

  $effect(() => {
    if (!scrollerEl) return;
    void highlights.length;
    requestAnimationFrame(updateArrows);
  });
</script>

{#if loading}
  <div class="flex gap-3 overflow-hidden pb-2">
    {#each Array(skeletonCount) as _}
      <div
        class="flex-shrink-0 rounded-[8px] bg-white border border-[#f0f0f0] p-4 flex flex-col gap-2 overflow-hidden"
        style="width: {cardWidth}px; height: {cardHeight}px;"
      >
        <!-- Top row: avatar + name | points + star -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-full bg-[#f1f1f1] skeleton-shimmer"></div>
            <div class="h-3 w-20 rounded bg-[#f1f1f1] skeleton-shimmer"></div>
          </div>
          <div class="flex items-center gap-2">
            <div class="h-4 w-12 rounded-full bg-[#f1f1f1] skeleton-shimmer"></div>
            <div class="w-7 h-7 rounded-full bg-[#f1f1f1] skeleton-shimmer"></div>
          </div>
        </div>
        <!-- Title + description -->
        <div class="flex-1 flex flex-col gap-1.5 pt-1">
          <div class="h-3 w-3/4 rounded bg-[#f1f1f1] skeleton-shimmer"></div>
          <div class="h-2.5 w-full rounded bg-[#f1f1f1] skeleton-shimmer"></div>
          <div class="h-2.5 w-5/6 rounded bg-[#f1f1f1] skeleton-shimmer"></div>
        </div>
        <!-- Footer -->
        <div class="flex items-center justify-between">
          <div class="h-4 w-24 rounded-full bg-[#f1f1f1] skeleton-shimmer"></div>
          <div class="h-3 w-16 rounded bg-[#f1f1f1] skeleton-shimmer"></div>
        </div>
      </div>
    {/each}
  </div>
{:else if highlights.length === 0}
  <div
    class="w-full rounded-[16px] border border-dashed border-[#e6e6e6] bg-[#fafafa] flex flex-col items-center justify-center text-center px-6 py-10 gap-3"
  >
    <div class="relative w-12 h-12">
      <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full opacity-90" />
      <div
        class="absolute inset-0 m-auto w-6 h-6"
        style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
      ></div>
    </div>
    <div class="flex flex-col gap-1 max-w-md">
      <h3 class="text-[15px] font-semibold text-black">{emptyTitle}</h3>
      <p class="text-[13px] text-[#6b6b6b] leading-snug">{emptyMessage}</p>
    </div>
    {#if emptyAction}
      <div class="mt-2">{@render emptyAction()}</div>
    {/if}
  </div>
{:else}
  <div class="relative">
    <div
      bind:this={scrollerEl}
      onscroll={updateArrows}
      class="flex gap-3 overflow-x-auto pb-2 -mx-1 px-1 hide-scrollbar scroll-smooth"
    >
      {#each highlights as highlight (highlight.id || highlight.contribution)}
        <div class="flex-shrink-0" style="width: {cardWidth}px;">
          <HighlightCard {highlight} height={cardHeight} />
        </div>
      {/each}
    </div>
    {#if canLeft}
      <button
        type="button"
        onclick={() => scrollBy(-1)}
        aria-label="Scroll left"
        class="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 w-9 h-9 rounded-full bg-white border border-[#e6e6e6] shadow-md flex items-center justify-center hover:bg-[#fafafa] hover:shadow-lg transition-all z-10"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 text-black">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
    {/if}
    {#if canRight}
      <button
        type="button"
        onclick={() => scrollBy(1)}
        aria-label="Scroll right"
        class="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-9 h-9 rounded-full bg-white border border-[#e6e6e6] shadow-md flex items-center justify-center hover:bg-[#fafafa] hover:shadow-lg transition-all z-10"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 text-black">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    {/if}
  </div>
{/if}

<style>
  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
  /* Subtle shimmer animation that's less harsh than animate-pulse */
  .skeleton-shimmer {
    background-image: linear-gradient(
      90deg,
      rgba(241, 241, 241, 1) 0%,
      rgba(230, 230, 230, 1) 50%,
      rgba(241, 241, 241, 1) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.4s ease-in-out infinite;
  }
  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
</style>
