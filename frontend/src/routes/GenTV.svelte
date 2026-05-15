<script>
  import { onMount } from 'svelte';
  import { genTvAPI } from '../lib/api.js';
  import StreamCard from '../components/portal/gen-tv/StreamCard.svelte';
  import LiveStreamHero from '../components/portal/gen-tv/LiveStreamHero.svelte';
  import UpcomingStreamsSlider from '../components/portal/gen-tv/UpcomingStreamsSlider.svelte';

  let streams = $state([]);
  let loading = $state(true);
  let error = $state('');

  function devIso(offsetMinutes) {
    return new Date(Date.now() + offsetMinutes * 60000).toISOString();
  }

  function devStream(overrides) {
    return {
      description:
        'Development-only preview content for checking Gen TV live and upcoming layouts.',
      image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/gentalks-ep13.png',
      url: 'https://x.com/GenLayer',
      category: 'internal',
      ...overrides,
    };
  }

  // DEV MOCK DATA: remove this helper plus withDevPreviewStreams when the
  // multi-live/upcoming layout no longer needs manual preview data.
  function createDevPreviewStreams() {
    return [
      devStream({
        id: 'dev-live-preview-1',
        title: 'GenTalks Live Preview',
        slug: 'dev-live-preview-1',
        description:
          'Live preview stream used to check the first card in the live grid.',
        image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/gentalks-ep13.png',
        starts_at: devIso(-10),
        ends_at: devIso(50),
        status: 'live',
      }),
      devStream({
        id: 'dev-live-preview-2',
        title: 'Community Builders Live',
        slug: 'dev-live-preview-2',
        description:
          'Second live preview stream used to check how community livestreams appear in the same hero carousel.',
        image_url:
          'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/bradbury-hackathon-demo-day.png',
        starts_at: devIso(-25),
        ends_at: devIso(35),
        status: 'live',
        category: 'community',
      }),
      devStream({
        id: 'dev-upcoming-preview-1',
        title: 'FUD Markets Testnet Launch',
        slug: 'dev-upcoming-preview-1',
        description:
          'Upcoming preview stream used to check the first card in the upcoming grid.',
        image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/gentalks-ep13.png',
        starts_at: devIso(120),
        ends_at: devIso(150),
        status: 'upcoming',
      }),
      devStream({
        id: 'dev-upcoming-preview-2',
        title: 'GenLayer Builder Workshop',
        slug: 'dev-upcoming-preview-2',
        description:
          'Second upcoming preview stream used to check spacing with several scheduled streams.',
        image_url: 'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/gentalks-ep12.png',
        starts_at: devIso(360),
        ends_at: devIso(390),
        status: 'upcoming',
      }),
      devStream({
        id: 'dev-upcoming-preview-3',
        title: 'Hackathon Winners AMA',
        slug: 'dev-upcoming-preview-3',
        description:
          'Third upcoming preview stream used to force a full desktop row.',
        image_url:
          'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/bradbury-hackathon-winners.png',
        starts_at: devIso(720),
        ends_at: devIso(750),
        status: 'upcoming',
      }),
      devStream({
        id: 'dev-upcoming-preview-4',
        title: 'Community Demo Review',
        slug: 'dev-upcoming-preview-4',
        description:
          'Community upcoming preview stream used to check mixed team and community programming in one slider.',
        image_url:
          'https://res.cloudinary.com/dfqmoeawa/image/upload/gen_tv/bradbury-builders-hackathon-launch.png',
        starts_at: devIso(1440),
        ends_at: devIso(1470),
        status: 'upcoming',
        category: 'community',
      }),
    ];
  }

  function shouldShowDevPreviewStreams() {
    return import.meta.env.DEV && new URLSearchParams(window.location.search).get('mockGenTv') === '1';
  }

  function withDevPreviewStreams(items) {
    if (!shouldShowDevPreviewStreams()) return items;

    return [...createDevPreviewStreams(), ...items];
  }

  let liveStreams = $derived(
    streams
      .filter((s) => s.status === 'live')
      .sort((a, b) => new Date(b.starts_at) - new Date(a.starts_at))
  );
  let upcomingStreams = $derived(
    streams
      .filter((s) => s.status === 'upcoming')
      .sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at))
  );
  let pastStreams = $derived(
    streams
      .filter((s) => s.status === 'past')
      .sort((a, b) => new Date(b.starts_at) - new Date(a.starts_at))
  );
  let hasStreams = $derived(liveStreams.length || upcomingStreams.length || pastStreams.length);

  onMount(async () => {
    try {
      const res = await genTvAPI.list();
      streams = withDevPreviewStreams(res.data?.results || res.data || []);
    } catch (err) {
      if (shouldShowDevPreviewStreams()) {
        streams = createDevPreviewStreams();
      } else {
        error = err.message || 'Failed to load streams';
      }
    } finally {
      loading = false;
    }
  });
</script>

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="absolute inset-x-0 top-0 h-[300px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <img
      src="/assets/illustrations/welcome-gradient.png"
      alt=""
      class="absolute inset-0 w-full h-full object-cover opacity-70"
    />
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
  <img
    src="/assets/gen-tv/gentv-television-cropped.png"
    alt=""
    class="pointer-events-none fixed right-[-10px] top-[74px] z-0 w-[155px] max-w-none opacity-95 sm:right-[18px] sm:top-[82px] sm:w-[245px] lg:right-16 lg:top-[92px] lg:w-[335px]"
    loading="eager"
  />

  <header class="relative z-10 space-y-2 pr-[170px] sm:pr-[260px] lg:pr-[390px]">
      <h1 class="text-[42px] sm:text-[56px] md:text-[64px] font-semibold font-display text-black leading-none" style="letter-spacing: -1.6px;">
        Gen TV
      </h1>
      <p class="max-w-[560px] text-[14px] sm:text-[15px] text-[#3f4b5f]" style="letter-spacing: 0.2px;">
        Live and recorded streams from the GenLayer team and community.
      </p>
  </header>

  {#if loading}
    <div class="relative z-10 space-y-8">
      <div class="h-[320px] rounded-[8px] bg-[#f8f8f8] animate-pulse sm:h-[460px] lg:h-[520px]"></div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {#each [1, 2] as _}
          <div class="aspect-[16/9] rounded-[8px] bg-[#f8f8f8] animate-pulse"></div>
        {/each}
      </div>
    </div>
  {:else if error}
    <div class="relative z-10 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-[8px]">
      {error}
    </div>
  {:else if !hasStreams}
    <div class="relative z-10 bg-[#f8f8f8] rounded-[8px] p-12 text-center">
      <h3 class="font-heading font-semibold text-black">No streams yet</h3>
      <p class="mt-1 text-[14px] text-[#6b6b6b]">
        Streams will appear here once they're scheduled.
      </p>
    </div>
  {:else}
    <div class="relative z-10 space-y-9">
      {#if liveStreams.length > 0}
        <section class="space-y-3">
          <h2
            class="text-[16px] font-semibold text-black flex items-center gap-2"
            style="letter-spacing: 0.32px;"
          >
            <span class="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            Live now
          </h2>
          <LiveStreamHero streams={liveStreams} />
        </section>
      {/if}

      {#if upcomingStreams.length > 0}
        <UpcomingStreamsSlider streams={upcomingStreams} />
      {/if}

      {#if pastStreams.length > 0}
        <section class="space-y-3">
          <h2
            class="text-[16px] font-semibold text-black"
            style="letter-spacing: 0.32px;"
          >
            Latest Episodes
          </h2>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each pastStreams as stream (stream.id)}
              <StreamCard {stream} variant="past" />
            {/each}
          </div>
        </section>
      {/if}
    </div>
  {/if}
  </div>
</div>
