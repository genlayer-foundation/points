<script>
  import { onMount } from 'svelte';
  import { projectsAPI } from '../../lib/api.js';
  import { resolvePortalLink } from '../../lib/links.js';

  let {
    title = 'Featured Builds',
    subtitle = 'This month curated builds',
    overviewOnly = false,
    limit = undefined,
    variant = 'horizontal',
  } = $props();

  let builds = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      const params = {
        ...(overviewOnly ? { show_in_overview: true } : {}),
        ...(limit ? { limit } : {}),
      };
      const response = await projectsAPI.list(params);
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
<div class="max-w-full min-w-0">
  <div class="flex items-end justify-between mb-3 gap-4">
    <div class="flex flex-col gap-1">
      <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">{title}</h2>
      {#if subtitle}
        <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">{subtitle}</p>
      {/if}
    </div>
    <a
      href="/ecosystem-partners?tab=project"
      class="flex-shrink-0 text-[13px] font-medium text-[#6b6b6b] hover:text-black transition-colors inline-flex items-center gap-1"
    >
      View all
      <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="w-4 h-4" />
    </a>
  </div>

  {#if loading}
    <div class={variant === 'vertical' ? 'vertical-project-grid' : 'flex max-w-full min-w-0 gap-[10px] overflow-x-auto pb-2'} aria-busy="true">
      {#each [1, 2, 3, 4, 5] as _}
        <div class={variant === 'vertical' ? 'vertical-project-skeleton project-skeleton' : 'horizontal-project-skeleton project-skeleton'} aria-hidden="true">
          <div class="project-skeleton-arrow"></div>
          <div class="project-skeleton-footer">
            <div class="project-skeleton-avatar"></div>
            <div class="project-skeleton-copy">
              <div class="project-skeleton-line title"></div>
              <div class="project-skeleton-line meta"></div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div
      class={variant === 'vertical' ? 'vertical-project-grid' : 'flex max-w-full min-w-0 gap-[10px] overflow-x-auto pb-2'}
      style={variant === 'vertical' ? '' : '-ms-overflow-style: none; scrollbar-width: none;'}
    >
      {#each builds as build}
        {@const projectLink = resolvePortalLink(build.link || build.url)}
        {@const projectHref = projectLink.href}
        {@const isExternal = projectLink.external}
        <a
          href={projectHref}
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noopener noreferrer' : undefined}
          class={variant === 'vertical' ? 'vertical-project-card group' : 'flex-shrink-0 w-[300px] h-[150px] rounded-[8px] overflow-hidden relative group cursor-pointer bg-[#f8f8f8]'}
        >
          <!-- Background image -->
          {#if build.hero_image_url}
            <img src={build.hero_image_url} alt="" class="absolute inset-0 w-full h-full object-cover">
          {:else}
            <div class="absolute inset-0 bg-gradient-to-br from-gray-700 to-gray-900"></div>
          {/if}

          <div class={variant === 'vertical' ? 'vertical-project-overlay' : 'absolute inset-0 bg-gradient-to-b from-[rgba(0,0,0,0.2)] to-[rgba(0,0,0,0.5)]'}></div>

          <div class={variant === 'vertical' ? 'vertical-project-arrow' : 'absolute top-0 right-0 p-4 flex flex-col items-start h-full'}>
            <div class={variant === 'vertical' ? 'vertical-project-arrow-button' : 'flex items-center p-2 rounded-[4px] backdrop-blur-[10px]'} style={variant === 'vertical' ? '' : 'background: rgba(255,255,255,0.1);'}>
              <img src="/assets/featured-builds/arrow-right-up-line.svg" alt="" class="w-4 h-4">
            </div>
          </div>

          <div class={variant === 'vertical' ? 'vertical-project-content' : 'absolute bottom-0 left-0 right-0 p-4 flex items-end justify-between'}>
            <div class="flex items-center gap-1">
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

<style>
  .vertical-project-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .vertical-project-card,
  .vertical-project-skeleton {
    aspect-ratio: 4 / 5;
    border-radius: 8px;
    overflow: hidden;
  }

  .vertical-project-card {
    background: #101010;
    border: 1px solid #ececf0;
    cursor: pointer;
    display: block;
    position: relative;
  }

  .vertical-project-card :global(img.absolute) {
    transition: transform 260ms ease;
  }

  .vertical-project-card:hover :global(img.absolute) {
    transform: scale(1.035);
  }

  .vertical-project-overlay {
    background: linear-gradient(180deg, rgba(0, 0, 0, 0.08) 0%, rgba(0, 0, 0, 0.18) 38%, rgba(0, 0, 0, 0.76) 100%);
    inset: 0;
    position: absolute;
  }

  .vertical-project-arrow {
    padding: 12px;
    position: absolute;
    right: 0;
    top: 0;
  }

  .vertical-project-arrow-button {
    align-items: center;
    backdrop-filter: blur(10px);
    background: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 8px;
    display: flex;
    height: 34px;
    justify-content: center;
    width: 34px;
  }

  .vertical-project-content {
    bottom: 0;
    left: 0;
    padding: 16px;
    position: absolute;
    right: 0;
  }

  .vertical-project-skeleton {
    display: block;
  }

  .horizontal-project-skeleton {
    border-radius: 8px;
    flex: 0 0 300px;
    height: 150px;
    overflow: hidden;
  }

  .project-skeleton {
    background:
      linear-gradient(180deg, rgba(248, 248, 249, 0.84), rgba(232, 234, 238, 0.92)),
      linear-gradient(135deg, #f2f3f5, #fbfbfc);
    border: 1px solid #ececf0;
    position: relative;
  }

  .project-skeleton::before {
    background: linear-gradient(180deg, transparent 8%, rgba(16, 16, 16, 0.05) 48%, rgba(16, 16, 16, 0.16) 100%);
    content: '';
    inset: 0;
    position: absolute;
  }

  .project-skeleton::after {
    animation: project-card-shimmer 1.45s ease-in-out infinite;
    background: linear-gradient(105deg, transparent 22%, rgba(255, 255, 255, 0.72) 48%, transparent 72%);
    content: '';
    inset: 0;
    position: absolute;
    transform: translateX(-100%);
  }

  .project-skeleton-arrow {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.78);
    border-radius: 8px;
    height: 34px;
    position: absolute;
    right: 12px;
    top: 12px;
    width: 34px;
    z-index: 1;
  }

  .project-skeleton-footer {
    align-items: center;
    bottom: 16px;
    display: flex;
    gap: 10px;
    left: 16px;
    position: absolute;
    right: 16px;
    z-index: 1;
  }

  .project-skeleton-avatar {
    background: rgba(255, 255, 255, 0.78);
    border-radius: 999px;
    flex: 0 0 40px;
    height: 40px;
    width: 40px;
  }

  .project-skeleton-copy {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 7px;
    min-width: 0;
  }

  .project-skeleton-line {
    background: rgba(255, 255, 255, 0.78);
    border-radius: 999px;
    height: 10px;
  }

  .project-skeleton-line.title {
    width: min(150px, 82%);
  }

  .project-skeleton-line.meta {
    opacity: 0.72;
    width: min(92px, 58%);
  }

  @keyframes project-card-shimmer {
    from {
      transform: translateX(-100%);
    }
    to {
      transform: translateX(100%);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .project-skeleton::after {
      animation: none;
    }
  }

  @media (max-width: 1180px) {
    .vertical-project-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .vertical-project-grid {
      display: flex;
      overflow-x: auto;
      padding-bottom: 2px;
      scroll-snap-type: x mandatory;
      scrollbar-width: none;
    }

    .vertical-project-grid::-webkit-scrollbar {
      display: none;
    }

    .vertical-project-card,
    .vertical-project-skeleton {
      flex: 0 0 72vw;
      scroll-snap-align: start;
    }
  }
</style>
