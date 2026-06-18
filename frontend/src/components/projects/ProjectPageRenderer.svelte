<script>
  // @ts-nocheck
  import { tick } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Avatar from '../Avatar.svelte';
  import { renderProjectMarkdown } from '../../lib/projectPageTemplate.js';

  /** @type {{ project: any }} */
  let { project } = $props();
  let participantListEl = $state(null);
  let participantListOverflows = $state(false);
  let participantCanScrollUp = $state(false);
  let participantCanScrollDown = $state(false);

  function getVideoBlocks() {
    const videos = [];

    for (const url of [project?.demo_url, project?.demo_video_url, project?.video_url]) {
      if (url && !videos.some((block) => block.url === url)) {
        videos.push({ type: 'video', title: 'Demo', url });
      }
    }

    return videos;
  }

  function hasSideRail() {
    return getParticipants().length || getVideoBlocks().length;
  }

  function getSideRailClass() {
    return 'space-y-4';
  }

  function getSideRailGridClass() {
    return 'grid min-h-0 gap-4';
  }

  /** @param {string | number | Date | null | undefined} value */
  function formatDate(value) {
    if (!value) return '';
    try {
      return new Date(value).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return value;
    }
  }

  /** @param {any} contribution */
  function normalizeContribution(contribution) {
    return {
      ...contribution,
      user_details: contribution.user_details || contribution.user || {},
      contribution_type_details: contribution.contribution_type_details || contribution.contribution_type || {},
      contribution_type_name: contribution.contribution_type_name || contribution.contribution_type?.name || 'Contribution',
    };
  }

  /** @param {any} contribution */
  function getContributionTitle(contribution) {
    const normalized = normalizeContribution(contribution);
    return normalized.title || normalized.mission?.name || normalized.contribution_type_name || 'Contribution';
  }

  /** @param {any} contribution */
  function getContributionUser(contribution) {
    const user = normalizeContribution(contribution).user_details || {};
    if (user.name) return user.name;
    if (user.address) return `${user.address.slice(0, 6)}...${user.address.slice(-4)}`;
    return 'Anonymous';
  }

  /** @param {any} contribution */
  function getPoints(contribution) {
    return Number(contribution.frozen_global_points ?? contribution.points ?? 0);
  }

  function getContributionDateValue(contribution) {
    const value = contribution.contribution_date || contribution.created_at || '';
    const timestamp = value ? new Date(value).getTime() : 0;
    return Number.isFinite(timestamp) ? timestamp : 0;
  }

  function isContributionHighlighted(contribution) {
    return Boolean(contribution.is_highlighted || contribution.highlight);
  }

  function getSortedContributions() {
    return [...(project.related_contributions || [])].sort((a, b) => {
      const highlightedDelta = Number(isContributionHighlighted(b)) - Number(isContributionHighlighted(a));
      if (highlightedDelta) return highlightedDelta;
      return getContributionDateValue(b) - getContributionDateValue(a);
    });
  }

  function getParticipants() {
    const seen = new Set();
    const people = [];
    for (const user of project.participants || []) {
      const isOwner = user.id === project.user;
      const participant = {
        ...user,
        name: user.name || (isOwner ? project.user_name : ''),
        address: user.address || (isOwner ? project.user_address : ''),
        profile_image_url: isOwner && project.owner_profile_image_url ? project.owner_profile_image_url : user.profile_image_url,
      };
      const key = participant.id || participant.address || participant.name;
      if (!key || seen.has(key)) continue;
      seen.add(key);
      people.push(participant);
    }
    if (project.user || project.user_name || project.user_address) {
      const owner = {
        id: project.user,
        name: project.user_name,
        address: project.user_address,
        profile_image_url: project.owner_profile_image_url || '',
      };
      const key = owner.id || owner.address || owner.name;
      if (key && !seen.has(key)) people.unshift(owner);
    }
    return people;
  }

  $effect(() => {
    project;
    getParticipants().length;
    refreshParticipantScroll();
  });

  async function refreshParticipantScroll() {
    await tick();
    const el = participantListEl;
    if (!el) {
      participantListOverflows = false;
      participantCanScrollUp = false;
      participantCanScrollDown = false;
      return;
    }

    const maxScroll = el.scrollHeight - el.clientHeight;
    participantListOverflows = maxScroll > 1;
    participantCanScrollUp = el.scrollTop > 1;
    participantCanScrollDown = el.scrollTop < maxScroll - 1;
  }

  function scrollParticipants(direction) {
    if (!participantListEl) return;
    participantListEl.scrollBy({ top: direction * 104, behavior: 'smooth' });
    setTimeout(refreshParticipantScroll, 260);
  }

  function formatAddress(address) {
    if (!address) return 'Portal participant';
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  }

  function getParticipantName(user) {
    if (user.name) return user.name;
    if (user.address) return formatAddress(user.address);
    return 'Participant';
  }

  function parseUrl(value) {
    if (!value) return '';
    try {
      return new URL(value);
    } catch {
      try {
        return new URL(`https://${value}`);
      } catch {
        return null;
      }
    }
  }

  /** @param {string} value */
  function getDemoMedia(value) {
    const url = parseUrl(value);
    if (!url) return null;

    const host = url.hostname.replace(/^www\./, '');
    const pathParts = url.pathname.split('/').filter(Boolean);

    if (host.includes('youtube.com') || host.includes('youtu.be')) {
      let id = '';
      if (host.includes('youtu.be')) {
        id = pathParts[0] || '';
      } else {
        id = url.searchParams.get('v') || '';
        if (!id && pathParts[0] === 'embed') id = pathParts[1] || '';
        if (!id && pathParts[0] === 'shorts') id = pathParts[1] || '';
      }
      return id ? { type: 'iframe', src: `https://www.youtube.com/embed/${id}` } : null;
    }

    if (host.includes('vimeo.com')) {
      const id = pathParts.find((part) => /^\d+$/.test(part));
      return id ? { type: 'iframe', src: `https://player.vimeo.com/video/${id}` } : null;
    }

    if (host.includes('loom.com')) {
      const shareIndex = pathParts.indexOf('share');
      const id = shareIndex >= 0 ? pathParts[shareIndex + 1] : '';
      return id ? { type: 'iframe', src: `https://www.loom.com/embed/${id}` } : null;
    }

    if (/\.(mp4|webm|ogg)$/i.test(url.pathname)) {
      return { type: 'video', src: url.toString() };
    }

    return null;
  }
</script>

{#snippet sectionHeading(title, subtitle)}
  <div class="mb-4 flex items-start justify-between gap-4">
    <div class="min-w-0">
      <h2 class="text-[22px] font-semibold font-display leading-none text-black">{title || 'About'}</h2>
      {#if subtitle}
        <p class="mt-2 text-[13px] leading-5 text-[#98a2b3]">{subtitle}</p>
      {/if}
    </div>
  </div>
{/snippet}

{#snippet markdownSection(block)}
  <section class="flex max-h-[460px] min-h-0 flex-col rounded-lg border border-white/70 bg-white/82 p-4 shadow backdrop-blur-md sm:max-h-[560px] sm:p-6">
    {#if block.title}
      {@render sectionHeading(block.title, '')}
    {/if}
    {#if block.body}
      <div class="project-markdown project-about-scroll min-h-0 max-h-[382px] overflow-y-auto pr-2 text-[14px] leading-6 text-[#344054] sm:max-h-[474px]">
        {@html renderProjectMarkdown(block.body)}
      </div>
    {:else}
      <p class="text-[14px] leading-6 text-[#667085]">{block.empty || 'Content has not been added for this section yet.'}</p>
    {/if}
  </section>
{/snippet}

{#snippet videoPanel(block)}
  {@const demoMedia = getDemoMedia(block.url)}
  <section class="flex h-[210px] min-h-0 flex-col space-y-4 sm:h-[240px]">
    <div class="min-w-0">
      <h2 class="text-[22px] font-semibold font-display leading-none text-black">{block.title || 'Demo video'}</h2>
    </div>

    <div class="min-h-0 flex-1 overflow-hidden rounded-[8px] border border-[#111827] bg-black shadow-[0_12px_30px_rgba(31,42,68,0.12)]">
      <div class="h-full min-h-[156px]">
        {#if demoMedia?.type === 'iframe'}
          <iframe
            title={block.title || 'Project demo video'}
            src={demoMedia.src}
            class="h-full w-full"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
          ></iframe>
        {:else if demoMedia?.type === 'video'}
          <!-- svelte-ignore a11y_media_has_caption -->
          <video
            src={demoMedia.src}
            class="h-full w-full bg-black object-cover"
            controls
            playsinline
          ></video>
        {:else}
          <a
            href={block.url}
            target="_blank"
            rel="noopener noreferrer"
            class="flex h-full items-center justify-center gap-2 bg-[#111827] px-4 text-[14px] font-semibold text-white transition hover:bg-black"
          >
            Open demo video
            <img src="/assets/icons/arrow-right-up-line.svg" alt="" class="h-4 w-4 invert" />
          </a>
        {/if}
      </div>
    </div>
  </section>
{/snippet}

{#snippet participantsPanel()}
  <section class="flex max-h-[230px] min-h-0 flex-col rounded-lg border border-white/70 bg-white/88 p-4 shadow backdrop-blur-md sm:max-h-[300px]">
    {@render sectionHeading('Participants', 'Portal users connected to this project')}

    {#if getParticipants().length}
      <div class="relative min-h-0">
        {#if participantListOverflows}
          <button
            type="button"
            onclick={() => scrollParticipants(-1)}
            disabled={!participantCanScrollUp}
            class="absolute left-1/2 top-1 z-10 flex h-7 w-7 -translate-x-1/2 items-center justify-center rounded-full border border-white/75 bg-white/90 shadow-[0_10px_24px_rgba(31,42,68,0.14)] backdrop-blur transition hover:-translate-y-0.5 disabled:pointer-events-none disabled:opacity-35"
            aria-label="Scroll participants up"
          >
            <img src="/assets/icons/arrow-up-s-line.svg" alt="" class="h-4 w-4" />
          </button>
        {/if}

        <div
          bind:this={participantListEl}
          onscroll={refreshParticipantScroll}
          class="participant-scroll grid max-h-[132px] gap-3 overflow-y-auto pr-1 sm:max-h-[202px]"
          class:pt-8={participantListOverflows}
          class:pb-8={participantListOverflows}
        >
          {#each getParticipants() as user}
            <button
              type="button"
              onclick={() => user.address && push(`/participant/${user.address}`)}
              class="group flex min-h-[68px] w-full items-center gap-3 rounded-[8px] border border-[#edf0f5] bg-[#fbfcfe] px-3 text-left transition hover:-translate-y-0.5 hover:border-[#f1bd82] hover:bg-white hover:shadow-[0_10px_24px_rgba(31,42,68,0.08)]"
            >
              <Avatar user={user} size="lg" showBorder={true} clickable={false} />
              <div class="min-w-0">
                <p class="truncate text-[14px] font-semibold text-black">{getParticipantName(user)}</p>
                <p class="mt-0.5 truncate font-mono text-[11px] text-[#667085]">{formatAddress(user.address)}</p>
              </div>
            </button>
          {/each}
        </div>

        {#if participantListOverflows}
          <button
            type="button"
            onclick={() => scrollParticipants(1)}
            disabled={!participantCanScrollDown}
            class="absolute bottom-1 left-1/2 z-10 flex h-7 w-7 -translate-x-1/2 items-center justify-center rounded-full border border-white/75 bg-white/90 shadow-[0_10px_24px_rgba(31,42,68,0.14)] backdrop-blur transition hover:translate-y-0.5 disabled:pointer-events-none disabled:opacity-35"
            aria-label="Scroll participants down"
          >
            <img src="/assets/icons/arrow-up-s-line.svg" alt="" class="h-4 w-4 rotate-180" />
          </button>
        {/if}
      </div>
    {:else}
      <div class="rounded-[8px] border border-dashed border-[#dfe3eb] bg-[#fbfcfe] p-5 text-[13px] leading-5 text-[#667085]">
        No participants have been linked to this project yet.
      </div>
    {/if}
  </section>
{/snippet}

{#snippet relatedSubmissions(block)}
  {#if getSortedContributions().length}
    <section class="space-y-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        {@render sectionHeading(block.title || 'Related Contributions', 'Accepted contributions connected to this project')}
      </div>

      <div class="project-slider">
        {#each getSortedContributions() as contribution}
          {@const normalized = normalizeContribution(contribution)}
          <button
            type="button"
            onclick={() => push(`/contribution/${contribution.id}`)}
            class="group flex h-[156px] w-[min(300px,calc(100vw-3rem))] shrink-0 flex-col justify-between rounded-[8px] border border-white/70 bg-white/86 p-4 text-left shadow-[0_12px_30px_rgba(31,42,68,0.10)] backdrop-blur-md transition hover:-translate-y-0.5 hover:border-[#f1bd82]"
          >
            <div>
              <div class="flex items-start justify-between gap-3">
                <p class="line-clamp-2 text-[15px] font-semibold leading-5 text-black">{getContributionTitle(normalized)}</p>
                <div class="flex shrink-0 flex-col items-end gap-1">
                  {#if isContributionHighlighted(normalized)}
                    <span class="rounded-full bg-[#111827] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-white">Highlighted</span>
                  {/if}
                  <span class="rounded-full bg-[#fff2e2] px-2 py-1 text-[12px] font-semibold text-[#ee8521]">{getPoints(normalized)} pts</span>
                </div>
              </div>
              <p class="mt-2 line-clamp-2 text-[13px] leading-5 text-[#667085]">
                {normalized.highlight?.description || normalized.notes || `${normalized.contribution_type_name} contribution`}
              </p>
            </div>
            <div class="mt-3 flex items-center justify-between gap-3 text-[12px] text-[#98a2b3]">
              <span class="truncate">{getContributionUser(normalized)}</span>
              <span class="shrink-0">{formatDate(normalized.contribution_date)}</span>
            </div>
          </button>
        {/each}
      </div>
    </section>
  {/if}
{/snippet}

<div class="space-y-6">
  <div class={hasSideRail() ? 'grid items-stretch gap-5 lg:grid-cols-[minmax(0,760px)_minmax(360px,1fr)] xl:grid-cols-[minmax(0,720px)_minmax(420px,1fr)]' : 'grid items-stretch gap-5'}>
    <main class="project-main min-w-0 flex h-full flex-col gap-6">
      {@render markdownSection({
        title: 'About',
        body: project?.details || '',
        empty: 'About content has not been added for this project yet.',
      })}
    </main>

    {#if hasSideRail()}
      <aside class={`min-w-0 ${getSideRailClass()}`}>
        <div class={getSideRailGridClass()}>
          {#if getParticipants().length}
            <div class="min-h-0">
              {@render participantsPanel()}
            </div>
          {/if}

          {#each getVideoBlocks() as block}
            <div class="min-h-0">
              {@render videoPanel(block)}
            </div>
          {/each}
        </div>
      </aside>
    {/if}
  </div>

  {#if getSortedContributions().length}
    <div class="min-w-0">
      {@render relatedSubmissions({ title: 'Related Contributions' })}
    </div>
  {/if}
</div>

<style>
  .project-slider {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding: 2px 0 16px;
    scroll-snap-type: x proximity;
    scrollbar-width: none;
  }

  .project-slider::-webkit-scrollbar {
    display: none;
  }

  .project-slider > :global(*) {
    scroll-snap-align: start;
  }

  .participant-scroll {
    scrollbar-width: none;
  }

  .participant-scroll::-webkit-scrollbar {
    display: none;
  }

  .project-about-scroll {
    scrollbar-width: thin;
    scrollbar-color: rgba(152, 162, 179, 0.62) transparent;
  }

  .project-about-scroll::-webkit-scrollbar {
    width: 6px;
  }

  .project-about-scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .project-about-scroll::-webkit-scrollbar-thumb {
    border-radius: 999px;
    background: rgba(152, 162, 179, 0.62);
  }

  .project-markdown :global(p) {
    margin: 0 0 0.9rem;
  }

  .project-markdown :global(p:last-child),
  .project-markdown :global(ul:last-child),
  .project-markdown :global(ol:last-child) {
    margin-bottom: 0;
  }

  .project-markdown :global(ul),
  .project-markdown :global(ol) {
    margin: 0.65rem 0 0.95rem;
    padding-left: 1.15rem;
  }

  .project-markdown :global(ul) {
    list-style: disc;
  }

  .project-markdown :global(ol) {
    list-style: decimal;
  }

  .project-markdown :global(li) {
    margin: 0.3rem 0;
  }

  .project-markdown :global(a) {
    color: #d87519;
    font-weight: 600;
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  .project-markdown :global(code) {
    border: 1px solid #eceff4;
    border-radius: 4px;
    background: #f7f8fb;
    padding: 0.05rem 0.28rem;
    color: #111827;
    font-size: 0.92em;
  }

  .project-markdown :global(h3) {
    margin: 1rem 0 0.45rem;
    color: #111827;
    font-size: 0.96rem;
    font-weight: 700;
  }

  .project-markdown :global(.project-mdx-media) {
    margin: 1.15rem 0;
  }

  .project-markdown :global(.project-mdx-image img) {
    display: block;
    width: 100%;
    max-height: 420px;
    border: 1px solid rgba(255, 255, 255, 0.78);
    border-radius: 8px;
    object-fit: cover;
    box-shadow: 0 18px 42px rgba(31, 42, 68, 0.12);
  }

  .project-markdown :global(.project-mdx-video-frame) {
    overflow: hidden;
    aspect-ratio: 16 / 9;
    border: 1px solid rgba(17, 24, 39, 0.88);
    border-radius: 8px;
    background: #0b0f19;
    box-shadow: 0 18px 42px rgba(31, 42, 68, 0.14);
  }

  .project-markdown :global(.project-mdx-video-frame iframe),
  .project-markdown :global(.project-mdx-video-frame video) {
    display: block;
    width: 100%;
    height: 100%;
  }

  .project-markdown :global(.project-mdx-video-link) {
    display: flex;
    width: 100%;
    height: 100%;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    color: #ffffff;
    font-weight: 700;
    text-decoration: none;
   }

  .project-markdown :global(.project-mdx-video-frame video) {
    object-fit: cover;
  }

  .project-markdown :global(figcaption) {
    margin-top: 0.55rem;
    color: #667085;
    font-size: 0.78rem;
    line-height: 1.4;
  }

</style>
