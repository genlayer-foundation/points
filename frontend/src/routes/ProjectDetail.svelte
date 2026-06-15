<script>
  // @ts-nocheck
  import { push } from 'svelte-spa-router';
  import { projectsAPI } from '../lib/api.js';
  import { setPageMeta } from '../lib/meta.js';
  import ProjectPageRenderer from '../components/projects/ProjectPageRenderer.svelte';

  /** @type {{ params?: { slug?: string } }} */
  let { params = {} } = $props();

  /** @type {any} */
  let project = $state(null);
  let loading = $state(true);
  /** @type {string | null} */
  let error = $state(null);
  let lastRequestedSlug = '';

  $effect(() => {
    const slug = params.slug;
    if (slug && slug !== lastRequestedSlug) {
      lastRequestedSlug = slug;
      fetchProject(slug);
    }
  });

  $effect(() => {
    if (!project) return;

    setPageMeta({
      title: `${project.title} | GenLayer Builder Project`,
      description: getProjectMetaDescription(),
      image: getProjectMetaImage(),
      path: `/builders/projects/${project.slug || params.slug}`,
    });
  });

  /** @param {string} slug */
  async function fetchProject(slug) {
    try {
      loading = true;
      error = null;
      const response = await projectsAPI.get(slug);
      project = response.data;
    } catch (err) {
      const requestError = /** @type {{ response?: { data?: { detail?: string } }, message?: string }} */ (err);
      error = requestError.response?.data?.detail || requestError.message || 'Failed to load project';
    } finally {
      loading = false;
    }
  }

  function getAuthorName() {
    return project?.author || project?.user_name || 'GenLayer builder';
  }

  function getInitials() {
    const source = getAuthorName();
    return source ? source[0].toUpperCase() : 'P';
  }

  function getProjectLogoUrl() {
    return project?.user_profile_image_url || project?.featured_profile_image_url || '';
  }

  function truncateMetaDescription(value) {
    const text = String(value || '').replace(/\s+/g, ' ').trim();
    if (!text) return '';
    return text.length > 155 ? `${text.slice(0, 152).trim()}...` : text;
  }

  function getProjectMetaDescription() {
    return truncateMetaDescription(
      project?.description ||
        project?.summary ||
        `${project?.title || 'This GenLayer builder project'} is built by ${getAuthorName()} for the GenLayer ecosystem.`
    );
  }

  function getProjectMetaImage() {
    return (
      project?.hero_image_url ||
      project?.hero_image_url_tablet ||
      project?.hero_image_url_mobile ||
      project?.featured_profile_image_url ||
      project?.user_profile_image_url ||
      undefined
    );
  }

  function getHeroContentClass() {
    return 'absolute inset-0 grid gap-6 p-5 sm:p-7 md:p-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end';
  }

  function getPageLinks() {
    const links = [];
    const seen = new Set();

    function add(label, url) {
      if (!url) return;
      const key = `${label}:${url}`.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      links.push({ label, url, type: getLinkType(label, url) });
    }

    add('Website', project?.url);
    add('X', project?.x_url || project?.twitter_url);
    add('Telegram', project?.telegram_url);
    add('Discord', project?.discord_url);
    add('GitHub', project?.github_url);
    return links;
  }

  function parseProjectUrl(rawUrl) {
    if (!rawUrl) return null;
    try {
      return new URL(rawUrl);
    } catch {
      try {
        return new URL(`https://${rawUrl}`);
      } catch {
        return null;
      }
    }
  }

  function getLinkType(label, url) {
    const value = `${label || ''} ${url || ''}`.toLowerCase();
    if (value.includes('github.com') || value.includes('github')) return 'github';
    if (value.includes('x.com') || value.includes('twitter.com') || value.includes('twitter') || value.includes(' x')) return 'x';
    if (value.includes('t.me') || value.includes('telegram')) return 'telegram';
    if (value.includes('discord')) return 'discord';
    return 'website';
  }

  function getDisplayUrl(link) {
    const rawUrl = link?.url || '';
    if (!rawUrl) return '';

    const url = parseProjectUrl(rawUrl);
    if (url) {
      const host = url.hostname.replace(/^www\./, '');
      const pathParts = url.pathname.split('/').filter(Boolean);

      if (link.type === 'x' || host === 'twitter.com' || host === 'x.com') {
        const handle = pathParts[0] || '';
        return handle && !['i', 'intent', 'share'].includes(handle.toLowerCase()) ? `@${handle}` : host;
      }

      if (link.type === 'telegram' || host === 't.me' || host === 'telegram.me') {
        return pathParts[0] ? `@${pathParts[0]}` : host;
      }

      if (link.type === 'discord') {
        if (host === 'discord.gg') return pathParts[0] || host;
        if (host.includes('discord.com') && pathParts[0] === 'invite') return pathParts[1] || host;
        if (host.includes('discord.com') && pathParts[0] === 'channels') return pathParts[1] || host;
        return pathParts[0] || host;
      }

      if (link.type === 'github') {
        return pathParts[0] || host;
      }

      return host;
    }

    return rawUrl.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');
  }

  function getLinkLabel(link) {
    return {
      website: 'Website',
      x: 'X',
      telegram: 'Telegram',
      discord: 'Discord',
      github: 'GitHub',
    }[link.type] || link.label || 'Link';
  }

  function getHeroClass() {
    return 'relative min-h-[360px] bg-[#111827] sm:min-h-[340px] lg:min-h-[320px]';
  }
</script>

{#snippet linkIcon(type)}
  {#if type === 'github'}
    <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-current">
      <path d="M12 2C6.48 2 2 6.58 2 12.25c0 4.52 2.86 8.35 6.84 9.71.5.09.68-.22.68-.49 0-.24-.01-1.05-.01-1.9-2.51.47-3.16-.63-3.36-1.21-.11-.3-.6-1.21-1.03-1.45-.35-.19-.85-.66-.01-.67.79-.01 1.35.74 1.54 1.05.9 1.55 2.34 1.11 2.91.85.09-.67.35-1.11.64-1.37-2.22-.26-4.55-1.14-4.55-5.05 0-1.11.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.71 0 0 .84-.28 2.75 1.05A9.3 9.3 0 0 1 12 7.01c.85 0 1.71.12 2.51.34 1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.45.1 2.71.64.72 1.03 1.63 1.03 2.75 0 3.92-2.34 4.78-4.57 5.05.36.32.68.94.68 1.9 0 1.37-.01 2.47-.01 2.8 0 .27.18.59.69.49A10.08 10.08 0 0 0 22 12.25C22 6.58 17.52 2 12 2z" />
    </svg>
  {:else if type === 'x'}
    <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-current">
      <path d="M18.9 2.8h3.15l-6.88 7.86 8.09 10.7h-6.33l-4.96-6.48-5.67 6.48H3.13l7.36-8.41L2.74 2.8h6.49l4.48 5.92 5.19-5.92zm-1.1 16.67h1.74L8.28 4.59H6.41l11.39 14.88z" />
    </svg>
  {:else if type === 'telegram'}
    <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-current">
      <path d="M21.74 4.42c.29-1.22-.85-1.72-1.72-1.38L2.77 9.7c-1.18.46-1.16 1.12-.2 1.42l4.43 1.38 10.27-6.48c.49-.3.93-.14.57.18l-8.32 7.51-.32 4.75c.47 0 .68-.22.94-.48l2.26-2.2 4.7 3.47c.87.48 1.49.23 1.7-.8l2.94-14.03z" />
    </svg>
  {:else if type === 'discord'}
    <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-current">
      <path d="M19.54 5.34A18.46 18.46 0 0 0 14.96 4l-.22.44c1.62.39 2.37.95 2.37.95a12.57 12.57 0 0 0-10.22 0s.75-.56 2.37-.95L9.04 4c-1.6.27-3.15.72-4.58 1.34C1.56 9.7.78 13.95 1.17 18.14A18.4 18.4 0 0 0 6.78 21s.68-.82 1.23-1.52a7.98 7.98 0 0 1-1.94-.93l.46-.35c3.74 1.73 7.79 1.73 11.48 0l.46.35c-.61.4-1.26.71-1.95.93.55.7 1.22 1.52 1.22 1.52a18.34 18.34 0 0 0 5.62-2.86c.46-4.86-.78-9.08-3.82-12.8zM8.63 15.55c-1.1 0-2.01-1.01-2.01-2.25s.89-2.25 2.01-2.25c1.13 0 2.03 1.02 2.01 2.25 0 1.24-.89 2.25-2.01 2.25zm6.74 0c-1.1 0-2.01-1.01-2.01-2.25s.89-2.25 2.01-2.25c1.13 0 2.03 1.02 2.01 2.25 0 1.24-.89 2.25-2.01 2.25z" />
    </svg>
  {:else}
    <svg aria-hidden="true" viewBox="0 0 24 24" class="h-4 w-4 fill-none stroke-current stroke-[2]">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.25 2.4 3.38 5.4 3.38 9S14.25 18.6 12 21M12 3C9.75 5.4 8.62 8.4 8.62 12S9.75 18.6 12 21" />
    </svg>
  {/if}
{/snippet}

<div class="relative -mx-3 -my-3 min-h-full overflow-hidden bg-[#f6f7f9] px-3 py-6 sm:px-5 sm:py-8 md:px-8">
  <div
    class="absolute inset-x-0 top-0 h-[420px] pointer-events-none overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_20%_8%,rgba(238,133,33,0.46),transparent_32%),radial-gradient(circle_at_78%_4%,rgba(245,153,61,0.24),transparent_28%),linear-gradient(180deg,#fff1df_0%,rgba(255,248,239,0.78)_48%,rgba(246,247,249,0)_100%)]"></div>
  </div>

  <div class="relative mx-auto max-w-[1320px]">
    {#if loading}
      <div class="space-y-5">
        <div class="h-[320px] animate-pulse rounded-[10px] border border-[#eceff4] bg-white"></div>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {#each [1, 2, 3, 4] as _}
            <div class="h-[118px] animate-pulse rounded-[8px] border border-[#eceff4] bg-white"></div>
          {/each}
        </div>
        <div class="h-[220px] animate-pulse rounded-[10px] border border-[#eceff4] bg-white"></div>
      </div>
    {:else if error}
      <div class="rounded-[10px] border border-rose-200 bg-rose-50 p-6 text-rose-700">
        <p class="text-sm font-semibold">Project unavailable</p>
        <p class="mt-1 text-sm">{error}</p>
        <button
          type="button"
          onclick={() => push('/builders')}
          class="mt-4 rounded-[6px] bg-rose-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-800"
        >
          Back to builders
        </button>
      </div>
    {:else if project}
      <div class="space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onclick={() => window.history.length > 1 ? window.history.back() : push('/builders')}
            class="inline-flex min-h-11 items-center gap-2 text-[13px] font-semibold text-[#667085] transition hover:text-black"
          >
            <img src="/assets/icons/arrow-left-s-line.svg" alt="" class="h-4 w-4" />
            Back
          </button>

          {#if project.can_edit}
            <button
              type="button"
              onclick={() => push(`/builders/projects/${project.slug}/edit`)}
              class="inline-flex h-9 items-center rounded-[7px] border border-[#dfe3eb] bg-white px-3 text-[13px] font-semibold text-black shadow-sm transition hover:border-[#f1bd82]"
            >
              Edit project page
            </button>
          {/if}
        </div>

        <section class="overflow-hidden rounded-[10px] border border-white/70 bg-white shadow-[0_22px_70px_rgba(38,48,75,0.18)]">
          <div class={getHeroClass()}>
            {#if project.hero_image_url}
              <picture>
                {#if project.hero_image_url_mobile}
                  <source media="(max-width: 767px)" srcset={project.hero_image_url_mobile} />
                {/if}
                {#if project.hero_image_url_tablet}
                  <source media="(max-width: 1023px)" srcset={project.hero_image_url_tablet} />
                {/if}
                <img src={project.hero_image_url} alt="" class="absolute inset-0 h-full w-full object-cover" />
              </picture>
            {:else}
              <div class="absolute inset-0 bg-gradient-to-br from-[#151515] via-[#2f2f2f] to-[#0d0d0d]"></div>
            {/if}
            <div class="absolute inset-0 bg-[linear-gradient(90deg,rgba(8,10,14,0.82)_0%,rgba(8,10,14,0.56)_34%,rgba(8,10,14,0.18)_68%,rgba(8,10,14,0.08)_100%)]"></div>
            <div class="absolute inset-0 bg-[linear-gradient(0deg,rgba(0,0,0,0.78)_0%,rgba(0,0,0,0.34)_34%,rgba(0,0,0,0.08)_68%,rgba(0,0,0,0.02)_100%)]"></div>
            <div class="absolute inset-y-0 left-0 w-[58%] bg-[radial-gradient(circle_at_20%_72%,rgba(0,0,0,0.64),transparent_44%)]"></div>

            <div class={getHeroContentClass()}>
              <div class="max-w-[780px] self-end">
                <div class="flex max-w-full items-center gap-4">
                  <div class="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/45 bg-black/42 p-1 text-[20px] font-semibold text-white shadow-[0_18px_44px_rgba(0,0,0,0.34)] backdrop-blur-xl sm:h-20 sm:w-20">
                    {#if getProjectLogoUrl()}
                      <img src={getProjectLogoUrl()} alt="" class="h-full w-full rounded-full object-cover" />
                    {:else}
                      {getInitials()}
                    {/if}
                  </div>
                  <h1 class="min-w-0 break-words font-display text-[44px] font-semibold leading-none text-white [text-shadow:0_3px_24px_rgba(0,0,0,0.82)] sm:text-[64px]">
                    {project.title}
                  </h1>
                </div>
                {#if project.description}
                  <p
                    class="mt-3 max-w-[720px] text-[15px] font-medium leading-6 sm:text-[16px]"
                    style="color: #f8fafc; text-shadow: 0 2px 16px rgba(0, 0, 0, 0.96), 0 1px 2px rgba(0, 0, 0, 0.82);"
                  >
                    {project.description}
                  </p>
                {/if}

                {#if getPageLinks().length}
                  <div class="mt-5 flex flex-wrap gap-2">
                    {#each getPageLinks() as link}
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="group relative inline-flex h-11 max-w-full items-center gap-2.5 overflow-hidden rounded-full border border-white/35 bg-black/48 px-4 text-white shadow-[0_22px_54px_rgba(0,0,0,0.36)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-white/55 hover:bg-black/56"
                      aria-label={`${getLinkLabel(link)}: ${getDisplayUrl(link)}`}
                    >
                      <span class="pointer-events-none absolute inset-0 bg-[linear-gradient(145deg,rgba(255,255,255,0.22),rgba(255,255,255,0.05)_42%,rgba(0,0,0,0.24)_100%)]"></span>
                      <span class="pointer-events-none absolute inset-x-0 top-0 h-px bg-white/72"></span>
                      <span class="pointer-events-none absolute -right-8 -top-10 h-20 w-20 rounded-full bg-[#ee8521]/18 blur-2xl transition group-hover:bg-[#ee8521]/26"></span>
                      <span class="relative shrink-0 text-white/92 [filter:drop-shadow(0_1px_8px_rgba(0,0,0,0.52))]">{@render linkIcon(link.type)}</span>
                      <span class="relative min-w-0 max-w-[210px] truncate text-[14px] font-semibold leading-5 text-white [text-shadow:0_1px_8px_rgba(0,0,0,0.52)]">
                        {getDisplayUrl(link)}
                      </span>
                    </a>
                    {/each}
                  </div>
                {/if}
              </div>

              <div class="hidden lg:block"></div>
            </div>
          </div>
        </section>

        <ProjectPageRenderer {project} />
      </div>
    {/if}
  </div>
</div>
