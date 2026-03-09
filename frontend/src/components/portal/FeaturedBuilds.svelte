<script>
  import { onMount } from 'svelte';
  import { featuredAPI } from '../../lib/api.js';

  let builds = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      const response = await featuredAPI.getBuilds();
      if (response.data && response.data.length > 0) {
        builds = response.data;
      }
    } catch (err) {
      // API failed, builds stays empty
    } finally {
      loading = false;
    }
  });
</script>

{#if loading || builds.length > 0}
<div>
  <div class="flex items-end justify-between mb-3">
    <div class="flex flex-col gap-1">
      <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Featured Builds</h2>
      <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">This month curated builds</p>
    </div>
    <div class="flex items-center gap-1">
      <span class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">Explore all </span>
      <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4">
    </div>
  </div>

  {#if loading}
    <div class="flex gap-[10px] overflow-x-auto pb-2">
      {#each [1, 2, 3] as _}
        <div class="flex-shrink-0 w-[300px] h-[150px] rounded-[8px] bg-[#f8f8f8] animate-pulse"></div>
      {/each}
    </div>
  {:else}
    <div class="flex gap-[10px] overflow-x-auto pb-2" style="-ms-overflow-style: none; scrollbar-width: none;">
      {#each builds as build}
        <a
          href={build.link || build.url || '#'}
          target={build.url?.startsWith('http') ? '_blank' : undefined}
          rel={build.url?.startsWith('http') ? 'noopener noreferrer' : undefined}
          class="flex-shrink-0 w-[300px] h-[150px] rounded-[8px] overflow-hidden relative group cursor-pointer bg-[#f8f8f8]"
        >
          <!-- Background image -->
          {#if build.hero_image_url}
            <img src={build.hero_image_url} alt="" class="absolute inset-0 w-full h-full object-cover">
          {:else}
            <div class="absolute inset-0 bg-gradient-to-br from-gray-700 to-gray-900"></div>
          {/if}

          <!-- Dark gradient overlay matching Figma: from rgba(0,0,0,0.2) to rgba(0,0,0,0.5) -->
          <div class="absolute inset-0 bg-gradient-to-b from-[rgba(0,0,0,0.2)] to-[rgba(0,0,0,0.5)]"></div>

          <!-- Top-right arrow icon — always visible, frosted glass pill -->
          <div class="absolute top-0 right-0 p-4 flex flex-col items-start h-full">
            <div class="flex items-center p-2 rounded-[4px] backdrop-blur-[10px]" style="background: rgba(255,255,255,0.1);">
              <img src="/assets/featured-builds/arrow-right-up-line.svg" alt="" class="w-4 h-4">
            </div>
          </div>

          <!-- Bottom content -->
          <div class="absolute bottom-0 left-0 right-0 p-4 flex items-end justify-between">
            <div class="flex items-center gap-1">
              <!-- Avatar -->
              {#if build.user_profile_image_url}
                <img src={build.user_profile_image_url} alt="" class="w-10 h-10 rounded-full flex-shrink-0">
              {:else}
                <div class="w-10 h-10 rounded-full flex-shrink-0 bg-white/20 flex items-center justify-center text-white text-sm font-medium">
                  {(build.user_name || '?')[0].toUpperCase()}
                </div>
              {/if}
              <div class="flex flex-col justify-center ml-0.5">
                <span class="text-white text-[14px] font-medium leading-[21px]">{build.title}</span>
                <span class="text-[#bbb] text-[12px] leading-[15px]" style="letter-spacing: 0.24px;">by {build.user_name || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>
{/if}
