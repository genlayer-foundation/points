<script>
  import { onMount } from 'svelte';
  import { genTvAPI } from '../lib/api.js';
  import { getCategoryGradientStyle } from '../lib/categoryPresentation.js';
  import StreamCard from '../components/portal/gen-tv/StreamCard.svelte';
  import {
    pageHeader,
    communityLinks,
    agentResources,
    codingStreams,
    starterProjects,
    buildTools,
    networkResources,
    deepDiveReferences,
  } from '../data/resources.js';

  const builderGradientStyle = getCategoryGradientStyle('builder', '#ee8521');

  let copiedStates = $state({});
  let streams = $state([]);
  let starterTrack = $state(null);
  let tvTrack = $state(null);
  let canScrollStartersPrev = $state(false);
  let canScrollStartersNext = $state(false);
  let canScrollTvPrev = $state(false);
  let canScrollTvNext = $state(false);

  function asArray(maybe) {
    if (Array.isArray(maybe)) return maybe;
    if (Array.isArray(maybe?.results)) return maybe.results;
    return [];
  }

  function fallbackStream(item) {
    return {
      id: `fallback-${item.slug}`,
      slug: item.slug,
      title: item.title,
      description: item.description,
      url: item.url,
      image_url: item.image_url,
      starts_at: item.starts_at,
      ends_at: item.ends_at,
      status: 'past',
      category: 'internal',
    };
  }

  let codingStreamCards = $derived(
    codingStreams.map((item) => {
      const fallback = fallbackStream(item);
      const stream = streams.find((entry) => entry.slug === item.slug);

      if (!stream) return fallback;

      return {
        ...fallback,
        ...stream,
        title: stream.title || fallback.title,
        description: stream.description || fallback.description,
        url: stream.url || fallback.url,
        image_url: stream.image_url || fallback.image_url,
        starts_at: stream.starts_at || fallback.starts_at,
        ends_at: stream.ends_at || fallback.ends_at,
        category: stream.category || fallback.category,
      };
    })
  );

  function updateStarterScrollState() {
    if (!starterTrack) return;
    canScrollStartersPrev = starterTrack.scrollLeft > 4;
    canScrollStartersNext = starterTrack.scrollLeft + starterTrack.clientWidth < starterTrack.scrollWidth - 4;
  }

  function updateTvScrollState() {
    if (!tvTrack) return;
    canScrollTvPrev = tvTrack.scrollLeft > 4;
    canScrollTvNext = tvTrack.scrollLeft + tvTrack.clientWidth < tvTrack.scrollWidth - 4;
  }

  function scrollTrack(track, direction, updateState) {
    if (!track) return;
    track.scrollBy({
      left: direction * Math.max(track.clientWidth * 0.85, 280),
      behavior: 'smooth',
    });
    setTimeout(updateState, 320);
  }

  async function copyToClipboard(text, key) {
    try {
      await navigator.clipboard.writeText(text);
      copiedStates[key] = true;
      setTimeout(() => { copiedStates[key] = false; }, 2000);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      copiedStates[key] = true;
      setTimeout(() => { copiedStates[key] = false; }, 2000);
    }
  }

  onMount(async () => {
    try {
      const res = await genTvAPI.list();
      streams = asArray(res.data);
    } catch {
      streams = [];
    } finally {
      setTimeout(() => {
        updateStarterScrollState();
        updateTvScrollState();
      }, 0);
    }
  });
</script>

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="pointer-events-none absolute inset-x-0 top-0 h-[320px] overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0" style={builderGradientStyle}></div>
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 mx-auto flex max-w-[1180px] flex-col gap-6 px-1 pb-12 md:px-3">
    <header class="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
      <div class="flex flex-col gap-2">
        <h1 class="font-display text-[32px] font-medium leading-[38px] text-black md:text-[46px] md:leading-[50px]" style="letter-spacing: -0.96px;">
          {pageHeader.title}
        </h1>
      </div>

      <div class="flex items-center gap-2 md:pt-1">
        {#each communityLinks as link}
          <a
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={link.label}
            class="flex h-11 w-11 items-center justify-center rounded-full border transition hover:-translate-y-0.5 hover:shadow-sm"
            style="color: {link.color}; border-color: {link.color}3D; background: {link.color}14;"
          >
            {#if link.icon === 'telegram'}
              <svg class="h-[21px] w-[21px]" viewBox="0 0 24 24" fill="currentColor"><path d="M21.9 4.1 18.6 20c-.2 1.1-.9 1.4-1.8.9l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1 9.3-8.4c.4-.4-.1-.6-.6-.3L6 13.4l-5-1.6c-1.1-.3-1.1-1.1.2-1.6L20.5 2.8c.9-.3 1.7.2 1.4 1.3z" /></svg>
            {:else if link.icon === 'discord'}
              <svg class="h-[26px] w-[26px]" viewBox="0 0 32 32" fill="none">
                <path fill="currentColor" d="M9.7 9.2c1.3-.5 2.7-.8 4.1-1l.5 1.1c1.1-.1 2.3-.1 3.4 0l.5-1.1c1.4.2 2.8.5 4.1 1 2.5 3.4 3.5 7 3.1 10.9-1.5 1.1-3.1 2-4.9 2.5l-1-1.5c.6-.2 1.1-.5 1.6-.8-3.3 1.5-6.9 1.5-10.2 0 .5.3 1 .6 1.6.8l-1 1.5c-1.8-.5-3.4-1.4-4.9-2.5-.4-3.9.6-7.5 3.1-10.9Z" />
                <circle cx="12.3" cy="16" r="1.75" fill="white" />
                <circle cx="19.7" cy="16" r="1.75" fill="white" />
              </svg>
            {:else}
              <svg class="h-[20px] w-[20px]" viewBox="0 0 24 24" fill="currentColor"><path d="M18.2 2.3h3.3l-7.3 8.4 8.6 11h-6.7l-5.2-6.8-6 6.8H1.6l7.8-8.9L1.2 2.3H8l4.7 6.2 5.5-6.2zm-1.2 17.5h1.8L7 4.1H5l12 15.7z" /></svg>
            {/if}
          </a>
        {/each}
      </div>
    </header>

  <section class="grid grid-cols-1 gap-4 lg:grid-cols-[1.25fr_0.75fr]">
    <div class="agent-hero relative overflow-hidden rounded-[8px] bg-[#101010] p-5 text-white shadow-[0_18px_50px_rgba(38,48,75,0.16)] md:p-6">
      <img src="/assets/resources/coding-agents-background.png" alt="" class="absolute inset-0 h-full w-full object-cover opacity-70 mix-blend-screen" loading="eager" />
      <div class="absolute inset-0 bg-[#050505]/78"></div>
      <div class="absolute inset-0" style="background: linear-gradient(90deg, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.7) 52%, rgba(0,0,0,0.42) 100%);"></div>
      <div class="relative flex flex-col gap-5">
        <div class="flex flex-col gap-3">
          <span class="inline-flex w-fit items-center rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase text-white/70" style="letter-spacing: 0.8px;">
            Primary builder resource
          </span>
          <div class="flex flex-col gap-2">
            <h2 class="max-w-[700px] font-display text-[30px] font-medium leading-[34px] md:text-[42px] md:leading-[44px]" style="letter-spacing: -0.8px;">
              {agentResources.title}
            </h2>
            <p class="max-w-[680px] text-[14px] leading-[21px] text-white/72">
              {agentResources.description}
            </p>
          </div>
        </div>

        <div class="flex flex-col gap-2 sm:flex-row">
          <a
            href={agentResources.url}
            target="_blank"
            rel="noopener noreferrer"
            class="inline-flex h-10 items-center justify-center gap-2 rounded-[20px] bg-white px-4 text-[14px] font-medium text-black transition hover:bg-white/90"
          >
            Open skills
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4" />
          </a>
          <button
            type="button"
            onclick={() => copyToClipboard(agentResources.prompt, 'agent-prompt')}
            class="inline-flex h-10 items-center justify-center gap-2 rounded-[20px] border border-white/15 px-4 text-[14px] font-medium text-white transition hover:bg-white/10"
          >
            {#if copiedStates['agent-prompt']}
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
              Copied
            {:else}
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
              Copy agent prompt
            {/if}
          </button>
        </div>

        <div class="grid grid-cols-1 gap-2 border-t border-white/10 pt-4 sm:grid-cols-2">
          {#each agentResources.includedReferences as reference}
            <a href={reference.url} target="_blank" rel="noopener noreferrer" class="group flex min-h-[64px] items-center justify-between gap-3 rounded-[8px] border border-white/10 bg-white/[0.04] px-3 py-2.5 transition hover:bg-white/[0.08]">
              <span>
                <span class="block text-[13px] font-medium text-white">{reference.label}</span>
                <span class="mt-0.5 block text-[11px] leading-[15px] text-white/50">{reference.description}</span>
              </span>
              <svg class="h-3.5 w-3.5 shrink-0 text-white/35 transition group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
            </a>
          {/each}
        </div>
      </div>
    </div>

    <div class="rounded-[8px] border border-[#ebebeb] bg-white p-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-[12px] font-semibold uppercase text-[#387de8]" style="letter-spacing: 0.8px;">Network</p>
          <h2 class="mt-1 font-display text-[22px] font-medium leading-[26px] text-black">Track live transactions</h2>
        </div>
        <div class="flex h-8 w-8 items-center justify-center rounded-[8px] bg-[#387de8]/10 text-[#387de8]">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.7"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 0a8.25 8.25 0 0116.5 0m-16.5 0a8.25 8.25 0 0016.5 0M12 3.75c2.25 2.09 3.38 4.84 3.38 8.25S14.25 18.16 12 20.25M12 3.75C9.75 5.84 8.62 8.59 8.62 12s1.13 6.16 3.38 8.25" /></svg>
        </div>
      </div>

      <div class="mt-3 grid grid-cols-1 gap-2">
        {#each networkResources as item}
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            class="group flex items-center justify-between gap-3 rounded-[8px] border px-3 py-2 transition {item.kind === 'faucet' ? 'border-[#f5d2aa] bg-[#fff8f0] hover:border-[#ee8521]/55 hover:bg-white' : 'border-[#eef3fb] bg-[#f8fbff] hover:border-[#cfdcf7] hover:bg-white'}"
          >
            <span class="flex min-w-0 items-center gap-2.5">
              <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] {item.kind === 'faucet' ? 'bg-[#ee8521]/12 text-[#ee8521]' : 'bg-[#387de8]/10 text-[#387de8]'}">
                {#if item.kind === 'faucet'}
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.9"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3.75S6.75 9.8 6.75 14.1a5.25 5.25 0 0010.5 0C17.25 9.8 12 3.75 12 3.75z" /><path stroke-linecap="round" stroke-linejoin="round" d="M12 11.25v5.5m-2.75-2.75h5.5" /></svg>
                {:else}
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 0a8.25 8.25 0 0116.5 0m-16.5 0a8.25 8.25 0 0016.5 0M12 3.75c2.25 2.09 3.38 4.84 3.38 8.25S14.25 18.16 12 20.25M12 3.75C9.75 5.84 8.62 8.59 8.62 12s1.13 6.16 3.38 8.25" /></svg>
                {/if}
              </span>
              <span class="min-w-0">
                <span class="block text-[13px] font-medium text-black">{item.label}</span>
                <span class="mt-0.5 block text-[11px] leading-[15px] text-[#777]">{item.description}</span>
              </span>
            </span>
            <svg class="h-3.5 w-3.5 shrink-0 transition {item.kind === 'faucet' ? 'text-[#ee8521]/55 group-hover:text-[#ee8521]' : 'text-[#ababab] group-hover:text-[#387de8]'}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        {/each}
      </div>
    </div>
  </section>

  <section class="flex flex-col gap-3">
    <div class="flex items-end justify-between gap-4">
      <div class="flex flex-col gap-1">
        <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Open-Source Starters</h2>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">Scrollable project references with visible code paths and room for more examples.</p>
      </div>
      <div class="flex items-center gap-1">
        <button
          type="button"
          onclick={() => scrollTrack(starterTrack, -1, updateStarterScrollState)}
          disabled={!canScrollStartersPrev}
          class="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f5f5f5] disabled:cursor-default disabled:opacity-35"
          aria-label="Previous starters"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 18l-6-6 6-6" /></svg>
        </button>
        <button
          type="button"
          onclick={() => scrollTrack(starterTrack, 1, updateStarterScrollState)}
          disabled={!canScrollStartersNext}
          class="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f5f5f5] disabled:cursor-default disabled:opacity-35"
          aria-label="Next starters"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 6l6 6-6 6" /></svg>
        </button>
      </div>
    </div>

    <div
      bind:this={starterTrack}
      onscroll={updateStarterScrollState}
      class="flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-smooth pb-1"
      style="-ms-overflow-style: none; scrollbar-width: none;"
    >
      {#each starterProjects as project}
        <div class="flex min-h-[210px] w-[310px] flex-none snap-start flex-col gap-4 rounded-[8px] border p-4 sm:w-[350px] {project.featured ? 'border-[#101010] bg-[#101010] text-white' : 'border-[#f0f0f0] bg-white text-black'}">
          <div class="flex items-start justify-between gap-3">
            <div class="flex flex-col gap-2">
              <span class="w-fit rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase {project.featured ? 'bg-white/10 text-white/70' : 'bg-[#f5f5f5] text-[#6b6b6b]'}" style="letter-spacing: 0.7px;">
                {project.category}
              </span>
              <h3 class="font-display text-[22px] font-medium leading-[26px] {project.featured ? 'text-white' : 'text-black'}">
                {project.label}
              </h3>
            </div>
            {#if project.pending}
              <span class="rounded-full border px-2 py-1 text-[11px] font-medium {project.featured ? 'border-white/15 text-white/55' : 'border-[#ebebeb] text-[#ababab]'}">URL pending</span>
            {/if}
          </div>

          <p class="text-[14px] leading-[21px] {project.featured ? 'text-white/70' : 'text-[#6b6b6b]'}">
            {project.description}
          </p>

          <div class="mt-auto flex flex-wrap gap-2">
            {#if project.codeUrl || project.url}
              <a
                href={project.codeUrl || project.url}
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex h-9 items-center gap-2 rounded-[18px] px-3 text-[13px] font-medium {project.featured ? 'bg-white text-black hover:bg-white/90' : 'bg-[#101010] text-white hover:bg-[#2a2a2a]'}"
              >
                {project.codeUrl ? 'View code' : 'Open project'}
                {#if project.codeUrl}
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" /></svg>
                {:else}
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                {/if}
              </a>
            {:else}
              <span class="inline-flex h-9 items-center rounded-[18px] border px-3 text-[13px] font-medium {project.featured ? 'border-white/15 text-white/50' : 'border-[#ebebeb] text-[#ababab]'}">Code pending</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </section>

  <section class="flex flex-col gap-3">
    <div class="flex items-end justify-between gap-4">
      <div class="flex flex-col gap-1">
        <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Watch First</h2>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">GenTV coding content for builders who need a guided entry point.</p>
      </div>
      <div class="flex items-center gap-2">
        <a href="#/gen-tv" class="hidden text-[13px] font-medium text-[#6b6b6b] transition hover:text-black sm:inline-flex">
          View GenTV
        </a>
        <div class="flex items-center gap-1">
          <button
            type="button"
            onclick={() => scrollTrack(tvTrack, -1, updateTvScrollState)}
            disabled={!canScrollTvPrev}
            class="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f5f5f5] disabled:cursor-default disabled:opacity-35"
            aria-label="Previous GenTV videos"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 18l-6-6 6-6" /></svg>
          </button>
          <button
            type="button"
            onclick={() => scrollTrack(tvTrack, 1, updateTvScrollState)}
            disabled={!canScrollTvNext}
            class="flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-black transition hover:bg-[#f5f5f5] disabled:cursor-default disabled:opacity-35"
            aria-label="Next GenTV videos"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 6l6 6-6 6" /></svg>
          </button>
        </div>
      </div>
    </div>

    <div
      bind:this={tvTrack}
      onscroll={updateTvScrollState}
      class="flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-smooth pb-1"
      style="-ms-overflow-style: none; scrollbar-width: none;"
    >
      {#each codingStreamCards as stream (stream.id)}
        <div class="w-[82%] flex-none snap-start sm:w-[calc((100%_-_12px)/2)] lg:w-[calc((100%_-_24px)/3)] xl:w-[calc((100%_-_36px)/4)]">
          <StreamCard {stream} variant="past" />
        </div>
      {/each}
    </div>
  </section>

  <section class="grid min-w-0 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.82fr)]">
    <div class="flex min-w-0 flex-col gap-3">
      <div class="flex flex-col gap-1">
        <div class="flex min-w-0 items-center justify-between gap-3 sm:justify-start">
          <h2 class="shrink-0 text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Tools</h2>
          <div class="flex shrink-0 items-center gap-1.5">
            {#each buildTools.filter((tool) => ['cli', 'python', 'js'].includes(tool.icon)) as tool}
              <a
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={tool.label}
                title={tool.label}
                class="group flex h-8 w-8 items-center justify-center rounded-[8px] border border-[#e9e9e9] bg-white transition hover:-translate-y-0.5 hover:border-[#d8d8d8] hover:bg-[#fafafa] hover:shadow-sm sm:h-9 sm:w-9"
              >
                {#if tool.icon === 'js'}
                  <svg class="h-[18px] w-[18px] text-[#c7a900]" viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h18v18H3V3zm9.7 14.7c.4.8 1.1 1.4 2.4 1.4 1.4 0 2.5-.7 2.5-2.1 0-1.3-.8-1.8-2.2-2.4l-.4-.2c-.7-.3-1-.5-1-.9 0-.4.3-.7.8-.7.5 0 .8.2 1.1.7l1.5-1c-.5-.9-1.3-1.3-2.5-1.3-1.6 0-2.6 1-2.6 2.3 0 1.4.8 2 2.1 2.5l.4.2c.7.3 1.1.5 1.1 1 0 .4-.4.7-1 .7-.7 0-1.1-.4-1.4-1l-1.5.8zm-4.6.1c.3.6.9 1.2 2 1.2 1.2 0 2-.6 2-2.1v-4.6h-1.8v4.6c0 .6-.2.8-.6.8-.4 0-.6-.3-.8-.6l-1.5.9z" /></svg>
                {:else if tool.icon === 'python'}
                  <svg class="h-[18px] w-[18px] text-[#3776AB]" viewBox="0 0 24 24" fill="currentColor"><path d="M12.1 2c-4.8 0-4.5 2.1-4.5 2.1v2.2h4.6V7H5.8S3 6.7 3 11.5 5.4 16 5.4 16h1.4v-2s-.1-2.4 2.3-2.4h4.5s2.3 0 2.3-2.2V4.1S16.2 2 12.1 2zM9.6 3.4c.5 0 .8.4.8.8s-.4.8-.8.8-.8-.4-.8-.8.3-.8.8-.8zM12 22c4.8 0 4.5-2.1 4.5-2.1v-2.2h-4.6V17h6.4s2.7.3 2.7-4.5S18.6 8 18.6 8h-1.4v2s.1 2.4-2.3 2.4h-4.5s-2.3 0-2.3 2.2v5.3S7.8 22 12 22zm2.5-1.4c-.5 0-.8-.4-.8-.8s.4-.8.8-.8.8.4.8.8-.4.8-.8.8z" /></svg>
                {:else}
                  <svg class="h-[18px] w-[18px] text-[#101010]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.55"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5l3 2.25-3 2.25m4.5 0h3M5.25 20.25h13.5A2.25 2.25 0 0021 18V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v12a2.25 2.25 0 002.25 2.25z" /></svg>
                {/if}
                <span class="sr-only">{tool.label}</span>
              </a>
            {/each}
          </div>
        </div>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">SDKs as quick-launch icons, with Studio and local workflow tools below.</p>
      </div>

      <div class="min-w-0 rounded-[8px] border border-[#e9e9e9] bg-white p-3">
        <div class="grid grid-cols-1 gap-2">
          {#each buildTools.filter((tool) => !['cli', 'python', 'js'].includes(tool.icon)) as tool}
            {#if tool.url}
              <a href={tool.url} target="_blank" rel="noopener noreferrer" class="group flex min-h-[58px] items-center justify-between gap-3 rounded-[8px] border border-[#f0f0f0] bg-[#fafafa] px-3 py-2 transition hover:border-[#d8d8d8] hover:bg-white">
                <span class="flex min-w-0 items-center gap-3">
                  <span class="flex h-8 w-8 items-center justify-center rounded-[8px] {tool.icon === 'test' ? 'bg-[#3eb359]/12 text-[#3eb359]' : 'bg-[#ee8521]/12 text-[#ee8521]'}">
                    {#if tool.icon === 'test'}
                      <svg class="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.7"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M12 3.75l7.5 3v5.7c0 4.5-3.2 7.25-7.5 8.8-4.3-1.55-7.5-4.3-7.5-8.8v-5.7l7.5-3z" /></svg>
                    {:else}
                      <svg class="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.7"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 7.5h15m-12 4.5h9m-7.5 4.5h6M5.25 4.5h13.5A1.5 1.5 0 0120.25 6v12a1.5 1.5 0 01-1.5 1.5H5.25A1.5 1.5 0 013.75 18V6a1.5 1.5 0 011.5-1.5z" /></svg>
                    {/if}
                  </span>
                  <span class="min-w-0">
                    <span class="block text-[13px] font-semibold leading-[17px] text-black">{tool.label}</span>
                    <span class="mt-0.5 block text-[11px] leading-[15px] text-[#777]">{tool.description}</span>
                  </span>
                </span>
                <svg class="h-3.5 w-3.5 shrink-0 text-[#ababab] transition group-hover:text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            {:else}
              <div class="flex min-h-[58px] items-center justify-between gap-3 rounded-[8px] border border-dashed border-[#d7d7d7] bg-[#fafafa] px-3 py-2">
                <span class="flex min-w-0 items-center gap-3">
                  <span class="flex h-8 w-8 items-center justify-center rounded-[8px] bg-[#387de8]/10 text-[#387de8]">
                    <svg class="h-[18px] w-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.7"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 18.75h4.5M4.5 5.25A2.25 2.25 0 016.75 3h10.5a2.25 2.25 0 012.25 2.25v10.5A2.25 2.25 0 0117.25 18H6.75a2.25 2.25 0 01-2.25-2.25V5.25z" /></svg>
                  </span>
                  <span class="min-w-0">
                    <span class="block text-[13px] font-semibold leading-[17px] text-black">{tool.label}</span>
                    <span class="mt-0.5 block text-[11px] leading-[15px] text-[#777]">{tool.description}</span>
                  </span>
                </span>
                <span class="rounded-full border border-[#ebebeb] px-2 py-1 text-[11px] font-medium text-[#ababab]">Soon</span>
              </div>
            {/if}
          {/each}
        </div>
      </div>
    </div>

    <div class="flex min-w-0 flex-col gap-3">
      <div class="flex flex-col gap-1">
        <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Deep-Dive</h2>
        <p class="text-[14px] leading-[21px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">Direct references for advanced inspection.</p>
      </div>

      <div class="min-w-0 overflow-hidden rounded-[8px] border border-[#e9e9e9] bg-white">
        {#each deepDiveReferences as reference}
          <a href={reference.url} target="_blank" rel="noopener noreferrer" class="group flex items-start justify-between gap-4 border-t border-[#f0f0f0] p-4 first:border-t-0">
            <span class="flex min-w-0 flex-col gap-1">
              <span class="text-[14px] font-medium text-black transition group-hover:text-[#ee8521]">{reference.label}</span>
              <span class="text-[12px] leading-[18px] text-[#777]">{reference.description}</span>
            </span>
            <svg class="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#ababab] transition group-hover:text-[#ee8521]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        {/each}
      </div>
    </div>
  </section>
  </div>
</div>
