<script>
  import { onDestroy } from 'svelte';
  import { format } from 'date-fns';

  let { streams = [] } = $props();

  let currentIndex = $state(0);
  let intervalId = null;

  let stream = $derived(streams[currentIndex] || null);

  function formatDateTime(value) {
    try {
      return format(new Date(value), "EEE, MMM d · HH:mm");
    } catch {
      return '';
    }
  }

  function selectStream(index) {
    currentIndex = index;
    startAutoAdvance();
  }

  function startAutoAdvance() {
    stopAutoAdvance();
    if (streams.length > 1) {
      intervalId = setInterval(() => {
        currentIndex = (currentIndex + 1) % streams.length;
      }, 6000);
    }
  }

  function stopAutoAdvance() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  $effect(() => {
    if (currentIndex >= streams.length) {
      currentIndex = 0;
    }
    startAutoAdvance();
  });

  onDestroy(() => {
    stopAutoAdvance();
  });

  let dateTime = $derived(stream ? formatDateTime(stream.starts_at) : '');
</script>

{#if stream}
  <div
    role="region"
    aria-label="Live streams"
    class="relative h-[320px] overflow-hidden rounded-[8px] bg-[#070707] sm:h-[460px] lg:h-[520px]"
    onmouseenter={stopAutoAdvance}
    onmouseleave={startAutoAdvance}
  >
    {#each streams as item, i (item.id)}
      <div
        class="absolute inset-0 transition-opacity duration-700 ease-in-out"
        style="opacity: {i === currentIndex ? 1 : 0};"
      >
        <div class="absolute inset-0 bg-gradient-to-br from-[#202020] via-[#111] to-black"></div>
        {#if item.image_url}
          <img
            src={item.image_url}
            alt=""
            class="absolute inset-0 h-full w-full scale-110 object-cover opacity-45 blur-2xl"
            loading={i === 0 ? 'eager' : 'lazy'}
            onerror={(event) => {
              event.currentTarget.remove();
            }}
          />
          <img
            src={item.image_url}
            alt=""
            class="absolute inset-0 h-full w-full object-cover sm:object-contain"
            loading={i === 0 ? 'eager' : 'lazy'}
            onerror={(event) => {
              event.currentTarget.remove();
            }}
          />
        {/if}
        <div class="absolute inset-0 bg-gradient-to-t from-black/88 via-black/20 to-black/10"></div>
        <div class="absolute inset-0 bg-gradient-to-r from-black/30 via-transparent to-black/20"></div>
      </div>
    {/each}

    <div class="absolute inset-x-0 bottom-0 z-10 p-4 sm:p-6 lg:p-8">
      <div class="max-w-[780px] space-y-2.5 sm:space-y-4">
        <div>
          <span class="inline-flex items-center gap-1.5 rounded-full bg-red-500 px-2.5 py-1 text-[11px] font-semibold uppercase text-white">
            <span class="h-1.5 w-1.5 rounded-full bg-white animate-pulse"></span>
            Live
          </span>
        </div>

        <div class="space-y-2">
          <h3 class="font-display text-[24px] sm:text-[44px] lg:text-[52px] font-medium leading-[0.98] text-white line-clamp-2">
            {stream.title}
          </h3>
          {#if dateTime}
            <p class="text-[12px] sm:text-[15px] font-medium text-white/75">
              {dateTime}
            </p>
          {/if}
        </div>

        <div>
          <a
            href={stream.url}
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex h-10 items-center gap-2 rounded-[20px] bg-white px-4 text-[14px] font-medium text-black transition hover:bg-white/90"
          >
            Watch now
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4">
          </a>
        </div>
      </div>
    </div>

    {#if streams.length > 1}
      <div class="absolute right-3 top-3 z-20 flex items-center gap-1.5 rounded-full bg-black/30 px-2 py-1.5 backdrop-blur-sm sm:bottom-6 sm:right-6 sm:top-auto lg:bottom-8 lg:right-8">
        {#each streams as _, i}
          <button
            type="button"
            onclick={() => selectStream(i)}
            class="h-1.5 rounded-full transition-all duration-300 ease-out {i === currentIndex ? 'w-5 bg-white' : 'w-1.5 bg-white/40 hover:bg-white/70'}"
            aria-label="Show live stream {i + 1}"
          ></button>
        {/each}
      </div>
    {/if}
  </div>
{/if}
