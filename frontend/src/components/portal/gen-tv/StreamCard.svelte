<script>
  import { format } from 'date-fns';

  let { stream, variant = 'past' } = $props();

  function formatDateTime(value) {
    try {
      return format(new Date(value), "EEE, MMM d · HH:mm");
    } catch {
      return '';
    }
  }

  function formatDuration(start, end) {
    if (!start || !end) return '';
    try {
      const minutes = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60000);
      if (minutes <= 0) return '';
      if (minutes < 60) return `${minutes} min`;
      const h = Math.floor(minutes / 60);
      const m = minutes % 60;
      return m === 0 ? `${h}h` : `${h}h ${m}m`;
    } catch {
      return '';
    }
  }

  function hostLabel(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, '');
    } catch {
      return '';
    }
  }

  let isLive = $derived(variant === 'live');
  let isUpcoming = $derived(variant === 'upcoming');
  let categoryLabel = $derived(stream.category === 'internal' ? 'GenLayer Team' : 'Community');
  let host = $derived(hostLabel(stream.url));
  let duration = $derived(formatDuration(stream.starts_at, stream.ends_at));
</script>

<a
  href={stream.url}
  target="_blank"
  rel="noopener noreferrer"
  class="group w-full rounded-[8px] overflow-hidden relative cursor-pointer bg-[#f8f8f8] block"
>
  <div class="relative w-full aspect-[16/9]">
    {#if stream.image_url}
      <img
        src={stream.image_url}
        alt=""
        class="absolute inset-0 w-full h-full object-cover"
        loading="lazy"
      />
    {:else}
      <div class="absolute inset-0 bg-gradient-to-br from-gray-700 to-gray-900"></div>
    {/if}

    <div class="absolute inset-0 bg-gradient-to-b from-[rgba(0,0,0,0.2)] to-[rgba(0,0,0,0.7)]"></div>

    <div class="absolute top-0 left-0 right-0 p-2.5 flex items-start justify-between gap-2">
      <div class="flex items-center gap-1 min-w-0 flex-wrap">
        {#if isLive}
          <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500 text-white text-[10px] font-semibold uppercase tracking-wide">
            <span class="inline-block w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
            Live
          </span>
        {:else if isUpcoming}
          <span class="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-500 text-white text-[10px] font-semibold uppercase tracking-wide">
            Upcoming
          </span>
        {:else}
          <span class="inline-flex items-center px-2 py-0.5 rounded-full bg-slate-600 text-white text-[10px] font-semibold uppercase tracking-wide">
            Ended
          </span>
        {/if}

        {#if duration}
          <span class="inline-flex items-center px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-[10px] text-white text-[10px] font-medium tracking-wide">
            {duration}
          </span>
        {/if}
      </div>

      <div class="flex items-center p-1.5 rounded-[4px] backdrop-blur-[10px]" style="background: rgba(255,255,255,0.1);">
        <img src="/assets/featured-builds/arrow-right-up-line.svg" alt="" class="w-3.5 h-3.5">
      </div>
    </div>

    <div class="absolute bottom-0 left-0 right-0 p-3 space-y-0.5">
      <div class="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wide text-white/80">
        <span>{categoryLabel}</span>
        {#if host}
          <span class="opacity-60">·</span>
          <span class="normal-case font-medium opacity-80">{host}</span>
        {/if}
      </div>
      <h3 class="text-white {isLive ? 'text-[16px] sm:text-[17px]' : 'text-[13px]'} font-display font-medium leading-tight line-clamp-1">
        {stream.title}
      </h3>
      {#if stream.starts_at}
        <p class="text-[#cfcfcf] text-[11px]" style="letter-spacing: 0.22px;">
          {formatDateTime(stream.starts_at)}
        </p>
      {/if}
    </div>
  </div>
</a>
