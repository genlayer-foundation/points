<script>
  import { onMount } from 'svelte';
  import { genTvAPI } from '../lib/api.js';
  import StreamCard from '../components/portal/gen-tv/StreamCard.svelte';

  // The label here is what's shown as the section heading; the id matches the
  // backend `Stream.category` value. Keeping this list small and explicit means
  // adding a new audience is a one-line change.
  const CATEGORIES = [
    { id: 'internal', label: 'GenLayer Team' },
    { id: 'community', label: 'Community' },
  ];

  let streams = $state([]);
  let loading = $state(true);
  let error = $state('');

  function bucket(category) {
    const inCat = streams.filter((s) => s.category === category);
    return {
      live: inCat.filter((s) => s.status === 'live'),
      upcoming: inCat
        .filter((s) => s.status === 'upcoming')
        .sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at)),
      past: inCat
        .filter((s) => s.status === 'past')
        .sort((a, b) => new Date(b.starts_at) - new Date(a.starts_at)),
    };
  }

  // Each entry is a category with its three buckets. Empty categories are
  // dropped here so we never render a heading with nothing under it.
  let groups = $derived(
    CATEGORIES.map((c) => ({ ...c, ...bucket(c.id) })).filter(
      (g) => g.live.length || g.upcoming.length || g.past.length
    )
  );

  onMount(async () => {
    try {
      const res = await genTvAPI.list();
      streams = res.data?.results || res.data || [];
    } catch (err) {
      error = err.message || 'Failed to load streams';
    } finally {
      loading = false;
    }
  });
</script>

<div class="space-y-10">
  <header class="space-y-1">
    <h1 class="text-[28px] font-medium font-display text-black" style="letter-spacing: -1px;">
      Gen TV
    </h1>
    <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">
      Live and recorded streams from the GenLayer team and community.
    </p>
  </header>

  {#if loading}
    <div class="space-y-8">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[10px]">
        {#each [1, 2, 3] as _}
          <div class="aspect-[16/9] rounded-[8px] bg-[#f8f8f8] animate-pulse"></div>
        {/each}
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-[10px]">
        {#each [1, 2, 3, 4] as _}
          <div class="aspect-[16/9] rounded-[8px] bg-[#f8f8f8] animate-pulse"></div>
        {/each}
      </div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-[8px]">
      {error}
    </div>
  {:else if groups.length === 0}
    <div class="bg-[#f8f8f8] rounded-[8px] p-12 text-center">
      <h3 class="font-heading font-semibold text-black">No streams yet</h3>
      <p class="mt-1 text-[14px] text-[#6b6b6b]">
        Streams will appear here once they're scheduled.
      </p>
    </div>
  {:else}
    {#each groups as group (group.id)}
      <section class="space-y-6">
        <h2
          class="text-[22px] font-medium font-display text-black"
          style="letter-spacing: -0.4px;"
        >
          {group.label}
        </h2>

        {#if group.live.length > 0}
          <section class="space-y-3">
            <h3
              class="text-[16px] font-semibold text-black flex items-center gap-2"
              style="letter-spacing: 0.32px;"
            >
              <span class="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              Live now
            </h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-[10px]">
              {#each group.live as stream (stream.id)}
                <StreamCard {stream} variant="live" />
              {/each}
            </div>
          </section>
        {/if}

        {#if group.upcoming.length > 0}
          <section class="space-y-3">
            <h3
              class="text-[16px] font-semibold text-black"
              style="letter-spacing: 0.32px;"
            >
              Upcoming
            </h3>
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-[10px]">
              {#each group.upcoming as stream (stream.id)}
                <StreamCard {stream} variant="upcoming" />
              {/each}
            </div>
          </section>
        {/if}

        {#if group.past.length > 0}
          <section class="space-y-3">
            <h3
              class="text-[16px] font-semibold text-black"
              style="letter-spacing: 0.32px;"
            >
              Past streams
            </h3>
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-[10px]">
              {#each group.past as stream (stream.id)}
                <StreamCard {stream} variant="past" />
              {/each}
            </div>
          </section>
        {/if}
      </section>
    {/each}
  {/if}
</div>
