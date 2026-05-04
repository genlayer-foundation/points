<script>
  import { onMount } from 'svelte';
  import { querystring } from 'svelte-spa-router';
  import { partnersAPI, validatorsAPI, featuredAPI } from '../lib/api.js';
  import PartnerCard from '../components/portal/partners/PartnerCard.svelte';

  const PAGE_SIZE = 30;

  const TABS = [
    { id: 'all', label: 'All' },
    { id: 'partner', label: 'Partners' },
    { id: 'validator', label: 'Validators' },
    { id: 'project', label: 'Projects' },
  ];

  // Per-category tinting for tab pills + badges + stat icons.
  const TAB_ACTIVE_CLASS = {
    all: 'bg-black text-white',
    partner: 'bg-black text-white',
    validator: 'bg-blue-600 text-white',
    project: 'bg-orange-500 text-white',
  };

  const STATS = [
    {
      id: 'partner',
      label: 'Partners',
      hex: '/assets/icons/hex-black-people.svg',
      overlay: null,
    },
    {
      id: 'validator',
      label: 'Validators',
      hex: '/assets/icons/hexagon-validator.svg',
      overlay: '/assets/icons/shield-white.svg',
    },
    {
      id: 'project',
      label: 'Projects',
      hex: '/assets/icons/hexagon-builder.svg',
      overlay: '/assets/icons/terminal-fill-white.svg',
    },
  ];

  let items = $state([]);
  let loading = $state(true);
  let activeTab = $state('all');
  let visibleCount = $state(PAGE_SIZE);

  let counts = $derived({
    all: items.length,
    partner: items.filter((i) => i.category === 'partner').length,
    validator: items.filter((i) => i.category === 'validator').length,
    project: items.filter((i) => i.category === 'project').length,
  });

  // Stat hexagons round the count down to the nearest 10 and append "+".
  // Tab pills keep the exact count so users still know what the filter shows.
  function roundedLabel(n) {
    if (!n) return '0';
    if (n < 10) return String(n);
    return `${Math.floor(n / 10) * 10}+`;
  }

  // Stable hash so the All-view order is shuffled but consistent across renders
  // (no jumping around between filter switches or after Load more).
  function hashId(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }

  let filtered = $derived(
    activeTab === 'all'
      ? [...items].sort((a, b) => hashId(a.id) - hashId(b.id))
      : items.filter((i) => i.category === activeTab)
  );

  let visible = $derived(filtered.slice(0, visibleCount));
  let hasMore = $derived(visible.length < filtered.length);

  function selectTab(id) {
    activeTab = id;
    visibleCount = PAGE_SIZE;
  }

  function loadMore() {
    visibleCount += PAGE_SIZE;
  }

  function normalizePartner(p) {
    return {
      id: `partner-${p.id || p.slug}`,
      slug: p.slug,
      name: p.name,
      logo_url: p.logo_url || '',
      href: p.website_url || p.url || '#',
      isExternal: true,
      category: 'partner',
    };
  }

  function normalizeValidator(user) {
    return {
      id: `validator-${user.address}`,
      name: user.name || 'Validator',
      logo_url: user.profile_image_url || '',
      href: user.address ? `#/participant/${user.address}` : '#',
      isExternal: false,
      category: 'validator',
    };
  }

  function normalizeProject(b) {
    const link = b.link || b.url || '';
    return {
      id: `project-${b.id || b.title}`,
      name: b.title || b.name || 'Project',
      logo_url: b.hero_image_url || b.user_profile_image_url || '',
      href: link || '#',
      isExternal: link.startsWith('http'),
      category: 'project',
    };
  }

  function asArray(maybe) {
    if (Array.isArray(maybe)) return maybe;
    if (Array.isArray(maybe?.results)) return maybe.results;
    return [];
  }

  onMount(async () => {
    // Allow deep-linking to a specific tab, e.g. /ecosystem-partners?tab=project
    const params = new URLSearchParams($querystring);
    const requested = params.get('tab');
    if (requested && TABS.some((t) => t.id === requested)) {
      activeTab = requested;
    }

    const [partnersRes, validatorsRes, buildsRes] = await Promise.allSettled([
      partnersAPI.list({ page_size: 200 }),
      // `getNewestValidators` returns graduated validators only (users with the
      // uptime contribution badge). Pull a wide page so we get the full list.
      validatorsAPI.getNewestValidators(200),
      featuredAPI.getBuilds(),
    ]);

    const partners =
      partnersRes.status === 'fulfilled'
        ? asArray(partnersRes.value?.data).map(normalizePartner)
        : [];

    const validators =
      validatorsRes.status === 'fulfilled'
        ? asArray(validatorsRes.value?.data)
            .filter((u) => u.address)
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

<div class="space-y-6 sm:space-y-8">
  <!-- Hero -->
  <section class="relative overflow-hidden rounded-[12px] bg-white border border-[#ececec]">
    <div
      class="absolute inset-0 pointer-events-none overflow-hidden"
      style="-webkit-mask-image: radial-gradient(ellipse 80% 100% at 100% 0%, black 10%, transparent 70%); mask-image: radial-gradient(ellipse 80% 100% at 100% 0%, black 10%, transparent 70%);"
    >
      <img
        src="/assets/illustrations/welcome-gradient.png"
        alt=""
        class="absolute inset-0 w-full h-full object-cover opacity-70"
      />
    </div>

    <div class="relative z-10 p-6 sm:p-8 md:p-10">
      <div class="space-y-2 max-w-xl">
        <h1
          class="text-[28px] md:text-[32px] font-medium font-display text-black"
          style="letter-spacing: -1px;"
        >
          Ecosystem Partners
        </h1>
        <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">
          The partners, validators, and projects building on GenLayer.
        </p>
      </div>
    </div>
  </section>

  <!-- Stats -->
  <section class="grid grid-cols-3 gap-[10px]">
    {#each STATS as stat}
      <div class="bg-white rounded-[10px] border border-[#ececec] p-4 flex items-center gap-3">
        <div class="relative w-10 h-10 flex-shrink-0">
          <img src={stat.hex} alt="" class="absolute inset-0 w-full h-full" />
          {#if stat.overlay}
            <img
              src={stat.overlay}
              alt=""
              class="absolute inset-0 m-auto w-[18px] h-[18px]"
            />
          {/if}
        </div>
        <div class="min-w-0">
          <div
            class="text-[24px] font-medium font-display text-black leading-none"
            style="letter-spacing: -0.5px;"
          >
            {loading ? '—' : roundedLabel(counts[stat.id] ?? 0)}
          </div>
          <div class="text-[12px] text-[#6b6b6b] mt-1 truncate">{stat.label}</div>
        </div>
      </div>
    {/each}
  </section>

  <!-- Tabs -->
  <section>
    <div class="flex items-center gap-2 overflow-x-auto pb-1" style="scrollbar-width: none;">
      {#each TABS as tab}
        {@const count = counts[tab.id] ?? 0}
        {@const isActive = activeTab === tab.id}
        <button
          type="button"
          onclick={() => selectTab(tab.id)}
          class="flex-shrink-0 px-4 py-2 rounded-full text-[13px] font-medium transition-colors {isActive
            ? TAB_ACTIVE_CLASS[tab.id]
            : 'bg-white text-[#4a4a4a] border border-[#e5e5e5] hover:bg-[#f8f8f8]'}"
        >
          {tab.label}
          <span class="ml-1 text-[12px] opacity-70">({count})</span>
        </button>
      {/each}
    </div>
  </section>

  <!-- Grid -->
  {#if loading}
    <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-[10px]">
      {#each Array(12) as _}
        <div class="aspect-square rounded-[10px] bg-[#f8f8f8] animate-pulse"></div>
      {/each}
    </div>
  {:else if visible.length === 0}
    <div class="bg-[#f8f8f8] rounded-[10px] p-12 text-center">
      <h3 class="font-heading font-semibold text-black">Nothing here yet</h3>
      <p class="mt-1 text-[14px] text-[#6b6b6b]">Check back soon — we're growing the ecosystem.</p>
    </div>
  {:else}
    <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-[10px]">
      {#each visible as item (item.id)}
        <PartnerCard {item} showBadge={activeTab === 'all'} />
      {/each}
    </div>

    {#if hasMore}
      <div class="flex justify-center pt-2">
        <button
          type="button"
          onclick={loadMore}
          class="px-5 py-2 rounded-full bg-white text-black border border-[#e5e5e5] text-[13px] font-medium hover:bg-[#f8f8f8] transition-colors"
        >
          Load more
        </button>
      </div>
    {/if}
  {/if}

  <!-- Footer banner — blends with the page background like Overview/Profile -->
  <section class="relative -mx-3 -mb-3 mt-12 pt-8">
    <div
      class="absolute inset-0 pointer-events-none overflow-hidden"
      style="-webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 40%); mask-image: linear-gradient(to bottom, transparent 0%, black 40%);"
    >
      <div class="absolute inset-0 flex items-center justify-center">
        <div
          class="relative w-full h-full"
          style="-webkit-mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); -webkit-mask-size: 1818px 1489.395px; mask-size: 1818px 1489.395px; -webkit-mask-position: center; mask-position: center; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;"
        >
          <img
            src="/assets/illustrations/welcome-gradient.png"
            alt=""
            class="absolute inset-0 w-full h-full object-cover mix-blend-screen"
          />
        </div>
      </div>
    </div>

    <div class="relative z-10 px-8 md:px-20 py-20 md:py-28 text-center">
      <h2
        class="text-3xl md:text-[44px] font-medium text-gray-900 font-display leading-tight mb-3"
        style="letter-spacing: -1.28px;"
      >
        An ecosystem in motion.
      </h2>
      <p class="text-[15px] text-[#6b6b6b] max-w-xl mx-auto">
        Partners, validators, and project teams shipping on GenLayer — the adjudication layer for AI agents.
      </p>
    </div>
  </section>
</div>
