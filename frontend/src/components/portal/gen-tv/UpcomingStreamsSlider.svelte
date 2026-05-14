<script>
  import { onMount } from 'svelte';
  import StreamCard from './StreamCard.svelte';

  let { streams = [] } = $props();

  let track = $state(null);
  let canScrollPrev = $state(false);
  let canScrollNext = $state(false);

  let isSlider = $derived(streams.length > 2);

  function updateScrollState() {
    if (!track) return;
    canScrollPrev = track.scrollLeft > 4;
    canScrollNext = track.scrollLeft + track.clientWidth < track.scrollWidth - 4;
  }

  function scrollByPage(direction) {
    if (!track) return;
    track.scrollBy({
      left: direction * track.clientWidth,
      behavior: 'smooth',
    });
    requestAnimationFrame(updateScrollState);
  }

  onMount(() => {
    updateScrollState();
  });
</script>

{#if streams.length > 0}
  <div class="space-y-3">
    <div class="flex items-center justify-between gap-3">
      <h3
        class="text-[16px] font-semibold text-black flex items-center gap-2"
        style="letter-spacing: 0.32px;"
      >
        <span class="inline-block w-2 h-2 rounded-full bg-[#f1c644]"></span>
        Upcoming Streams
      </h3>

      {#if isSlider}
        <div class="hidden sm:flex items-center gap-1">
          <button
            type="button"
            onclick={() => scrollByPage(-1)}
            disabled={!canScrollPrev}
            class="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f5f5f5] disabled:cursor-default disabled:opacity-35"
            aria-label="Previous upcoming streams"
          >
            <span aria-hidden="true">‹</span>
          </button>
          <button
            type="button"
            onclick={() => scrollByPage(1)}
            disabled={!canScrollNext}
            class="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f5f5f5] disabled:cursor-default disabled:opacity-35"
            aria-label="Next upcoming streams"
          >
            <span aria-hidden="true">›</span>
          </button>
        </div>
      {/if}
    </div>

    {#if isSlider}
      <div
        bind:this={track}
        onscroll={updateScrollState}
        class="flex snap-x snap-mandatory gap-4 overflow-x-auto scroll-smooth pb-1"
      >
        {#each streams as stream (stream.id)}
          <div class="w-full flex-none snap-start sm:w-[calc((100%_-_1rem)/2)]">
            <StreamCard {stream} variant="upcoming" />
          </div>
        {/each}
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {#each streams as stream (stream.id)}
          <StreamCard {stream} variant="upcoming" />
        {/each}
      </div>
    {/if}
  </div>
{/if}
