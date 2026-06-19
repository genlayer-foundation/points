<script>
  import { onMount } from 'svelte';
  import { partnersAPI, validatorsAPI, projectsAPI } from '../lib/api.js';
  import { resolvePortalLink } from '../lib/links.js';

  const TABS = [
    { id: 'all', label: 'All' },
    {
      id: 'project',
      label: 'Projects',
      accent: '#F59E0B',
    },
    {
      id: 'validator',
      label: 'Validators',
      accent: '#8B6BFF',
    },
    {
      id: 'partner',
      label: 'Partners',
      accent: '#3B82F6',
    },
  ];

  const CATEGORY_LABELS = {
    project: 'Project',
    validator: 'Validator',
    partner: 'Partner',
  };

  const ACCENTS = ['#8B6BFF', '#16A085', '#F59E0B', '#E2557A', '#2563EB', '#0F766E', '#B45309'];

  let items = $state([]);
  let loading = $state(true);
  let activeTab = $state('all');

  let grouped = $derived({
    partner: items.filter((i) => i.category === 'partner'),
    validator: items.filter((i) => i.category === 'validator'),
    project: items.filter((i) => i.category === 'project'),
  });

  let tabCounts = $derived({
    all: items.length,
    project: grouped.project.length,
    validator: grouped.validator.length,
    partner: grouped.partner.length,
  });

  let allSections = $derived([
    { id: 'project', label: 'Projects', items: grouped.project },
    { id: 'validator', label: 'Validators', items: grouped.validator },
    { id: 'partner', label: 'Partners', items: grouped.partner },
  ]);

  let filteredItems = $derived(activeTab === 'all' ? items : items.filter((item) => item.category === activeTab));

  function normalizePartner(p) {
    return {
      id: `partner-${p.id || p.slug}`,
      slug: p.slug,
      name: p.name,
      logo_url: p.logo_url || '',
      href: p.website_url || p.url || '#',
      isExternal: true,
      category: 'partner',
      accent: pickAccent(p.name || p.slug || 'partner'),
    };
  }

  function normalizeValidator(user) {
    return {
      id: `validator-${user.address || user.id || user.name}`,
      name: user.name || 'Validator',
      logo_url: user.profile_image_url || '',
      href: user.address ? `/participant/${user.address}` : '#',
      isExternal: false,
      category: 'validator',
      accent: pickAccent(user.name || user.address || 'validator'),
    };
  }

  function normalizeProject(b) {
    const link = resolvePortalLink(b.link || b.url);
    return {
      id: `project-${b.id || b.title}`,
      name: b.title || b.name || 'Project',
      logo_url: b.featured_profile_image_url || b.user_profile_image_url || '',
      background_url: b.hero_image_url || b.hero_image_url_tablet || b.hero_image_url_mobile || '',
      href: link.href,
      isExternal: link.external,
      category: 'project',
      accent: pickAccent(b.title || b.name || 'project'),
    };
  }

  function asArray(maybe) {
    if (Array.isArray(maybe)) return maybe;
    if (Array.isArray(maybe?.results)) return maybe.results;
    return [];
  }

  function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return '?';
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }

  function pickAccent(name) {
    let hash = 0;
    const source = name || '';
    for (let i = 0; i < source.length; i++) hash = (hash * 31 + source.charCodeAt(i)) | 0;
    return ACCENTS[Math.abs(hash) % ACCENTS.length];
  }

  function setActiveTab(tab) {
    activeTab = tab;
    const url = new URL(window.location.href);
    if (tab === 'all') {
      url.searchParams.delete('tab');
    } else {
      url.searchParams.set('tab', tab);
    }
    window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`);
  }

  onMount(async () => {
    const initialTab = new URLSearchParams(window.location.search).get('tab');
    if (TABS.some((tab) => tab.id === initialTab)) {
      activeTab = initialTab;
    }

    const [partnersRes, validatorsRes, buildsRes] = await Promise.allSettled([
      partnersAPI.list({ page_size: 200 }),
      validatorsAPI.getAllValidators(),
      projectsAPI.list(),
    ]);

    const partners =
      partnersRes.status === 'fulfilled'
        ? asArray(partnersRes.value?.data).map(normalizePartner)
        : [];

    const validators =
      validatorsRes.status === 'fulfilled'
        ? asArray(validatorsRes.value?.data)
            .map(normalizeValidator)
        : [];

    const projects =
      buildsRes.status === 'fulfilled'
        ? asArray(buildsRes.value?.data).map(normalizeProject)
        : [];

    items = [...partners, ...validators, ...projects];
    loading = false;
  });
</script>

{#snippet ecosystemItem(item, index)}
  <a
    href={item.href}
    target={item.isExternal ? '_blank' : undefined}
    rel={item.isExternal ? 'noopener noreferrer' : undefined}
    aria-label={item.name}
    title={item.name}
    class="brand-cell group relative flex min-w-0 overflow-hidden rounded-[14px] border border-[#ECEDF1] bg-white shadow-[0_1px_2px_rgba(20,20,40,0.04)] outline-none {item.category === 'project' ? 'project-card h-[154px]' : 'h-[108px] items-center justify-center'}"
    style="--brand-accent: {item.accent}; --brand-border: {item.accent}66; animation-delay: {Math.min(index * 12, 460)}ms;"
  >
    {#if item.category === 'project'}
      {#if item.background_url}
        <img
          src={item.background_url}
          alt=""
          loading="lazy"
          class="project-bg absolute inset-0 h-full w-full object-cover"
        />
      {:else}
        <div class="project-bg absolute inset-0 bg-[linear-gradient(135deg,#F2F3F7_0%,#FFFFFF_52%,#ECE8FF_100%)]"></div>
      {/if}
      <div class="absolute inset-0 bg-[linear-gradient(180deg,rgba(21,21,27,0.08)_0%,rgba(21,21,27,0.2)_42%,rgba(21,21,27,0.72)_100%)]"></div>

      <div class="project-logo absolute left-3 top-3 flex h-10 w-10 items-center justify-center rounded-[10px] border border-white/70 bg-white/92 p-1.5 shadow-[0_8px_20px_rgba(20,20,40,0.16)] backdrop-blur-md">
        {#if item.logo_url}
          <img src={item.logo_url} alt="" loading="lazy" class="h-full w-full object-contain" />
        {:else}
          <span class="ecosystem-mono text-[13px] font-semibold text-[#33333C]">{getInitials(item.name)}</span>
        {/if}
      </div>

      <div class="absolute inset-x-0 bottom-0 p-3">
        <span class="block truncate text-[14px] font-semibold leading-none text-white">{item.name}</span>
        <span class="ecosystem-mono mt-1.5 block text-[10.5px] font-medium uppercase text-white/72" style="letter-spacing: 0.08em;">
          Project
        </span>
      </div>
    {:else}
      <div class="brand-mark flex h-12 max-w-[116px] items-center justify-center text-[#33333C]">
        {#if item.logo_url && item.category === 'partner'}
          <span
            class="logo-mask block h-12 w-[116px]"
            style="-webkit-mask-image: url('{item.logo_url}'); mask-image: url('{item.logo_url}');"
            aria-hidden="true"
          ></span>
        {:else if item.logo_url && item.category === 'validator'}
          <img
            src={item.logo_url}
            alt=""
            loading="lazy"
            class="validator-avatar h-14 w-14 rounded-full border border-[#ECEDF1] object-cover shadow-[0_8px_18px_-14px_rgba(20,20,40,0.35)]"
          />
        {:else}
          <span class="ecosystem-mono text-[19px] font-semibold leading-none">{getInitials(item.name)}</span>
        {/if}
      </div>

      <div class="brand-caption absolute inset-x-0 bottom-0 px-3 pb-3 pt-8 text-center">
        <span class="block truncate text-[13px] font-semibold leading-none text-[#15151B]">{item.name}</span>
        <span class="ecosystem-mono mt-1 block text-[10.5px] font-medium uppercase text-[#9A9AA6]" style="letter-spacing: 0.08em;">
          {CATEGORY_LABELS[item.category]}
        </span>
      </div>
    {/if}
  </a>
{/snippet}

<div class="ecosystem-page relative -mx-3 -my-3 min-h-full overflow-hidden bg-[#FCFCFD] px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-[#EEF0F4]"></div>

  <div class="relative mx-auto max-w-[1380px]">
    <header class="grid gap-8 border-b border-[#EEF0F4] pb-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
      <div class="max-w-[720px]">
        <h1
          class="font-heading text-[38px] font-extrabold leading-[0.96] text-[#15151B] sm:text-[46px]"
          style="letter-spacing: -0.03em;"
        >
          Ecosystem
        </h1>
        <p class="mt-4 max-w-[640px] text-[16px] font-normal leading-[1.55] text-[#55555F]">
          A curated wall of projects, validators, and partners building across the GenLayer network.
        </p>
      </div>

      <div class="grid grid-cols-3 gap-x-5 gap-y-4 sm:flex sm:justify-end sm:gap-[34px]">
        {#each TABS.slice(1) as stat}
          <div class="text-left sm:text-right">
            <div class="ecosystem-mono text-[30px] font-semibold leading-none text-[#15151B] sm:text-[34px]" style="letter-spacing: -0.03em;">
              {tabCounts[stat.id]}
            </div>
            <div class="ecosystem-mono mt-2 text-[11px] font-medium uppercase text-[#9A9AA6]" style="letter-spacing: 0.08em;">
              {stat.label}
            </div>
          </div>
        {/each}
      </div>
    </header>

    <nav class="mt-5 flex items-end gap-1 overflow-x-auto border-b border-[#ECEDF1]" aria-label="Ecosystem filters">
      {#each TABS as tab}
        <button
          type="button"
          class="ecosystem-tab inline-flex h-12 flex-shrink-0 items-center gap-1.5 px-2 text-[13px] font-semibold text-[#777781] transition-colors sm:gap-2 sm:px-3 sm:text-[14px]"
          class:active={activeTab === tab.id}
          onclick={() => setActiveTab(tab.id)}
        >
          <span>{tab.label}</span>
          <span class="ecosystem-mono rounded-full border border-[#EEF0F4] bg-white px-2 py-0.5 text-[10.5px] font-medium text-[#A6A6B0]">
            {tabCounts[tab.id]}
          </span>
        </button>
      {/each}
    </nav>

    {#if loading}
      <div class="ecosystem-wall mt-6">
        {#each Array(24) as _, index}
          <div
            class="h-[108px] animate-pulse rounded-[14px] border border-[#ECEDF1] bg-white shadow-[0_1px_2px_rgba(20,20,40,0.04)]"
            style="animation-delay: {Math.min(index * 12, 460)}ms;"
          ></div>
        {/each}
      </div>
    {:else if items.length === 0}
      <div class="mt-6 rounded-[14px] border border-[#ECEDF1] bg-white px-6 py-14 text-center shadow-[0_1px_2px_rgba(20,20,40,0.04)]">
        <h2 class="font-heading text-[22px] font-bold text-[#15151B]">Nothing here yet</h2>
        <p class="mt-2 text-[15px] text-[#55555F]">Check back soon.</p>
      </div>
    {:else if activeTab === 'all'}
      <div class="mt-8 space-y-10">
        {#each allSections as section}
          {#if section.items.length}
            <section class="ecosystem-section">
              <div class="mb-4 flex items-end justify-between gap-4 border-b border-[#ECEDF1] pb-3">
                <h2 class="font-heading text-[18px] font-bold text-[#15151B]">{section.label}</h2>
                <span class="ecosystem-mono text-[11px] font-medium uppercase text-[#9A9AA6]" style="letter-spacing: 0.08em;">
                  {section.items.length}
                </span>
              </div>
              <div class="ecosystem-wall">
                {#each section.items as item, index (item.id)}
                  {@render ecosystemItem(item, index)}
                {/each}
              </div>
            </section>
          {/if}
        {/each}
      </div>
    {:else}
      <div class="ecosystem-wall mt-6">
        {#each filteredItems as item, index (item.id)}
          {@render ecosystemItem(item, index)}
        {/each}
      </div>
    {/if}
  </div>
</div>

<style>
  .ecosystem-page {
    color: #15151B;
  }

  .ecosystem-mono {
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  }

  .ecosystem-tab {
    box-shadow: inset 0 0 0 transparent;
  }

  .ecosystem-tab:hover,
  .ecosystem-tab.active {
    color: #15151B;
  }

  .ecosystem-tab.active {
    box-shadow: inset 0 -2px 0 #15151B;
  }

  .ecosystem-tab.active span:last-child {
    border-color: #E4E5EA;
    color: #15151B;
  }

  .ecosystem-wall {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(154px, 1fr));
    gap: 12px;
  }

  .brand-cell {
    animation: ecoFade 0.42s cubic-bezier(.4, 0, .2, 1) both;
    transition:
      transform 0.24s cubic-bezier(.4, 0, .2, 1),
      border-color 0.24s cubic-bezier(.4, 0, .2, 1),
      box-shadow 0.24s cubic-bezier(.4, 0, .2, 1);
  }

  .brand-cell:hover,
  .brand-cell:focus-visible {
    transform: translateY(-3px);
    border-color: var(--brand-border);
    box-shadow: 0 16px 30px -18px rgba(20, 20, 40, 0.28);
  }

  .project-card {
    border-color: rgba(236, 237, 241, 0.9);
  }

  .project-bg,
  .project-logo {
    transition:
      transform 0.24s cubic-bezier(.4, 0, .2, 1),
      opacity 0.24s cubic-bezier(.4, 0, .2, 1);
  }

  .project-card:hover .project-bg,
  .project-card:focus-visible .project-bg {
    transform: scale(1.035);
  }

  .project-card:hover .project-logo,
  .project-card:focus-visible .project-logo {
    transform: translateY(-2px);
  }

  .brand-mark {
    transition:
      transform 0.24s cubic-bezier(.4, 0, .2, 1),
      color 0.24s cubic-bezier(.4, 0, .2, 1);
  }

  .validator-avatar {
    filter: grayscale(0.18) saturate(0.9);
    transition:
      border-color 0.24s cubic-bezier(.4, 0, .2, 1),
      filter 0.24s cubic-bezier(.4, 0, .2, 1);
  }

  .brand-cell:hover .brand-mark,
  .brand-cell:focus-visible .brand-mark {
    color: var(--brand-accent);
    transform: translateY(-9px);
  }

  .brand-cell:hover .validator-avatar,
  .brand-cell:focus-visible .validator-avatar {
    border-color: var(--brand-border);
    filter: grayscale(0) saturate(1);
  }

  .logo-mask {
    background: currentColor;
    -webkit-mask-position: center;
    mask-position: center;
    -webkit-mask-repeat: no-repeat;
    mask-repeat: no-repeat;
    -webkit-mask-size: contain;
    mask-size: contain;
  }

  .brand-caption {
    background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #FFFFFF 42%, #FFFFFF 100%);
    opacity: 0;
    transform: translateY(8px);
    transition:
      opacity 0.24s cubic-bezier(.4, 0, .2, 1),
      transform 0.24s cubic-bezier(.4, 0, .2, 1);
  }

  .brand-cell:hover .brand-caption,
  .brand-cell:focus-visible .brand-caption {
    opacity: 1;
    transform: translateY(0);
  }

  @keyframes ecoFade {
    from {
      opacity: 0;
      transform: translateY(9px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
