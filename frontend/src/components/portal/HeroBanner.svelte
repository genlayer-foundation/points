<script>
  import { onMount } from 'svelte';
  import { featuredAPI } from '../../lib/api.js';

  let hero = $state(null);
  let loading = $state(true);
  let error = $state(null);

  // Static fallback values matching the original design
  const fallback = {
    title: 'Argue.fun Launch',
    subtitle: 'cognocracy',
    description: 'Deploy intelligent contracts, run validators, and earn GenLayer Points on the latest testnet.',
    hero_image_url: null,
    link: '#',
  };

  onMount(async () => {
    try {
      const response = await featuredAPI.getHero();
      if (response.data && response.data.length > 0) {
        hero = response.data[0];
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  });

  let displayData = $derived(hero || fallback);
  let bgImage = $derived(displayData.hero_image_url || '/assets/hero-bg.png');
  let projectLink = $derived(displayData.link || displayData.url || '#');
</script>

{#if loading}
  <!-- Loading skeleton -->
  <div class="relative overflow-hidden rounded-[8px] p-5 flex items-end animate-pulse" style="min-height: 300px; background: linear-gradient(to right, #c4bfe8, #eae9f3);">
    <div class="relative z-10 rounded-[24px] p-4 flex flex-col gap-4 w-full md:w-[386px] backdrop-blur-[10px]" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.25); box-shadow: inset 0 1px 1px rgba(255,255,255,0.15), 0 0 20px rgba(255,255,255,0.05);">
      <div class="flex flex-col gap-2">
        <div class="h-3 w-24 bg-white/20 rounded"></div>
        <div class="h-8 w-48 bg-white/20 rounded"></div>
        <div class="h-4 w-64 bg-white/20 rounded"></div>
      </div>
      <div class="h-10 w-32 bg-white/20 rounded-[20px]"></div>
    </div>
  </div>
{:else}
  <div class="relative overflow-hidden rounded-[8px] p-5 flex items-end" style="min-height: 300px; background: linear-gradient(to right, #8d81e1, #eae9f3);">
    <!-- Background image -->
    <div class="absolute inset-0">
      <img src={bgImage} alt="" class="w-full h-full object-cover">
      <div class="absolute inset-0" style="background: linear-gradient(to right, rgba(0,0,0,0.2), transparent);"></div>
    </div>

    <!-- Card overlay — frosted glass matching Figma -->
    <div class="relative z-10 rounded-[24px] p-4 flex flex-col gap-4 w-full md:w-[386px] backdrop-blur-[10px]" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.25); box-shadow: inset 0 1px 1px rgba(255,255,255,0.15), 0 0 20px rgba(255,255,255,0.05);">
      <div class="flex flex-col">
        <div class="flex items-center gap-1">
          <span class="text-white/60 text-xs font-medium leading-none" style="letter-spacing: 0.24px;">By {displayData.subtitle || displayData.user_name || 'Unknown'}</span>
          <img src="/assets/icons/verified-badge-fill.svg" alt="Verified" class="w-4 h-4 flex-shrink-0">
        </div>
        <h2 class="font-display text-[32px] font-medium text-white leading-[38px]" style="letter-spacing: -1.28px;">
          {displayData.title}
        </h2>
        <p class="text-white/80 text-sm max-w-[280px]" style="letter-spacing: 0.28px;">
          {displayData.description}
        </p>
      </div>

      <div>
        <a href={projectLink} target={projectLink.startsWith('http') ? '_blank' : undefined} rel={projectLink.startsWith('http') ? 'noopener noreferrer' : undefined} class="inline-flex h-10 px-4 bg-white rounded-[20px] items-center gap-2 hover:bg-white/90 transition-colors">
          <span class="text-black text-sm font-medium" style="letter-spacing: 0.28px;">View project</span>
          <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
        </a>
      </div>
    </div>
  </div>
{/if}
