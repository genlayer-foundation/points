<script>
  import { onMount } from 'svelte';
  import { push, replace } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI } from '../lib/api.js';
  import { showError, showSuccess } from '../lib/toastStore';
  import { isSafeHttpUrl } from '../lib/urlSafety.js';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';

  const TITLE_PREVIEW_LENGTH = 80;
  const DESCRIPTION_PREVIEW_LENGTH = 220;
  const socialIconPaths = {
    GitHub: 'M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2z',
    X: 'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z',
    Discord: 'M20.317 4.37A19.79 19.79 0 0 0 15.366 2.8a.074.074 0 0 0-.079.037c-.213.38-.45.875-.616 1.265a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.626-1.265.077.077 0 0 0-.079-.037 19.74 19.74 0 0 0-4.951 1.57.07.07 0 0 0-.032.026C.533 8.824-.319 13.144.079 17.41a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 6.073 3.075.078.078 0 0 0 .084-.027c.468-.638.885-1.312 1.24-2.02a.076.076 0 0 0-.041-.105 13.1 13.1 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.099.246.198.373.292a.077.077 0 0 1-.007.128 12.3 12.3 0 0 1-1.873.891.077.077 0 0 0-.04.106c.36.707.777 1.381 1.238 2.019a.076.076 0 0 0 .084.028 19.84 19.84 0 0 0 6.082-3.075.077.077 0 0 0 .031-.055c.477-4.932-.8-9.216-3.419-13.015a.061.061 0 0 0-.031-.028ZM8.02 14.801c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.211 0 2.176 1.096 2.157 2.419 0 1.333-.955 2.419-2.157 2.419Zm7.975 0c-1.183 0-2.157-1.086-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.211 0 2.176 1.096 2.157 2.419 0 1.333-.946 2.419-2.157 2.419Z',
  };
  const scoreOptions = [
    {
      value: 0,
      label: 'Not interesting',
      guideClass: 'border-red-200 bg-red-50 text-red-700',
      selectedClass: 'border-red-600 bg-red-600 text-white shadow-sm',
      numberClass: 'bg-red-100 text-red-700',
    },
    {
      value: 1,
      label: 'Weak',
      guideClass: 'border-amber-200 bg-amber-50 text-amber-800',
      selectedClass: 'border-amber-500 bg-amber-500 text-white shadow-sm',
      numberClass: 'bg-amber-100 text-amber-800',
    },
    {
      value: 2,
      label: 'Good',
      guideClass: 'border-blue-200 bg-blue-50 text-blue-800',
      selectedClass: 'border-blue-600 bg-blue-600 text-white shadow-sm',
      numberClass: 'bg-blue-100 text-blue-800',
    },
    {
      value: 3,
      label: 'Strong',
      guideClass: 'border-emerald-200 bg-emerald-50 text-emerald-800',
      selectedClass: 'border-[#19A663] bg-[#19A663] text-white shadow-sm',
      numberClass: 'bg-emerald-100 text-emerald-800',
    },
  ];
  const scoreLabels = Object.fromEntries(scoreOptions.map(option => [option.value, option.label]));

  let access = $state({ can_review: false, can_admin: false });
  let candidates = $state([]);
  let adminRows = $state([]);
  let progress = $state({ scored: 0, total: 0 });
  let loading = $state(true);
  let adminLoading = $state(false);
  let error = $state('');
  let activeTab = $state('review');
  let reviewFilterTab = $state('not_scored');
  let saving = $state(new Set());
  let scoreDrafts = $state({});
  let expandedTitles = $state(new Set());
  let expandedDescriptions = $state(new Set());
  let expandedAdminRows = $state(new Set());

  let scoredPercent = $derived(
    progress.total ? Math.round((progress.scored / progress.total) * 100) : 0
  );
  let visibleCandidates = $derived(
    [...candidates].sort((a, b) => {
      if (a.own_score == null && b.own_score != null) return -1;
      if (a.own_score != null && b.own_score == null) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    })
  );
  let notScoredCount = $derived(candidates.filter(candidate => candidate.own_score == null).length);
  let scoredCount = $derived(candidates.filter(candidate => candidate.own_score != null).length);
  let filteredCandidates = $derived(
    visibleCandidates.filter(candidate =>
      reviewFilterTab === 'scored' ? candidate.own_score != null : candidate.own_score == null
    )
  );

  onMount(async () => {
    if (!$authState.isAuthenticated) {
      replace('/');
      return;
    }
    await loadAccessAndReviewQueue();
  });

  async function loadAccessAndReviewQueue() {
    try {
      loading = true;
      error = '';
      const accessResponse = await stewardAPI.getFeatureReviewAccess();
      access = accessResponse.data || { can_review: false, can_admin: false };
      if (!access.can_review && !access.can_admin) {
        error = 'You do not have access to feature candidate scoring.';
        return;
      }

      if (access.can_review) {
        await loadCandidates();
      } else if (access.can_admin) {
        activeTab = 'admin';
        await loadAdminRows();
      }
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to load feature review access.';
      showError(message);
      error = message;
    } finally {
      loading = false;
    }
  }

  async function loadCandidates() {
    const response = await stewardAPI.getFeatureReviewCandidates();
    candidates = response.data?.results || [];
    progress = response.data?.progress || { scored: 0, total: candidates.length };
    scoreDrafts = Object.fromEntries(
      candidates.map(candidate => [
        candidate.id,
        {
          score: candidate.own_score,
          reason: candidate.own_score_reason || '',
        },
      ])
    );
  }

  async function loadAdminRows() {
    if (!access.can_admin) return;
    try {
      adminLoading = true;
      const response = await stewardAPI.getFeatureReviewAdmin();
      adminRows = response.data?.results || [];
    } catch (err) {
      showError(err.response?.data?.detail || 'Failed to load feature review admin table.');
    } finally {
      adminLoading = false;
    }
  }

  async function selectTab(tab) {
    activeTab = tab;
    if (tab === 'admin' && adminRows.length === 0) {
      await loadAdminRows();
    }
  }

  function draftFor(candidate) {
    return scoreDrafts[candidate.id] || {
      score: candidate.own_score,
      reason: candidate.own_score_reason || '',
    };
  }

  function draftScore(candidate) {
    return draftFor(candidate).score;
  }

  function draftReason(candidate) {
    return draftFor(candidate).reason || '';
  }

  function updateScoreDraft(candidate, patch) {
    scoreDrafts = {
      ...scoreDrafts,
      [candidate.id]: {
        ...draftFor(candidate),
        ...patch,
      },
    };
  }

  async function scoreCandidate(candidate) {
    const draft = draftFor(candidate);
    if (!Number.isInteger(draft.score)) {
      showError('Select a score before saving.');
      return;
    }

    saving.add(candidate.id);
    saving = new Set(saving);
    try {
      const response = await stewardAPI.scoreFeatureReviewCandidate(
        candidate.id,
        draft.score,
        draft.reason || ''
      );
      const savedReason = response.data?.reason ?? draft.reason ?? '';
      const wasUnscored = candidate.own_score === null || candidate.own_score === undefined;
      candidates = candidates.map(item =>
        item.id === candidate.id
          ? { ...item, own_score: draft.score, own_score_reason: savedReason }
          : item
      );
      updateScoreDraft(candidate, { score: draft.score, reason: savedReason });
      if (wasUnscored) {
        progress = { ...progress, scored: progress.scored + 1 };
      }
      showSuccess('Score saved');
    } catch (err) {
      showError(err.response?.data?.detail || err.response?.data?.score || err.response?.data?.reason || 'Failed to save score.');
    } finally {
      saving.delete(candidate.id);
      saving = new Set(saving);
    }
  }

  function displayName(user) {
    if (!user) return 'Unknown';
    if (user.display_name) return user.display_name;
    if (user.name) return user.name;
    if (user.address) return `${user.address.slice(0, 6)}...${user.address.slice(-4)}`;
    return 'Unknown';
  }

  function profileHref(user) {
    return user?.address ? `/participant/${user.address}` : '';
  }

  function goToProfile(user) {
    const href = profileHref(user);
    if (href) push(href);
  }

  function profileInitial(user) {
    return displayName(user).charAt(0).toUpperCase();
  }

  function socialUsername(connection) {
    return connection?.platform_username || connection?.username || connection?.handle || '';
  }

  function socialConnections(user) {
    const github = socialUsername(user?.github_connection).replace(/^@/, '');
    const twitter = socialUsername(user?.twitter_connection).replace(/^@/, '');
    const discord = socialUsername(user?.discord_connection);
    const connections = [];

    if (github) {
      connections.push({
        platform: 'GitHub',
        label: 'GitHub',
        title: `GitHub ${github}`,
        href: `https://github.com/${encodeURIComponent(github)}`,
        className: 'border-gray-200 bg-white text-gray-700 hover:border-gray-400 hover:text-gray-950',
      });
    }
    if (twitter) {
      connections.push({
        platform: 'X',
        label: 'X',
        title: `X ${twitter}`,
        href: `https://x.com/${encodeURIComponent(twitter)}`,
        className: 'border-gray-200 bg-white text-gray-900 hover:border-gray-400',
      });
    }
    if (discord) {
      connections.push({
        platform: 'Discord',
        label: 'Discord',
        title: `Discord ${discord}`,
        href: '',
        className: 'border-gray-200 bg-white text-indigo-600',
      });
    }
    return connections;
  }

  function socialIconPath(platform) {
    return socialIconPaths[platform] || socialIconPaths.Discord;
  }

  function evidenceUrl(item) {
    return item?.url || item?.file || '';
  }

  function evidenceHref(item) {
    const href = evidenceUrl(item);
    if (isSafeHttpUrl(href)) return href.trim();
    if (typeof href === 'string' && href.startsWith('/')) return href;
    return '';
  }

  function evidenceType(item) {
    if (item?.url_type?.name) return item.url_type.name;
    if (item?.file) return 'File';
    return '';
  }

  function headingText(item) {
    const title = item?.title?.trim();
    if (title) return title;
    const notes = item?.notes?.trim();
    if (notes) return notes;
    return 'No description provided';
  }

  function hasExpandableTitle(item) {
    const text = headingText(item);
    return Boolean(text && (text.length > TITLE_PREVIEW_LENGTH || text.includes('\n')));
  }

  function toggleTitle(id) {
    const next = new Set(expandedTitles);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    expandedTitles = next;
  }

  function hasExpandableDescription(text) {
    return Boolean(text && (text.length > DESCRIPTION_PREVIEW_LENGTH || text.includes('\n')));
  }

  function toggleDescription(id) {
    const next = new Set(expandedDescriptions);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    expandedDescriptions = next;
  }

  function toggleAdminRow(id) {
    const next = new Set(expandedAdminRows);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    expandedAdminRows = next;
  }

  function truncateText(text, maxLength = 120) {
    const normalized = String(text || '').replace(/\s+/g, ' ').trim();
    if (!normalized) return '';
    if (normalized.length <= maxLength) return normalized;
    return `${normalized.slice(0, maxLength - 3).trim()}...`;
  }

  function submissionHeading(item) {
    const title = item?.title?.trim();
    if (title) return title;
    const notes = item?.notes?.trim();
    if (notes) return truncateText(notes, 120);
    return 'No description provided';
  }

  function scoreText(score) {
    return score == null ? 'Not scored' : `${score} - ${scoreLabels[score]}`;
  }

  function scoreButtonClass(candidate, option) {
    if (draftScore(candidate) === option.value) return option.selectedClass;
    return `${option.guideClass} hover:border-[#19A663] hover:bg-white hover:text-gray-950`;
  }

  function scoreNumberClass(candidate, option) {
    if (draftScore(candidate) === option.value) return 'bg-white/20 text-current';
    return option.numberClass;
  }

  function scoreValue(value) {
    if (value == null) return '-';
    return Number.isInteger(value) ? value : value.toFixed(1);
  }

  function decisionLabel(decision) {
    if (decision === 'feature') return 'Feature';
    if (decision === 'do_not_feature') return 'Do not feature';
    if (decision === 'manual_review') return 'Manual review';
    return 'Pending';
  }

  function decisionClass(row) {
    if (row.manual_review) return 'bg-amber-100 text-amber-800';
    if (row.decision === 'feature') return 'bg-green-100 text-green-800';
    if (row.decision === 'do_not_feature') return 'bg-gray-100 text-gray-700';
    return 'bg-blue-100 text-blue-700';
  }
</script>

<div class="min-h-full bg-gradient-to-br from-emerald-50 via-white to-white antialiased">
<div class="w-full px-5 py-6 md:px-8 md:py-8">
  <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <div class="flex items-center gap-3">
        <CategoryIcon category="steward" mode="hexagon" size={48} />
        <h1 class="text-2xl font-bold text-gray-950">Feature candidate scoring</h1>
      </div>
      <p class="mt-2 max-w-3xl text-sm text-gray-600">
        Score interesting submissions independently. Progress and saved scores are tracked for your steward account.
      </p>
    </div>

    {#if access.can_review}
      <div class="min-w-[240px] rounded-lg border border-emerald-100 bg-white p-4 shadow-sm">
        <div class="flex items-center justify-between text-sm">
          <span class="font-medium text-gray-700">Progress</span>
          <span class="font-semibold text-gray-950">{progress.scored}/{progress.total}</span>
        </div>
        <div class="mt-3 h-2 rounded-full bg-gray-100">
          <div class="h-2 rounded-full bg-[#19A663]" style="width: {scoredPercent}%"></div>
        </div>
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="flex justify-center p-10">
      <div class="h-10 w-10 animate-spin rounded-full border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
  {:else}
    {#if access.can_review && access.can_admin}
      <div class="mb-5 flex w-fit rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
        <button
          type="button"
          onclick={() => selectTab('review')}
          class="rounded-md px-4 py-2 text-sm font-medium transition-colors {activeTab === 'review' ? 'bg-[#19A663] text-white' : 'text-gray-600 hover:bg-gray-50'}"
        >
          Review
        </button>
        <button
          type="button"
          onclick={() => selectTab('admin')}
          class="rounded-md px-4 py-2 text-sm font-medium transition-colors {activeTab === 'admin' ? 'bg-[#19A663] text-white' : 'text-gray-600 hover:bg-gray-50'}"
        >
          Admin
        </button>
      </div>
    {/if}

    {#if activeTab === 'review' && access.can_review}
      {#if visibleCandidates.length === 0}
        <div class="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500">
          No interesting submissions are waiting for feature scoring.
        </div>
      {:else}
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div class="flex rounded-lg border border-emerald-100 bg-white p-1 shadow-sm">
            <button
              type="button"
              onclick={() => (reviewFilterTab = 'not_scored')}
              class="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors {reviewFilterTab === 'not_scored' ? 'bg-[#19A663] text-white' : 'text-gray-600 hover:bg-emerald-50 hover:text-[#137f4c]'}"
            >
              Not scored
              <span class="rounded-full px-2 py-0.5 text-xs tabular-nums {reviewFilterTab === 'not_scored' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-700'}">
                {notScoredCount}
              </span>
            </button>
            <button
              type="button"
              onclick={() => (reviewFilterTab = 'scored')}
              class="inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors {reviewFilterTab === 'scored' ? 'bg-[#19A663] text-white' : 'text-gray-600 hover:bg-emerald-50 hover:text-[#137f4c]'}"
            >
              Scored
              <span class="rounded-full px-2 py-0.5 text-xs tabular-nums {reviewFilterTab === 'scored' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-700'}">
                {scoredCount}
              </span>
            </button>
          </div>
        </div>

        {#if filteredCandidates.length === 0}
          <div class="rounded-lg border border-emerald-100 bg-white p-8 text-center text-gray-500 shadow-sm">
            {reviewFilterTab === 'scored' ? 'No scored candidates yet.' : 'All visible candidates have been scored.'}
          </div>
        {:else}
          <div class="space-y-3">
          {#each filteredCandidates as candidate}
            <article class="grid gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-colors hover:border-emerald-200 hover:bg-emerald-50/20 xl:grid-cols-[minmax(0,1fr)_220px] xl:items-start">
                  <div class="min-w-0">
                    <div class="flex items-start gap-2">
                      <h3 class="min-w-0 flex-1 whitespace-pre-wrap text-lg font-semibold leading-7 text-gray-950 {expandedTitles.has(candidate.id) ? '' : 'line-clamp-2'}">
                        {headingText(candidate)}
                      </h3>
                      {#if hasExpandableTitle(candidate)}
                        <button
                          type="button"
                          aria-label={expandedTitles.has(candidate.id) ? 'Collapse title' : 'Expand title'}
                          aria-expanded={expandedTitles.has(candidate.id)}
                          onclick={() => toggleTitle(candidate.id)}
	                          class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white text-gray-500 transition-colors hover:border-[#19A663] hover:text-[#137f4c]"
                        >
                          <svg class="h-4 w-4 transition-transform {expandedTitles.has(candidate.id) ? 'rotate-180' : ''}" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                            <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                          </svg>
                        </button>
                      {/if}
                    </div>

                    <div class="mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-600">
                      {#if profileHref(candidate.user_details)}
                        <a
                          href={profileHref(candidate.user_details)}
                          onclick={(event) => { event.preventDefault(); goToProfile(candidate.user_details); }}
                          class="inline-flex items-center gap-2 text-sm font-semibold text-gray-950 transition-colors hover:text-[#137f4c]"
                        >
                          {#if candidate.user_details?.profile_image_url}
                            <img
                              src={candidate.user_details.profile_image_url}
                              alt=""
                              class="h-7 w-7 rounded-full border border-gray-200 object-cover"
                            />
                          {:else}
                            <span class="inline-flex h-7 w-7 items-center justify-center rounded-full border border-gray-200 bg-gray-50 text-xs font-bold text-[#137f4c]">
                              {profileInitial(candidate.user_details)}
                            </span>
                          {/if}
                          <span>{displayName(candidate.user_details)}</span>
                        </a>
                      {:else}
                        <span class="text-sm font-semibold text-gray-950">by {displayName(candidate.user_details)}</span>
                      {/if}
	                      {#each socialConnections(candidate.user_details) as social}
                        {#if social.href}
                          <a
                            href={social.href}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={social.title}
                            title={social.title}
                            class="inline-flex h-8 w-8 items-center justify-center rounded-md border transition-colors {social.className}"
                          >
                            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                              <path d={socialIconPath(social.platform)} />
                            </svg>
                          </a>
                        {:else}
                          <span
                            class="inline-flex h-8 w-8 items-center justify-center rounded-md border {social.className}"
                            aria-label={social.title}
                            title={social.title}
                          >
                            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                              <path d={socialIconPath(social.platform)} />
                            </svg>
	                          </span>
	                        {/if}
	                      {/each}
                      {#if saving.has(candidate.id)}
                        <span class="text-xs font-semibold text-gray-500">Saving...</span>
                      {/if}
	                    </div>

                    {#if candidate.notes}
                      <div class="mt-4 rounded-md border border-emerald-50 bg-emerald-50/40 px-4 py-3">
                        <div class="flex items-start gap-2">
                          <div class="min-w-0 flex-1">
                            <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Description</p>
                            <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-700 {expandedDescriptions.has(candidate.id) ? '' : 'line-clamp-5'}">
                              {candidate.notes}
                            </p>
                          </div>
                        {#if hasExpandableDescription(candidate.notes)}
                          <button
                            type="button"
                            aria-label={expandedDescriptions.has(candidate.id) ? 'Collapse description' : 'Expand description'}
                            aria-expanded={expandedDescriptions.has(candidate.id)}
                            onclick={() => toggleDescription(candidate.id)}
	                            class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-emerald-100 bg-white text-gray-500 transition-colors hover:border-[#19A663] hover:text-[#137f4c]"
                          >
                            <svg class="h-4 w-4 transition-transform {expandedDescriptions.has(candidate.id) ? 'rotate-180' : ''}" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                              <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                            </svg>
                          </button>
                        {/if}
                        </div>
                      </div>
                    {/if}

                    {#if candidate.evidence_items?.length}
                      <div class="mt-4">
                        <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Evidence</p>
                        <ul class="mt-2 divide-y divide-gray-100 rounded-md border border-gray-200 bg-white">
                          {#each candidate.evidence_items as evidence}
                            <li class="p-3">
                              <div class="flex flex-wrap items-center gap-2">
                                {#if evidenceType(evidence)}
                                  <span class="rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                                    {evidenceType(evidence)}
                                  </span>
                                {/if}
	                                {#if evidenceHref(evidence)}
	                                  <a
	                                    href={evidenceHref(evidence)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    class="break-all text-sm font-medium text-blue-700 underline-offset-2 hover:text-blue-900 hover:underline"
                                  >
                                    {evidenceUrl(evidence)}
                                  </a>
	                                {:else}
	                                  <span class="text-sm text-gray-500">No URL provided</span>
	                                {/if}
	                              </div>
                            </li>
                          {/each}
                        </ul>
                      </div>
                    {:else}
                      <p class="mt-4 rounded-md border border-dashed border-gray-200 px-4 py-3 text-sm text-gray-500">
                        No evidence items submitted.
                      </p>
                    {/if}
                  </div>

                  <div class="grid grid-cols-1 gap-3">
                    {#each scoreOptions as option}
                      <button
                        type="button"
                        disabled={saving.has(candidate.id)}
                        onclick={() => updateScoreDraft(candidate, { score: option.value })}
                        title={`${option.value} - ${option.label}`}
                        aria-label={`Score ${option.value} - ${option.label}`}
                        class="flex min-h-16 items-center justify-start gap-3 rounded-md border px-3 py-2 text-left text-xs font-semibold transition-colors active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-60 {scoreButtonClass(candidate, option)}"
                      >
                        <span class="inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold tabular-nums {scoreNumberClass(candidate, option)}">
                          {option.value}
                        </span>
                        <span class="leading-tight">{option.label}</span>
                      </button>
                    {/each}
                    <label class="block">
                      <span class="text-xs font-semibold uppercase tracking-wide text-gray-500">Reason</span>
                      <textarea
                        value={draftReason(candidate)}
                        oninput={(event) => updateScoreDraft(candidate, { reason: event.currentTarget.value })}
                        maxlength="2000"
                        rows="4"
                        placeholder="What stood out in this project for the score?"
                        class="mt-2 min-h-28 w-full resize-y rounded-md border border-gray-200 bg-white px-3 py-2 text-sm leading-5 text-gray-800 shadow-sm outline-none transition-colors placeholder:text-gray-400 focus:border-[#19A663] focus:ring-2 focus:ring-emerald-100"
                      ></textarea>
                    </label>
                    <button
                      type="button"
                      disabled={saving.has(candidate.id) || !Number.isInteger(draftScore(candidate))}
                      onclick={() => scoreCandidate(candidate)}
                      class="inline-flex min-h-11 items-center justify-center rounded-md bg-[#19A663] px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#137f4c] disabled:cursor-not-allowed disabled:bg-gray-300"
                    >
                      {saving.has(candidate.id) ? 'Saving...' : 'Save opinion'}
                    </button>
                  </div>
            </article>
	          {/each}
          </div>
        {/if}
	      {/if}
    {:else if activeTab === 'admin' && access.can_admin}
      <div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {#if adminLoading}
          <div class="flex justify-center p-10">
            <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-primary-600"></div>
          </div>
        {:else if adminRows.length === 0}
          <div class="p-8 text-center text-sm text-gray-500">
            No feature candidates are available.
          </div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th class="px-4 py-3">Submission</th>
                  <th class="px-4 py-3">Median</th>
                  <th class="px-4 py-3">Reviewers</th>
                  <th class="px-4 py-3">Spread</th>
                  <th class="px-4 py-3">Decision</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                {#each adminRows as row}
                  <tr class={row.manual_review || row.is_borderline ? 'bg-amber-50/60' : ''}>
                    <td class="px-4 py-4">
                      <div class="flex items-start gap-3">
                        <button
                          type="button"
                          aria-expanded={expandedAdminRows.has(row.id)}
                          onclick={() => toggleAdminRow(row.id)}
                          class="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white text-gray-500 transition-colors hover:border-[#19A663] hover:text-[#137f4c]"
                        >
                          <span class="text-base leading-none">{expandedAdminRows.has(row.id) ? '-' : '+'}</span>
                        </button>
                        <div class="min-w-[260px]">
                          <div class="font-medium leading-6 text-gray-950">{submissionHeading(row)}</div>
                          <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                            <span>{row.contribution_type_details?.name || 'Contribution'}</span>
                            <span>by {displayName(row.user_details)}</span>
                            {#if profileHref(row.user_details)}
                              <a
                                href={profileHref(row.user_details)}
                                onclick={(event) => { event.preventDefault(); goToProfile(row.user_details); }}
                                class="font-semibold text-[#137f4c] hover:text-[#0f663d]"
                              >
                                Profile
                              </a>
                            {/if}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td class="px-4 py-4 font-semibold text-gray-950">{scoreValue(row.median_score)}</td>
                    <td class="px-4 py-4 text-gray-700">{row.reviewer_count}</td>
                    <td class="px-4 py-4 text-gray-700">{scoreValue(row.spread)}</td>
                    <td class="px-4 py-4">
                      <span class="rounded-full px-2.5 py-1 text-xs font-semibold {decisionClass(row)}">
                        {decisionLabel(row.decision)}
                      </span>
                    </td>
                  </tr>
                  {#if expandedAdminRows.has(row.id)}
                    <tr class="bg-gray-50/70">
                      <td colspan="5" class="px-4 py-4">
                        <div class="grid gap-4 lg:grid-cols-[1fr_320px]">
                          <div class="rounded-lg border border-gray-200 bg-white p-4">
                            <h3 class="text-sm font-semibold text-gray-950">Submission content</h3>
                            {#if row.notes}
                              <p class="mt-3 whitespace-pre-wrap text-sm leading-6 text-gray-700">{row.notes}</p>
                            {:else}
                              <p class="mt-3 text-sm text-gray-500">No description provided.</p>
                            {/if}

                            <div class="mt-4">
                              <p class="text-xs font-semibold uppercase tracking-wide text-gray-500">Evidence</p>
                              {#if row.evidence_items?.length}
                                <ul class="mt-2 divide-y divide-gray-100 rounded-md border border-gray-200">
                                  {#each row.evidence_items as evidence}
                                    <li class="p-3">
                                      <div class="flex flex-wrap items-center gap-2">
                                        {#if evidenceType(evidence)}
                                          <span class="rounded-full border border-blue-100 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
                                            {evidenceType(evidence)}
                                          </span>
                                        {/if}
                                        {#if evidenceHref(evidence)}
                                          <a
                                            href={evidenceHref(evidence)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            class="break-all text-sm font-medium text-blue-700 underline-offset-2 hover:text-blue-900 hover:underline"
                                          >
                                            {evidenceUrl(evidence)}
                                          </a>
                                        {:else}
                                          <span class="text-sm text-gray-500">No URL provided</span>
                                        {/if}
                                      </div>
                                    </li>
                                  {/each}
                                </ul>
                              {:else}
                                <p class="mt-2 text-sm text-gray-500">No evidence items submitted.</p>
                              {/if}
                            </div>
                          </div>

                          <div class="rounded-lg border border-gray-200 bg-white p-4">
                            <h3 class="text-sm font-semibold text-gray-950">Scoring summary</h3>
                            <dl class="mt-3 grid grid-cols-2 gap-3 text-sm">
                              <div class="rounded-md bg-gray-50 p-3">
                                <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Median</dt>
                                <dd class="mt-1 text-lg font-bold text-gray-950">{scoreValue(row.median_score)}</dd>
                              </div>
                              <div class="rounded-md bg-gray-50 p-3">
                                <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Reviewers</dt>
                                <dd class="mt-1 text-lg font-bold text-gray-950">{row.reviewer_count}</dd>
                              </div>
                              <div class="rounded-md bg-gray-50 p-3">
                                <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Spread</dt>
                                <dd class="mt-1 text-lg font-bold text-gray-950">{scoreValue(row.spread)}</dd>
                              </div>
                              <div class="rounded-md bg-gray-50 p-3">
                                <dt class="text-xs font-semibold uppercase tracking-wide text-gray-500">Your score</dt>
                                <dd class="mt-1 text-lg font-bold text-gray-950">{scoreText(row.own_score)}</dd>
                              </div>
                            </dl>
                          </div>
                        </div>
                      </td>
                    </tr>
                  {/if}
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>
</div>
