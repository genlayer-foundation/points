<script>
  import { onMount, onDestroy } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { featuredAPI } from '../../lib/api.js';
  import { resolvePortalLink } from '../../lib/links.js';

  let { category = 'builder', showNewsLink = false } = $props();

  let heroes = $state([]);
  let currentIndex = $state(0);
  let intervalId = $state(null);
  let loading = $state(true);

  let hero = $derived(heroes.length > 0 ? heroes[currentIndex] : null);
  let placement = $derived(showNewsLink ? 'overview' : category);
  let showDashboardFallback = $derived(!showNewsLink && !loading && !hero);
  let fallbackGradient = $derived(
    category === 'validator'
      ? 'linear-gradient(135deg, #1f56f2 0%, #4f76f6 48%, #b8c7ff 100%)'
      : category === 'community'
        ? 'linear-gradient(135deg, #6f35d7 0%, #7f52e1 48%, #d6c3ff 100%)'
        : 'linear-gradient(135deg, #d96816 0%, #ee8521 48%, #ffd1a3 100%)'
  );
  let loadingGradient = $derived(showNewsLink ? 'linear-gradient(to right, #c4bfe8, #eae9f3)' : fallbackGradient);
  let fallbackEyebrow = $derived(
    category === 'validator' ? 'Validator Dashboard' : category === 'community' ? 'Community Dashboard' : 'Builder Dashboard'
  );
  let fallbackTitle = $derived(
    category === 'validator' ? 'Join Validator Journey' : category === 'community' ? 'Community Journey' : 'Builder Journey'
  );
  let fallbackDescription = $derived(
    category === 'validator'
      ? 'Track validator progress, waitlist activity, and network participation across the GenLayer ecosystem.'
      : category === 'community'
        ? 'Follow community contributions, active members, and the latest progress across GenLayer.'
        : 'Discover builder activity, featured contributions, and the teams shaping GenLayer.'
  );
  let fallbackActionLabel = $derived(category === 'validator' ? 'Join the waitlist' : 'View contributions');
  let fallbackActionPath = $derived(
    category === 'validator'
      ? '/validators/waitlist/join'
      : category === 'community'
        ? '/community/all-contributions'
        : '/builders/all-contributions'
  );

  function startAutoAdvance() {
    stopAutoAdvance();
    if (heroes.length > 1) {
      intervalId = setInterval(() => {
        currentIndex = (currentIndex + 1) % heroes.length;
      }, 5000);
    }
  }

  function stopAutoAdvance() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  onMount(async () => {
    try {
      const response = await featuredAPI.getHero({ placement });
      if (response.data && response.data.length > 0) {
        heroes = response.data;
        startAutoAdvance();
      }
    } catch (err) {
      // API failed, heroes stays empty
    } finally {
      loading = false;
    }
  });

  onDestroy(() => {
    stopAutoAdvance();
  });

  let projectLink = $derived(resolvePortalLink(hero?.link || hero?.url));
</script>

{#if showDashboardFallback}
  <!-- Dashboard fallback banner -->
  <div
    class="relative overflow-hidden rounded-[8px] p-4 pt-10 md:p-5 flex items-start md:items-end h-[480px] md:h-[300px]"
    style="background: {fallbackGradient};"
  >
    <div class="absolute inset-0 opacity-25" style="background-image: linear-gradient(rgba(255,255,255,0.22) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.18) 1px, transparent 1px); background-size: 44px 44px;"></div>
    <div class="absolute inset-0" style="background: linear-gradient(to right, rgba(0,0,0,0.18), rgba(0,0,0,0.04));"></div>

    <!-- Card overlay — frosted glass -->
    <div
      class="relative z-10 rounded-[24px] p-4 flex flex-col gap-4 w-full md:w-[386px] backdrop-blur-[10px]"
      style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.25); box-shadow: inset 0 1px 1px rgba(255,255,255,0.15), 0 0 20px rgba(255,255,255,0.05);"
    >
      <div class="flex flex-col">
        <div class="flex items-center gap-1 h-4">
          <span class="text-white/70 text-xs font-medium leading-none">{fallbackEyebrow}</span>
          <img src="/assets/icons/verified-badge-fill.svg" alt="Verified" class="w-4 h-4 flex-shrink-0">
        </div>
        <h2 class="font-display text-[32px] font-medium text-white leading-[38px] line-clamp-1 h-[38px] overflow-hidden">
          {fallbackTitle}
        </h2>
        <p class="text-white/80 text-sm line-clamp-3 h-[60px] overflow-hidden" style="letter-spacing: 0.28px;">
          {fallbackDescription}
        </p>
      </div>

      <div class="h-10">
        <button
          onclick={() => push(fallbackActionPath)}
          class="inline-flex h-10 px-4 bg-white rounded-[20px] items-center gap-2 hover:bg-white/90 transition-colors"
        >
          <span class="text-black text-sm font-medium" style="letter-spacing: 0.28px;">{fallbackActionLabel}</span>
          <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
        </button>
      </div>
    </div>
  </div>
{:else if loading}
  <!-- Loading skeleton -->
  <div class="relative overflow-hidden rounded-[8px] p-4 pt-10 md:p-5 flex items-start md:items-end animate-pulse h-[480px] md:h-[300px]" style="background: {loadingGradient};">
    <div class="relative z-10 rounded-[24px] p-4 flex flex-col gap-4 w-full md:w-[386px] backdrop-blur-[10px]" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.25); box-shadow: inset 0 1px 1px rgba(255,255,255,0.15), 0 0 20px rgba(255,255,255,0.05);">
      <div class="flex flex-col gap-2">
        <div class="h-3 w-24 bg-white/20 rounded"></div>
        <div class="h-8 w-48 bg-white/20 rounded"></div>
        <div class="h-4 w-64 bg-white/20 rounded"></div>
      </div>
      <div class="h-10 w-32 bg-white/20 rounded-[20px]"></div>
    </div>
  </div>
{:else if hero}
  <div
    role="region"
    aria-label="Featured announcement"
    class="relative overflow-hidden rounded-[8px] p-4 pt-10 md:p-5 flex items-start md:items-end h-[480px] md:h-[300px]"
    style="background: linear-gradient(to right, #8d81e1, #eae9f3);"
    onmouseenter={stopAutoAdvance}
    onmouseleave={startAutoAdvance}
  >
    <!-- Background images — crossfade via stacked layers, responsive per breakpoint -->
    {#each heroes as h, i}
      <div
        class="absolute inset-0 transition-opacity duration-700 ease-in-out"
        style="opacity: {i === currentIndex ? 1 : 0};"
      >
        <picture>
          <source media="(min-width: 1024px)" srcset={h.hero_image_url || '/assets/hero-bg.png'}>
          <source media="(min-width: 768px)" srcset={h.hero_image_url_tablet || h.hero_image_url || '/assets/hero-bg.png'}>
          <img src={h.hero_image_url_mobile || h.hero_image_url || '/assets/hero-bg.png'} alt="" class="w-full h-full object-cover">
        </picture>
        <div class="absolute inset-0" style="background: linear-gradient(to right, rgba(0,0,0,0.2), transparent);"></div>
      </div>
    {/each}

    <!-- Card overlay — frosted glass matching Figma -->
    <div class="relative z-10 rounded-[24px] p-4 flex flex-col gap-4 w-full md:w-[386px] backdrop-blur-[10px]" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.25); box-shadow: inset 0 1px 1px rgba(255,255,255,0.15), 0 0 20px rgba(255,255,255,0.05);">
      <div class="flex flex-col">
        {#if hero.author || hero.user_name}
          <div class="flex items-center gap-1 h-4">
            <span class="text-white/60 text-xs font-medium leading-none" style="letter-spacing: 0.24px;">By {hero.author || hero.user_name}</span>
            <img src="/assets/icons/verified-badge-fill.svg" alt="Verified" class="w-4 h-4 flex-shrink-0">
          </div>
        {/if}
        <h2 class="font-display text-[32px] font-medium text-white leading-[38px] line-clamp-1 h-[38px] overflow-hidden" style="letter-spacing: -1.28px;">
          {hero.title}
        </h2>
        <p class="text-white/80 text-sm max-w-[280px] line-clamp-2 h-[40px] overflow-hidden" style="letter-spacing: 0.28px;">
          {hero.description}
        </p>
      </div>

      <div class={showNewsLink ? 'min-h-10' : 'h-10'}>
        {#if hero.link || hero.url}
          {#if showNewsLink}
            <div class="flex flex-wrap items-center gap-2">
              <a href={projectLink.href} target={projectLink.external ? '_blank' : undefined} rel={projectLink.external ? 'noopener noreferrer' : undefined} class="inline-flex h-10 px-4 bg-white rounded-[20px] items-center gap-2 hover:bg-white/90 transition-colors">
                <span class="text-black text-sm font-medium" style="letter-spacing: 0.28px;">View project</span>
                <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
              </a>
              <a
                href="#/gen-news"
                class="inline-flex h-10 items-center gap-1 rounded-[20px] border border-white/25 bg-white/10 px-4 text-sm font-medium text-white backdrop-blur-[10px] transition-colors hover:bg-white/20"
                style="letter-spacing: 0.28px;"
              >
                See all
                <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4 brightness-0 invert">
              </a>
            </div>
          {:else}
            <a href={projectLink.href} target={projectLink.external ? '_blank' : undefined} rel={projectLink.external ? 'noopener noreferrer' : undefined} class="inline-flex h-10 px-4 bg-white rounded-[20px] items-center gap-2 hover:bg-white/90 transition-colors">
              <span class="text-black text-sm font-medium" style="letter-spacing: 0.28px;">View project</span>
              <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
            </a>
          {/if}
        {:else if showNewsLink}
          <a
            href="#/gen-news"
            class="inline-flex h-10 items-center gap-2 rounded-[20px] bg-white px-4 text-sm font-medium text-black transition-colors hover:bg-white/90"
            style="letter-spacing: 0.28px;"
          >
            See all news
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
          </a>
        {/if}
      </div>
    </div>

    {#if heroes.length > 1}
      <div class="absolute bottom-4 right-4 z-20 flex items-center gap-1.5 rounded-full px-2 py-1.5 backdrop-blur-sm" style="background: rgba(0,0,0,0.25);">
        {#each heroes as _, i}
          <button
            onclick={() => { currentIndex = i; startAutoAdvance(); }}
            class="h-1.5 rounded-full transition-all duration-400 ease-out {i === currentIndex ? 'w-5 bg-white' : 'w-1.5 bg-white/40 hover:bg-white/70'}"
            aria-label="Go to slide {i + 1}"
          ></button>
        {/each}
      </div>
    {/if}
  </div>
{/if}
