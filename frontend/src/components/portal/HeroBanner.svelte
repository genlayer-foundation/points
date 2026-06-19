<script>
  import { onMount, onDestroy } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { featuredAPI } from '../../lib/api.js';
  import { resolvePortalLink } from '../../lib/links.js';

  let { category = 'builder', showNewsLink = false, compact = false, socialStats = null } = $props();

  let heightClass = $derived(compact ? 'h-[420px] md:h-[240px]' : 'h-[480px] md:h-[300px]');

  // White brand marks (simple-icons) for the discreet social cluster.
  const BRAND = {
    x: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"/></svg>',
    telegram: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>',
    discord: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.317 4.3698a19.7913 19.7913 0 0 0-4.8851-1.5152.0741.0741 0 0 0-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 0 0-.0785-.037 19.7363 19.7363 0 0 0-4.8852 1.515.0699.0699 0 0 0-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 0 0 .0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 0 0 .0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 0 0-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 0 1-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 0 1 .0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 0 1 .0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 0 1-.0066.1276 12.2986 12.2986 0 0 1-1.873.8914.0766.0766 0 0 0-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 0 0 .0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 0 0 .0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 0 0-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg>',
  };

  function formatCount(n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return null;
    if (x >= 1000000) return `${(x / 1000000).toFixed(1)}M`;
    if (x >= 1000) return `${(x / 1000).toFixed(1)}K`;
    return x.toLocaleString();
  }

  let socialItems = $derived(
    socialStats
      ? [
          { key: 'x', unit: 'followers', href: 'https://x.com/GenLayer', value: formatCount(socialStats.x), icon: BRAND.x },
          { key: 'telegram', unit: 'members', href: 'https://t.me/genlayer', value: formatCount(socialStats.telegram), icon: BRAND.telegram },
          { key: 'discord', unit: 'members', href: 'https://discord.gg/genlayerlabs', value: formatCount(socialStats.discord), icon: BRAND.discord },
        ].filter((s) => s.value != null)
      : []
  );

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
    class="relative overflow-hidden rounded-[8px] p-4 pt-10 md:p-5 flex items-start md:items-end {heightClass}"
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
  <div class="relative overflow-hidden rounded-[8px] p-4 pt-10 md:p-5 flex items-start md:items-end animate-pulse {heightClass}" style="background: {loadingGradient};">
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
    class="relative overflow-hidden rounded-[8px] p-4 pt-10 md:p-5 flex items-start md:items-end {heightClass}"
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
          <a href={projectLink.href} target={projectLink.external ? '_blank' : undefined} rel={projectLink.external ? 'noopener noreferrer' : undefined} class="inline-flex h-10 px-4 bg-white rounded-[20px] items-center gap-2 hover:bg-white/90 transition-colors">
            <span class="text-black text-sm font-medium" style="letter-spacing: 0.28px;">View</span>
            <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
          </a>
        {/if}
      </div>
    </div>

    {#if socialItems.length}
      <div class="absolute top-3 right-3 md:top-4 md:right-4 z-20 hidden sm:flex items-center gap-2.5">
        {#each socialItems as s}
          <a
            href={s.href}
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center gap-2 rounded-full border border-white/15 bg-black/35 px-3.5 py-2 backdrop-blur-[10px] transition-colors hover:bg-black/55 hover:border-white/25"
            aria-label={`${s.value} ${s.unit}`}
          >
            <span class="social-ico">{@html s.icon}</span>
            <span class="leading-none">
              <span class="text-white text-[15px] font-semibold tabular-nums">{s.value}</span>
              <span class="text-white/70 text-[13px] ml-1">{s.unit}</span>
            </span>
          </a>
        {/each}
      </div>
    {/if}

    {#if heroes.length > 1 || showNewsLink}
      <div class="absolute bottom-4 right-4 z-20 flex items-center gap-3">
        {#if heroes.length > 1}
          <div class="flex items-center gap-1.5 rounded-full px-2 py-1.5 backdrop-blur-sm" style="background: rgba(0,0,0,0.25);">
            {#each heroes as _, i}
              <button
                onclick={() => { currentIndex = i; startAutoAdvance(); }}
                class="h-1.5 rounded-full transition-all duration-400 ease-out {i === currentIndex ? 'w-5 bg-white' : 'w-1.5 bg-white/40 hover:bg-white/70'}"
                aria-label="Go to slide {i + 1}"
              ></button>
            {/each}
          </div>
        {/if}
        {#if showNewsLink}
          <a
            href="/gen-news"
            class="inline-flex items-center text-sm font-medium text-white/90 underline-offset-4 transition-colors hover:text-white hover:underline"
            style="letter-spacing: 0.28px; text-shadow: 0 1px 3px rgba(0,0,0,0.45);"
          >
            See all
          </a>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .social-ico {
    align-items: center;
    color: #fff;
    display: flex;
  }

  .social-ico :global(svg) {
    display: block;
    height: 16px;
    width: 16px;
  }
</style>
