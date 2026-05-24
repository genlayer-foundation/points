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

  function descriptionPreview(value) {
    if (!value) return '';
    return value
      .split(/\n\s*\n/)
      .find(Boolean)
      ?.replace(/\s+/g, ' ')
      .trim() || '';
  }

  function isDefaultImage(url) {
    return !url || url.includes('/default-banner.');
  }

  function withImageCacheKey(url, key) {
    if (!url || !key) return url || '';
    try {
      const imageUrl = new URL(url);
      imageUrl.searchParams.set('v', key);
      return imageUrl.toString();
    } catch {
      return `${url}${url.includes('?') ? '&' : '?'}v=${encodeURIComponent(key)}`;
    }
  }

  let imageFailed = $state(false);
  let isLive = $derived(variant === 'live');
  let isUpcoming = $derived(variant === 'upcoming');
  let categoryLabel = $derived(
    stream.detailed_category?.name ||
      stream.category_display ||
      (stream.category === 'internal' ? 'Internal team' : 'Community')
  );
  let host = $derived(hostLabel(stream.url));
  let duration = $derived(formatDuration(stream.starts_at, stream.ends_at));
  let dateTime = $derived(formatDateTime(stream.starts_at));
  let description = $derived(descriptionPreview(stream.description));
  let imageSrc = $derived(withImageCacheKey(stream.image_url, stream.updated_at || stream.id));
  let showDefaultInfo = $derived(isDefaultImage(stream.image_url) || imageFailed);

  $effect(() => {
    stream.image_url;
    stream.updated_at;
    imageFailed = false;
  });
</script>

<a
  href={stream.url}
  target="_blank"
  rel="noopener noreferrer"
  aria-label={`Open ${stream.title}${dateTime ? `, ${dateTime}` : ''}`}
  class="stream-card group w-full rounded-[8px] overflow-hidden relative cursor-pointer bg-[#111] block shadow-sm ring-1 ring-black/5 transition duration-300 hover:-translate-y-0.5 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black"
>
  <div class="relative w-full aspect-[16/9]">
    <div class="absolute inset-0 bg-gradient-to-br from-[#202020] via-[#111] to-black"></div>
    {#if imageSrc}
      <img
        src={imageSrc}
        alt=""
        class="absolute inset-0 w-full h-full object-cover"
        loading="lazy"
        onerror={(event) => {
          imageFailed = true;
          event.currentTarget.remove();
        }}
      />
    {/if}

    <div class="absolute inset-0 {showDefaultInfo ? 'bg-gradient-to-b from-black/5 via-black/10 to-black/75' : 'bg-gradient-to-b from-black/0 via-black/0 to-black/20'}"></div>

    <div class="absolute top-0 left-0 right-0 p-2.5 sm:p-3 flex items-start justify-between gap-3">
      <div class="min-w-0">
        {#if isLive}
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500 text-white text-[11px] font-semibold uppercase">
            <span class="inline-block w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
            Live
          </span>
        {:else if isUpcoming}
          <span class="inline-flex items-center px-2.5 py-1 rounded-full bg-[#f1c644] text-black text-[11px] font-semibold uppercase">
            Upcoming
          </span>
        {/if}
      </div>

      <div class="flex items-center p-2 rounded-[6px] backdrop-blur-[10px] bg-white/15 transition duration-300 group-hover:bg-white/25 group-focus-visible:bg-white/25">
        <img src="/assets/featured-builds/arrow-right-up-line.svg" alt="" class="w-4 h-4">
      </div>
    </div>

    <div class="stream-card-preview absolute bottom-0 left-0 right-0 p-3.5 sm:p-5 space-y-1.5 transition duration-200 {showDefaultInfo ? 'opacity-100 translate-y-0 group-hover:opacity-0 group-hover:translate-y-2 group-focus-visible:opacity-0 group-focus-visible:translate-y-2' : 'opacity-0 translate-y-2'}">
      <h3 class="stream-card-title text-white font-display font-medium line-clamp-2">
        {stream.title}
      </h3>
      {#if dateTime}
        <p class="stream-card-date text-white/80 font-medium">
          {dateTime}
        </p>
      {/if}
    </div>

    <div class="stream-card-hover absolute inset-0 p-3.5 sm:p-5 flex items-end bg-black/30 backdrop-blur-[14px] opacity-0 translate-y-3 transition duration-200 group-hover:opacity-100 group-hover:translate-y-0 group-focus-visible:opacity-100 group-focus-visible:translate-y-0">
      <div class="stream-card-copy space-y-3 drop-shadow-[0_2px_10px_rgba(0,0,0,0.65)]">
        <div class="space-y-1">
          <h3 class="stream-card-title text-white font-display font-medium line-clamp-2">
            {stream.title}
          </h3>
          {#if dateTime}
            <p class="stream-card-date text-white/70 font-medium">
              {dateTime}{duration ? ` · ${duration}` : ''}
            </p>
          {/if}
        </div>

        {#if description}
          <p class="stream-card-description text-white/85 leading-snug line-clamp-3 max-w-[58ch]">
            {description}
          </p>
        {/if}

        <div class="stream-card-meta flex items-center gap-2 font-semibold uppercase text-white/72">
          <span>{categoryLabel}</span>
          {#if host}
            <span class="opacity-50">·</span>
            <span class="normal-case font-medium">{host}</span>
          {/if}
        </div>
      </div>
    </div>
  </div>
</a>

<style>
  .stream-card {
    container-type: inline-size;
  }

  .stream-card-title {
    font-size: 22px;
    line-height: 1.05;
  }

  .stream-card-date {
    font-size: 14px;
    line-height: 1.25;
  }

  .stream-card-description {
    font-size: 15px;
  }

  .stream-card-meta {
    font-size: 11px;
  }

  @container (max-width: 340px) {
    .stream-card-preview,
    .stream-card-hover {
      padding: 12px;
    }

    .stream-card-title {
      font-size: 16px;
      line-height: 1.08;
    }

    .stream-card-date {
      font-size: 11px;
    }

    .stream-card-description {
      font-size: 12px;
      line-height: 1.28;
      -webkit-line-clamp: 2;
    }

    .stream-card-copy > :not([hidden]) ~ :not([hidden]) {
      margin-top: 8px;
    }

    .stream-card-meta {
      font-size: 10px;
    }
  }

  @container (max-width: 260px) {
    .stream-card-preview,
    .stream-card-hover {
      padding: 10px;
    }

    .stream-card-title {
      font-size: 14px;
    }

    .stream-card-description,
    .stream-card-meta {
      display: none;
    }
  }
</style>
