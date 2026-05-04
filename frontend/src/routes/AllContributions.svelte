<script>
  import { onMount } from 'svelte';
  import { push, location } from 'svelte-spa-router';
  import { contributionsAPI, usersAPI } from '../lib/api';
  import { getMissions } from '../lib/missionsStore.js';
  import { getContributionTypes } from '../lib/api/contributions.js';
  import HighlightCard from '../components/portal/HighlightCard.svelte';
  import HighlightsSlider from '../components/portal/HighlightsSlider.svelte';
  import PortalContributionCard from '../components/portal/PortalContributionCard.svelte';
  import SearchBar from '../components/portal/SearchBar.svelte';
  import Pagination from '../components/Pagination.svelte';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';
  import CTABanner from '../components/shared/CTABanner.svelte';

  const HIGHLIGHTS_PREVIEW_COUNT = 15;
  const PAGE_SIZE = 20;

  const SORT_MAP = {
    newest: '-contribution_date',
    oldest: 'contribution_date',
    highest: '-frozen_global_points',
    lowest: 'frozen_global_points',
  };
  const SORT_REVERSE = Object.fromEntries(Object.entries(SORT_MAP).map(([k, v]) => [v, k]));

  const CATEGORY_OPTIONS = [
    { id: 'all', label: 'All', icon: 'genlayer' },
    { id: 'builder', label: 'Builder', icon: 'builder' },
    { id: 'validator', label: 'Validator', icon: 'validator' },
    { id: 'community', label: 'Community', icon: 'community' },
  ];

  // === Routing context ===
  function detectRouteCategory(path) {
    if (path.startsWith('/builders')) return 'builder';
    if (path.startsWith('/validators')) return 'validator';
    if (path.startsWith('/community')) return 'community';
    return 'all';
  }
  function buildBasePath(path) {
    if (path.startsWith('/builders')) return '/builders/all-contributions';
    if (path.startsWith('/validators')) return '/validators/all-contributions';
    if (path.startsWith('/community')) return '/community/all-contributions';
    return '/all-contributions';
  }

  // === State ===
  let category = $state('all');
  let typeId = $state('');
  let missionId = $state('');
  let participantQuery = $state('');
  let sortBy = $state('-contribution_date');
  let view = $state('both'); // 'both' | 'highlights' | 'all'
  let highlightsPage = $state(1);
  let allPage = $state(1);
  let searchInput = $state('');

  // Data
  let highlights = $state([]);
  let highlightsCount = $state(0);
  let highlightsLoading = $state(false);
  let highlightsError = $state(null);
  let contributions = $state([]);
  let contributionsCount = $state(0);
  let contributionsLoading = $state(false);
  let contributionsError = $state(null);

  // Catalogs (for filter dropdowns)
  let allTypes = $state([]); // submittable types only
  let allMissions = $state([]);
  let typesLoading = $state(false);

  // Cached names for filter chips when URL targets a non-submittable type
  let activeTypeName = $state('');
  let activeMissionName = $state('');
  let participantDetails = $state(null);

  let baseRoutePath = $derived(buildBasePath($location));
  let routeIsHighlightsView = $derived($location.endsWith('/highlights'));
  let routeCategory = $derived(detectRouteCategory($location));

  let typesForCategory = $derived(
    category === 'all' ? allTypes : allTypes.filter(t => t.category === category)
  );
  // Surface the URL-applied type as a synthetic option when it's not in the submittable list
  let typesForDropdown = $derived.by(() => {
    if (!typeId) return typesForCategory;
    if (typesForCategory.some(t => String(t.id) === String(typeId))) return typesForCategory;
    if (!activeTypeName) return typesForCategory;
    return [{ id: typeId, name: activeTypeName }, ...typesForCategory];
  });
  let missionsForType = $derived(
    typeId ? allMissions.filter(m => String(m.contribution_type) === String(typeId)) : []
  );

  let hasActiveFilters = $derived(
    category !== routeCategory || !!typeId || !!missionId || !!participantQuery || sortBy !== '-contribution_date'
  );

  function looksLikeAddress(s) {
    return s && s.trim().toLowerCase().startsWith('0x');
  }

  // === Search syntax ===
  function parseSearchInput(input) {
    let sortValue = '-contribution_date';
    let text = input || '';
    const match = text.match(/(?:^|\s)sort:(\S+)/i);
    if (match) {
      const key = match[1].toLowerCase();
      if (SORT_MAP[key]) sortValue = SORT_MAP[key];
      text = (text.slice(0, match.index) + ' ' + text.slice(match.index + match[0].length)).trim();
    }
    return { sortValue, participantText: text };
  }

  function serializeSearchInput(participantText, sortValue) {
    const sortKey = SORT_REVERSE[sortValue];
    if (sortValue === '-contribution_date' || !sortKey) return participantText || '';
    return `sort:${sortKey}${participantText ? ' ' + participantText : ''}`;
  }

  // === URL <-> state sync ===
  function parseUrlParams() {
    const hash = window.location.hash || '';
    const queryString = hash.includes('?') ? hash.split('?')[1] : '';
    const params = new URLSearchParams(queryString);

    const urlCategory = params.get('category');
    category = ['all', 'builder', 'validator', 'community'].includes(urlCategory)
      ? urlCategory
      : routeCategory;

    typeId = params.get('type') || '';
    missionId = params.get('mission') || '';
    participantQuery = params.get('user') || '';
    sortBy = params.get('sort') || '-contribution_date';

    const urlView = params.get('view');
    view = ['highlights', 'all', 'both'].includes(urlView)
      ? urlView
      : (routeIsHighlightsView ? 'highlights' : 'both');

    highlightsPage = Math.max(1, Number(params.get('hpage')) || 1);
    allPage = Math.max(1, Number(params.get('page')) || 1);
    searchInput = serializeSearchInput(participantQuery, sortBy);
  }

  function updateUrl() {
    const params = new URLSearchParams();
    if (category !== routeCategory) {
      if (category !== 'all') params.set('category', category);
      else if (routeCategory !== 'all') params.set('category', 'all');
    }
    if (typeId) params.set('type', String(typeId));
    if (missionId) params.set('mission', String(missionId));
    if (participantQuery) params.set('user', participantQuery);
    if (sortBy !== '-contribution_date') params.set('sort', sortBy);
    const naturalView = routeIsHighlightsView ? 'highlights' : 'both';
    if (view !== naturalView) params.set('view', view);
    if (highlightsPage > 1) params.set('hpage', String(highlightsPage));
    if (allPage > 1) params.set('page', String(allPage));

    const qs = params.toString();
    const targetHash = '#' + baseRoutePath + (qs ? `?${qs}` : '');
    if (window.location.hash !== targetHash) {
      window.history.replaceState({}, '', targetHash);
      lastHash = targetHash;
    }
  }

  // === Single helper: reset paging, sync URL, refetch ===
  function resetAndLoad() {
    highlightsPage = 1;
    allPage = 1;
    updateUrl();
    loadHighlights();
    loadAllContributions();
    resolveTypeName();
    resolveMissionName();
  }

  // === Filter actions ===
  function setCategory(next) {
    if (category === next) return;
    category = next;
    typeId = '';
    missionId = '';
    activeTypeName = '';
    activeMissionName = '';
    resetAndLoad();
  }
  function setView(next) {
    if (view === next) return;
    view = next;
    resetAndLoad();
  }
  function onTypeChange() {
    missionId = '';
    activeTypeName = '';
    activeMissionName = '';
    resetAndLoad();
  }
  function onMissionChange() {
    activeMissionName = '';
    resetAndLoad();
  }

  function onSearchChange() {
    const { sortValue, participantText } = parseSearchInput(searchInput);
    participantQuery = participantText;
    sortBy = sortValue;
    loadParticipantDetails();
    resetAndLoad();
  }
  function clearSearch() {
    participantQuery = '';
    sortBy = '-contribution_date';
    participantDetails = null;
    resetAndLoad();
  }

  function clearAllFilters() {
    category = routeCategory;
    typeId = '';
    missionId = '';
    participantQuery = '';
    sortBy = '-contribution_date';
    activeTypeName = '';
    activeMissionName = '';
    participantDetails = null;
    searchInput = '';
    resetAndLoad();
  }
  function clearTypeFilter() {
    typeId = '';
    missionId = '';
    activeTypeName = '';
    activeMissionName = '';
    resetAndLoad();
  }
  function clearMissionFilter() {
    missionId = '';
    activeMissionName = '';
    resetAndLoad();
  }
  function clearParticipantFilter() {
    participantQuery = '';
    participantDetails = null;
    searchInput = serializeSearchInput('', sortBy);
    resetAndLoad();
  }

  // === Pagination ===
  function handleAllPageChange(event) {
    allPage = event.detail;
    updateUrl();
    loadAllContributions();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  function handleHighlightsPageChange(event) {
    highlightsPage = event.detail;
    updateUrl();
    loadHighlights();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // === Loaders ===
  // Set of submittable type IDs (string-keyed for easy lookup); used to filter
  // out non-submittable contributions client-side from the highlights endpoint.
  let submittableTypeIds = $derived(new Set(allTypes.map(t => String(t.id))));

  function buildBaseParams() {
    // Always restrict to submittable contribution types — non-submittable types
    // (badges, journey rewards) are not user-facing in the explorer.
    const params = { submittable_only: 'true' };
    if (category !== 'all') params.category = category;
    if (typeId) params.contribution_type = typeId;
    if (missionId) params.mission = missionId;
    if (participantQuery?.trim()) {
      const q = participantQuery.trim();
      if (looksLikeAddress(q)) params.user_address = q;
      else params.search = q;
    }
    return params;
  }

  function sortHighlights(items) {
    return [...items].sort((a, b) => {
      switch (sortBy) {
        case 'contribution_date':
          return new Date(a.contribution_date) - new Date(b.contribution_date);
        case '-frozen_global_points':
          return (b.contribution_points || 0) - (a.contribution_points || 0);
        case 'frozen_global_points':
          return (a.contribution_points || 0) - (b.contribution_points || 0);
        default:
          return new Date(b.contribution_date) - new Date(a.contribution_date);
      }
    });
  }

  function filterHighlightsClientSide(items) {
    const q = participantQuery?.trim().toLowerCase() || '';
    const isAddress = looksLikeAddress(q);
    // Only apply the submittable filter once the catalog has loaded; otherwise
    // we'd briefly render an empty list while `allTypes` is still empty.
    const enforceSubmittable = submittableTypeIds.size > 0;
    return items.filter(h => {
      if (enforceSubmittable && !submittableTypeIds.has(String(h.contribution_type))) return false;
      if (typeId && String(h.contribution_type) !== String(typeId)) return false;
      if (missionId && String(h.mission_id ?? h.mission?.id ?? '') !== String(missionId)) return false;
      if (!q) return true;
      if (isAddress) return (h.user_address || '').toLowerCase() === q;
      const name = (h.user_name || '').toLowerCase();
      const addr = (h.user_address || '').toLowerCase();
      return name.includes(q) || addr.includes(q);
    });
  }

  async function loadHighlights() {
    if (view === 'all') {
      highlights = [];
      highlightsCount = 0;
      return;
    }
    highlightsLoading = true;
    highlightsError = null;
    try {
      // Backend /highlights/ only honors `category` server-side; rest is client-side.
      const params = category !== 'all' ? { category } : {};
      const response = await contributionsAPI.getAllHighlights(params);
      const all = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      const sorted = sortHighlights(filterHighlightsClientSide(all));
      highlightsCount = sorted.length;
      const start = view === 'both' ? 0 : (highlightsPage - 1) * PAGE_SIZE;
      const end = view === 'both' ? HIGHLIGHTS_PREVIEW_COUNT : start + PAGE_SIZE;
      highlights = sorted.slice(start, end);
    } catch (err) {
      highlightsError = err?.message || 'Failed to load highlights';
      highlights = [];
      highlightsCount = 0;
    } finally {
      highlightsLoading = false;
    }
  }

  async function loadAllContributions() {
    if (view === 'highlights') {
      contributions = [];
      contributionsCount = 0;
      return;
    }
    contributionsLoading = true;
    contributionsError = null;
    try {
      const response = await contributionsAPI.getContributions({
        ...buildBaseParams(),
        page: allPage,
        page_size: PAGE_SIZE,
        ordering: sortBy,
      });
      contributions = response.data?.results || [];
      contributionsCount = response.data?.count || 0;
    } catch (err) {
      contributionsError = err?.message || 'Failed to load contributions';
      contributions = [];
      contributionsCount = 0;
    } finally {
      contributionsLoading = false;
    }
  }

  async function loadParticipantDetails() {
    if (!participantQuery || !looksLikeAddress(participantQuery)) {
      participantDetails = null;
      return;
    }
    try {
      const response = await usersAPI.getUserByAddress(participantQuery.trim());
      participantDetails = response.data;
    } catch {
      participantDetails = null;
    }
  }

  async function resolveTypeName() {
    if (!typeId) {
      activeTypeName = '';
      return;
    }
    const fromList = allTypes.find(t => String(t.id) === String(typeId));
    if (fromList) {
      activeTypeName = fromList.name;
      return;
    }
    try {
      const res = await contributionsAPI.getContributionType(typeId);
      activeTypeName = res.data?.name || '';
    } catch {
      activeTypeName = '';
    }
  }

  async function resolveMissionName() {
    if (!missionId) {
      activeMissionName = '';
      return;
    }
    const fromList = allMissions.find(m => String(m.id) === String(missionId));
    if (fromList) {
      activeMissionName = fromList.name;
      // Backfill parent type id so the mission dropdown becomes enabled
      if (!typeId && fromList.contribution_type) {
        typeId = String(fromList.contribution_type);
        resolveTypeName();
      }
      return;
    }
    try {
      const res = await contributionsAPI.getMission(missionId);
      activeMissionName = res.data?.name || '';
      if (!typeId && res.data?.contribution_type) {
        typeId = String(res.data.contribution_type);
        resolveTypeName();
      }
    } catch {
      activeMissionName = '';
    }
  }

  async function loadCatalogs() {
    typesLoading = true;
    try {
      const [types, missions] = await Promise.all([
        getContributionTypes({ is_submittable: 'true' }),
        getMissions({ is_active: true }),
      ]);
      allTypes = Array.isArray(types) ? [...types].sort((a, b) => a.name.localeCompare(b.name)) : [];
      allMissions = Array.isArray(missions) ? missions : [];
    } catch {
      allTypes = [];
      allMissions = [];
    } finally {
      typesLoading = false;
    }
  }

  // === Page title ===
  let categoryLabel = $derived(
    category === 'builder' ? 'Builder'
    : category === 'validator' ? 'Validator'
    : category === 'community' ? 'Community'
    : 'All'
  );
  let pageTitle = $derived(
    participantDetails?.name
      ? `${participantDetails.name}'s contributions`
      : view === 'highlights'
        ? `${categoryLabel} highlights`
        : `${categoryLabel} contributions`
  );
  let pageSubtitle = $derived(
    view === 'highlights'
      ? (highlightsLoading ? 'Exceptional contributions from the community' : `${highlightsCount} highlight${highlightsCount === 1 ? '' : 's'}`)
      : 'Browse highlighted and recent contributions'
  );

  let viewAllHighlightsHref = $derived.by(() => {
    if (view !== 'both' || highlightsCount <= HIGHLIGHTS_PREVIEW_COUNT) return '';
    const params = new URLSearchParams();
    if (category !== routeCategory) {
      if (category !== 'all') params.set('category', category);
      else if (routeCategory !== 'all') params.set('category', 'all');
    }
    if (typeId) params.set('type', String(typeId));
    if (missionId) params.set('mission', String(missionId));
    if (participantQuery) params.set('user', participantQuery);
    if (sortBy !== '-contribution_date') params.set('sort', sortBy);
    if (!routeIsHighlightsView) params.set('view', 'highlights');
    const qs = params.toString();
    return baseRoutePath + (qs ? `?${qs}` : '');
  });

  let highlightsTotalPages = $derived(Math.max(1, Math.ceil(highlightsCount / PAGE_SIZE)));

  function categoryAccent(cat) {
    switch (cat) {
      case 'builder': return { bg: '#FEF3E2', text: '#EE8521', border: '#EE8521' };
      case 'validator': return { bg: '#EBF3FE', text: '#387DE8', border: '#387DE8' };
      case 'community': return { bg: '#F4ECFD', text: '#7F52E1', border: '#7F52E1' };
      default: return { bg: '#EEEDFB', text: '#6D5DD3', border: '#8D81E1' };
    }
  }

  // === Lifecycle ===
  let isMounted = $state(false);
  let lastHash = $state('');

  function handleHashChange() {
    if (!isMounted) return;
    if (window.location.hash === lastHash) return;
    lastHash = window.location.hash;
    parseUrlParams();
    loadParticipantDetails();
    resolveTypeName();
    resolveMissionName();
    loadHighlights();
    loadAllContributions();
  }

  onMount(async () => {
    parseUrlParams();
    lastHash = window.location.hash;
    await loadCatalogs();
    await Promise.all([loadParticipantDetails(), resolveTypeName(), resolveMissionName()]);
    await Promise.all([loadHighlights(), loadAllContributions()]);
    isMounted = true;
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  });

  // Re-resolve names when catalogs load (URL may have preselected something)
  $effect(() => {
    if (allTypes.length || allMissions.length) {
      resolveTypeName();
      resolveMissionName();
    }
  });
</script>

<!-- ===== Reusable snippets: skeletons, empty states, CTAs ===== -->
{#snippet highlightSkeleton()}
  <div class="rounded-[8px] bg-white border border-[#f0f0f0] p-4 flex flex-col gap-2 h-[180px] overflow-hidden">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-3 w-20 rounded bg-[#f1f1f1] sk-shimmer"></div>
      </div>
      <div class="flex items-center gap-2">
        <div class="h-4 w-12 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        <div class="w-7 h-7 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
      </div>
    </div>
    <div class="flex-1 flex flex-col gap-1.5 pt-1">
      <div class="h-3 w-3/4 rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-2.5 w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-2.5 w-5/6 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="flex items-center justify-between">
      <div class="h-4 w-24 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-3 w-16 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
  </div>
{/snippet}

{#snippet contributionSkeleton()}
  <div class="rounded-[8px] bg-white border border-[#f0f0f0] p-4 flex flex-col gap-2 h-[180px] overflow-hidden">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
        <div class="h-3 w-20 rounded bg-[#f1f1f1] sk-shimmer"></div>
      </div>
      <div class="h-4 w-12 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="flex-1 flex flex-col gap-1.5 pt-1">
      <div class="h-3 w-2/3 rounded bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-2.5 w-full rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
    <div class="flex items-center justify-between">
      <div class="h-4 w-20 rounded-full bg-[#f1f1f1] sk-shimmer"></div>
      <div class="h-3 w-14 rounded bg-[#f1f1f1] sk-shimmer"></div>
    </div>
  </div>
{/snippet}

{#snippet emptyState(iconRender, title, description, action)}
  <div class="w-full rounded-[16px] border border-dashed border-[#e6e6e6] bg-[#fafafa] flex flex-col items-center justify-center text-center px-6 py-12 gap-3">
    {@render iconRender()}
    <div class="flex flex-col gap-1 max-w-md">
      <h3 class="text-[15px] font-semibold text-black">{title}</h3>
      <p class="text-[13px] text-[#6b6b6b] leading-snug">{description}</p>
    </div>
    {#if action}
      <div class="mt-2">{@render action()}</div>
    {/if}
  </div>
{/snippet}

{#snippet starIcon()}
  <div class="relative w-12 h-12">
    <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full" />
    <div
      class="absolute inset-0 m-auto w-6 h-6"
      style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
    ></div>
  </div>
{/snippet}

{#snippet docIcon()}
  <div class="w-12 h-12 rounded-full bg-white border border-[#e6e6e6] flex items-center justify-center">
    <svg class="w-6 h-6 text-[#999]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="9" y1="13" x2="15" y2="13" />
      <line x1="9" y1="17" x2="13" y2="17" />
    </svg>
  </div>
{/snippet}

{#snippet clearFiltersAction()}
  <button
    type="button"
    onclick={clearAllFilters}
    class="px-4 py-2 rounded-[20px] bg-[#101010] text-white text-[13px] font-medium hover:bg-black transition-colors"
  >
    Clear filters
  </button>
{/snippet}

{#snippet submitContributionAction()}
  <button
    type="button"
    onclick={() => push('/submit-contribution')}
    class="px-4 py-2 rounded-[20px] bg-[#101010] text-white text-[13px] font-medium hover:bg-black transition-colors"
  >
    Submit a contribution
  </button>
{/snippet}

{#snippet highlightsEmptyState()}
  {@render emptyState(
    starIcon,
    hasActiveFilters ? 'No highlights match these filters' : 'No highlighted contributions yet',
    hasActiveFilters
      ? 'Try clearing some filters to see highlighted contributions from other categories or types.'
      : 'Submit impactful or pioneering work and a steward may highlight it.',
    hasActiveFilters ? clearFiltersAction : submitContributionAction
  )}
{/snippet}

{#snippet contributionsEmptyState()}
  {@render emptyState(
    docIcon,
    hasActiveFilters ? 'No contributions match these filters' : 'No contributions yet',
    hasActiveFilters
      ? 'Try clearing some filters or searching by a different name or address.'
      : 'Be the first — submit a contribution to get started.',
    hasActiveFilters ? clearFiltersAction : submitContributionAction
  )}
{/snippet}

<div class="space-y-8">
  <!-- Header -->
  <div class="flex flex-col gap-1">
    <h1 class="text-[28px] md:text-[32px] font-semibold text-black" style="letter-spacing: -0.4px;">{pageTitle}</h1>
    <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">{pageSubtitle}</p>
  </div>

  <!-- Filter bar -->
  <div class="bg-white border border-[#f0f0f0] rounded-[16px] p-4 md:p-5 space-y-4">
    <!-- Category pills -->
    <div class="flex flex-wrap gap-2">
      {#each CATEGORY_OPTIONS as opt}
        {@const a = categoryAccent(opt.id)}
        {@const active = category === opt.id}
        <button
          type="button"
          onclick={() => setCategory(opt.id)}
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[13px] font-medium transition-colors"
          style={active
            ? `background: ${a.bg}; color: ${a.text}; border: 1px solid ${a.border};`
            : 'background: #f8f8f8; color: #6b6b6b; border: 1px solid #f0f0f0;'}
        >
          <CategoryIcon category={opt.icon} mode="small" size={14} />
          {opt.label}
        </button>
      {/each}
    </div>

    <!-- Filter row -->
    <div class="grid grid-cols-1 md:grid-cols-[1fr_1fr_2fr] gap-3">
      <div class="flex flex-col gap-1">
        <label for="type-select" class="text-[12px] font-medium text-[#6b6b6b]" style="letter-spacing: 0.24px;">Contribution type</label>
        <select
          id="type-select"
          bind:value={typeId}
          onchange={onTypeChange}
          disabled={typesLoading}
          class="w-full px-3 py-2 border border-[#e6e6e6] rounded-[8px] bg-white text-[14px] text-black focus:outline-none focus:border-[#8D81E1] transition-colors"
        >
          <option value="" selected={!typeId}>All types</option>
          {#each typesForDropdown as type (type.id)}
            <option value={String(type.id)} selected={String(type.id) === String(typeId)}>{type.name}</option>
          {/each}
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label for="mission-select" class="text-[12px] font-medium text-[#6b6b6b]" style="letter-spacing: 0.24px;">Mission</label>
        <select
          id="mission-select"
          bind:value={missionId}
          onchange={onMissionChange}
          disabled={!typeId || missionsForType.length === 0}
          class="w-full px-3 py-2 border border-[#e6e6e6] rounded-[8px] bg-white text-[14px] text-black focus:outline-none focus:border-[#8D81E1] disabled:bg-[#f8f8f8] disabled:text-[#bababa] transition-colors"
        >
          <option value="" selected={!missionId}>{typeId ? (missionsForType.length === 0 ? 'No missions' : 'Any mission') : 'Select a type first'}</option>
          {#each missionsForType as mission (mission.id)}
            <option value={String(mission.id)} selected={String(mission.id) === String(missionId)}>{mission.name}</option>
          {/each}
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label for="search-input" class="text-[12px] font-medium text-[#6b6b6b]" style="letter-spacing: 0.24px;">Search</label>
        <SearchBar
          id="search-input"
          bind:value={searchInput}
          placeholder="name, 0x… · sort:newest"
          debounceMs={300}
          onChange={onSearchChange}
          onClear={clearSearch}
          helpTitle="Search syntax"
        >
          {#snippet helpBody()}
            <p class="text-[12px] text-[#6b6b6b] mb-3 leading-snug">
              Type a name or 0x address to filter by participant. Add a <code class="font-mono bg-[#f5f5f5] px-1 rounded">sort:</code> tag to change ordering.
            </p>
            <ul class="space-y-1.5 text-[12px]">
              {#each [['sort:newest', 'Newest first (default)'], ['sort:oldest', 'Oldest first'], ['sort:highest', 'Highest points first'], ['sort:lowest', 'Lowest points first']] as [tag, desc]}
                <li class="flex items-start gap-2">
                  <code class="font-mono bg-[#f5f5f5] px-1.5 py-0.5 rounded text-black whitespace-nowrap">{tag}</code>
                  <span class="text-[#6b6b6b]">{desc}</span>
                </li>
              {/each}
            </ul>
            <div class="mt-3 pt-3 border-t border-[#f0f0f0]">
              <p class="text-[11px] text-[#999] mb-1">Examples</p>
              {#each ['alice', 'sort:highest', 'sort:newest 0x1234'] as ex}
                <div class="font-mono text-[11px] text-[#6b6b6b] bg-[#fafafa] rounded px-2 py-1 mb-1 last:mb-0">{ex}</div>
              {/each}
            </div>
          {/snippet}
        </SearchBar>
      </div>
    </div>

    <!-- View toggle + clear -->
    <div class="flex items-center justify-between flex-wrap gap-3 pt-1">
      <div class="inline-flex items-center bg-[#f8f8f8] rounded-[8px] p-1 border border-[#f0f0f0]">
        {#each [{ id: 'both', label: 'Both' }, { id: 'highlights', label: 'Highlights only' }, { id: 'all', label: 'Contributions only' }] as opt}
          <button
            type="button"
            onclick={() => setView(opt.id)}
            class="px-3 py-1 rounded-[6px] text-[13px] font-medium transition-colors"
            style={view === opt.id
              ? 'background: white; color: black; box-shadow: 0 1px 2px rgba(0,0,0,0.04);'
              : 'background: transparent; color: #6b6b6b;'}
          >
            {opt.label}
          </button>
        {/each}
      </div>
      {#if hasActiveFilters}
        <button type="button" onclick={clearAllFilters} class="text-[13px] text-[#6b6b6b] hover:text-black transition-colors">
          Clear filters
        </button>
      {/if}
    </div>

    <!-- Active filter chips -->
    {#if (typeId && activeTypeName) || (missionId && activeMissionName) || (participantQuery && !looksLikeAddress(participantQuery))}
      <div class="flex flex-wrap gap-2 pt-1">
        {#if typeId && activeTypeName}
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] bg-[#f8f8f8] border border-[#f0f0f0] text-black">
            Type: {activeTypeName}
            <button type="button" onclick={clearTypeFilter} class="text-[#6b6b6b] hover:text-black leading-none">×</button>
          </span>
        {/if}
        {#if missionId && activeMissionName}
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] bg-[#f8f8f8] border border-[#f0f0f0] text-black">
            Mission: {activeMissionName}
            <button type="button" onclick={clearMissionFilter} class="text-[#6b6b6b] hover:text-black leading-none">×</button>
          </span>
        {/if}
        {#if participantQuery && !looksLikeAddress(participantQuery)}
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] bg-[#f8f8f8] border border-[#f0f0f0] text-black">
            Search: {participantQuery}
            <button type="button" onclick={clearParticipantFilter} class="text-[#6b6b6b] hover:text-black leading-none">×</button>
          </span>
        {/if}
      </div>
    {/if}
  </div>

  <!-- Highlights section -->
  {#if view !== 'all'}
    <section class="space-y-3">
      {#if view === 'both'}
        <div class="flex items-end justify-between gap-3">
          <div class="flex items-center gap-2">
            <h2 class="text-[16px] font-semibold text-black" style="letter-spacing: -0.2px;">Highlights</h2>
            <span class="text-[12px] text-[#999]">· {highlightsCount}</span>
          </div>
          {#if viewAllHighlightsHref}
            <button type="button" onclick={() => push(viewAllHighlightsHref)} class="flex items-center gap-1 text-[13px] text-[#6b6b6b] hover:text-black transition-colors">
              View all <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4" />
            </button>
          {/if}
        </div>
      {/if}

      {#if highlightsError}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-[12px] text-sm">{highlightsError}</div>
      {:else if view === 'both'}
        <HighlightsSlider
          {highlights}
          loading={highlightsLoading}
          emptyTitle={hasActiveFilters ? 'No highlights match these filters' : 'No highlights yet'}
          emptyMessage={hasActiveFilters
            ? 'Try clearing some filters to see highlighted contributions from other categories or types.'
            : 'Submit impactful or pioneering work and a steward may highlight it.'}
          emptyAction={hasActiveFilters ? clearFiltersAction : submitContributionAction}
        />
      {:else if highlightsLoading}
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {#each Array(10) as _}
            {@render highlightSkeleton()}
          {/each}
        </div>
      {:else if highlights.length === 0}
        {@render highlightsEmptyState()}
      {:else}
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {#each highlights as highlight (highlight.id || highlight.contribution)}
            <HighlightCard {highlight} />
          {/each}
        </div>
        {#if highlightsTotalPages > 1}
          <Pagination page={highlightsPage} limit={PAGE_SIZE} totalCount={highlightsCount} on:pageChange={handleHighlightsPageChange} />
        {/if}
      {/if}
    </section>
  {/if}

  <!-- All contributions section -->
  {#if view !== 'highlights'}
    <section class="space-y-3">
      {#if view === 'both'}
        <div class="flex items-center gap-3 pt-3">
          <div class="flex items-center gap-2 flex-shrink-0">
            <h2 class="text-[16px] font-semibold text-black" style="letter-spacing: -0.2px;">Contributions</h2>
            <span class="text-[12px] text-[#999]">· {contributionsLoading ? '…' : `${contributionsCount} total`}</span>
          </div>
          <div class="flex-1 h-px bg-[#e6e6e6]"></div>
        </div>
      {:else}
        <div class="flex items-center gap-2">
          <h2 class="text-[16px] font-semibold text-black" style="letter-spacing: -0.2px;">Contributions</h2>
          <span class="text-[12px] text-[#999]">· {contributionsLoading ? '…' : `${contributionsCount} total`}</span>
        </div>
      {/if}

      {#if contributionsError}
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-[12px] text-sm">{contributionsError}</div>
      {:else if contributionsLoading}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {#each Array(8) as _}
            {@render contributionSkeleton()}
          {/each}
        </div>
      {:else if contributions.length === 0}
        {@render contributionsEmptyState()}
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {#each contributions as contribution (contribution.id)}
            <PortalContributionCard {contribution} category={category === 'all' ? null : category} />
          {/each}
        </div>
        {#if contributionsCount > PAGE_SIZE}
          <Pagination page={allPage} limit={PAGE_SIZE} totalCount={contributionsCount} on:pageChange={handleAllPageChange} />
        {/if}
      {/if}
    </section>
  {/if}

  <!-- Branding footer -->
  <div class="relative -mx-3 -mb-3 mt-12 pt-16 overflow-hidden">
    <div class="absolute inset-0 pointer-events-none overflow-hidden" style="-webkit-mask-image: linear-gradient(to bottom, transparent 0%, black 40%); mask-image: linear-gradient(to bottom, transparent 0%, black 40%);">
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="relative w-full h-full" style="-webkit-mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); mask-image: url('/assets/illustrations/welcome-gradient-mask.svg'); -webkit-mask-size: 1818px 1489.395px; mask-size: 1818px 1489.395px; -webkit-mask-position: center; mask-position: center; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat;">
          <img src="/assets/illustrations/welcome-gradient.png" alt="" class="absolute inset-0 w-full h-full object-cover mix-blend-screen" />
        </div>
      </div>
    </div>
    <div class="relative z-10">
      <CTABanner variant="light" />
    </div>
  </div>
</div>

<style>
  .sk-shimmer {
    background-image: linear-gradient(
      90deg,
      rgba(241, 241, 241, 1) 0%,
      rgba(228, 228, 228, 1) 50%,
      rgba(241, 241, 241, 1) 100%
    );
    background-size: 200% 100%;
    animation: sk-shimmer 1.4s ease-in-out infinite;
  }
  @keyframes sk-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
</style>
