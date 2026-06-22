<script>
  import { onMount } from 'svelte';
  import { replace } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { stewardAPI } from '../lib/api.js';
  import { showError, showSuccess } from '../lib/toastStore';
  import { isSafeHttpUrl } from '../lib/urlSafety.js';

  const scoreLabels = {
    0: "Not interesting",
    1: "Weak",
    2: "Good",
    3: "Strong",
  };

  const anchorExamples = [
    {
      score: 0,
      title: "Generic link dump",
      copy: "A submission that only points to a repo, social post, or landing page without a GenLayer-specific use case or community path.",
    },
    {
      score: 2,
      title: "Internet Court",
      copy: "Clear GenLayer fit and understandable community value, but still needs more polish, distribution, or proof of traction before a hard feature push.",
    },
    {
      score: 3,
      title: "Argue.fun",
      copy: "A strong GenLayer-native use case with a legible product loop, scalable community relevance, and a credible chance of real adoption if promoted.",
    },
  ];

  let access = $state({ can_review: false, can_admin: false });
  let candidates = $state([]);
  let adminRows = $state([]);
  let progress = $state({ scored: 0, total: 0 });
  let loading = $state(true);
  let adminLoading = $state(false);
  let error = $state('');
  let activeTab = $state('review');
  let saving = $state(new Set());

  let scoredPercent = $derived(
    progress.total ? Math.round((progress.scored / progress.total) * 100) : 0
  );
  let visibleCandidates = $derived(
    [...candidates].sort((a, b) => {
      if (a.own_score === null && b.own_score !== null) return -1;
      if (a.own_score !== null && b.own_score === null) return 1;
      return new Date(b.created_at) - new Date(a.created_at);
    })
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

  async function scoreCandidate(candidate, score) {
    saving.add(candidate.id);
    saving = new Set(saving);
    try {
      await stewardAPI.scoreFeatureReviewCandidate(candidate.id, score);
      const wasUnscored = candidate.own_score === null || candidate.own_score === undefined;
      candidates = candidates.map(item =>
        item.id === candidate.id ? { ...item, own_score: score } : item
      );
      if (wasUnscored) {
        progress = { ...progress, scored: progress.scored + 1 };
      }
      showSuccess('Score saved');
    } catch (err) {
      showError(err.response?.data?.detail || err.response?.data?.score || 'Failed to save score.');
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

  function evidenceHref(item) {
    const href = item.url || item.file || '';
    if (isSafeHttpUrl(href)) return href.trim();
    if (typeof href === 'string' && href.startsWith('/')) return href;
    return '';
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

<div class="container mx-auto px-4 py-8">
  <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <p class="text-sm font-medium text-[#19A663]">Stewards</p>
      <h1 class="mt-1 text-2xl font-bold text-gray-950">Feature candidate scoring</h1>
      <p class="mt-2 max-w-3xl text-sm text-gray-600">
        Score interesting submissions independently. You will only see your own progress and your own scores.
      </p>
    </div>

    {#if access.can_review}
      <div class="min-w-[220px] rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
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
          class="rounded-md px-4 py-2 text-sm font-medium {activeTab === 'review' ? 'bg-[#19A663] text-white' : 'text-gray-600 hover:bg-gray-50'}"
        >
          Review
        </button>
        <button
          type="button"
          onclick={() => selectTab('admin')}
          class="rounded-md px-4 py-2 text-sm font-medium {activeTab === 'admin' ? 'bg-[#19A663] text-white' : 'text-gray-600 hover:bg-gray-50'}"
        >
          Admin
        </button>
      </div>
    {/if}

    {#if activeTab === 'review' && access.can_review}
      <div class="mb-6 grid gap-4 lg:grid-cols-[1fr_360px]">
        <div class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 class="text-base font-semibold text-gray-950">Scoring bar</h2>
          <div class="mt-4 grid gap-3 sm:grid-cols-4">
            {#each [0, 1, 2, 3] as score}
              <div class="rounded-md border border-gray-200 p-3">
                <div class="text-lg font-bold text-gray-950">{score}</div>
                <div class="text-sm font-medium text-gray-700">{scoreLabels[score]}</div>
              </div>
            {/each}
          </div>
          <p class="mt-4 text-sm text-gray-600">
            Judge absolute community use: scalability, fit with GenLayer, and realistic traction if pushed to the community.
          </p>
        </div>

        <div class="rounded-lg border border-gray-200 bg-[#f7fbf8] p-5 shadow-sm">
          <h2 class="text-base font-semibold text-gray-950">Anchor examples</h2>
          <div class="mt-3 space-y-3">
            {#each anchorExamples as example}
              <div class="border-l-2 border-[#19A663] pl-3">
                <div class="text-sm font-semibold text-gray-950">{example.score}: {example.title}</div>
                <p class="mt-1 text-xs leading-5 text-gray-600">{example.copy}</p>
              </div>
            {/each}
          </div>
        </div>
      </div>

      {#if visibleCandidates.length === 0}
        <div class="rounded-lg border border-gray-200 bg-white p-8 text-center text-gray-500">
          No interesting submissions are waiting for feature scoring.
        </div>
      {:else}
        <div class="space-y-4">
          {#each visibleCandidates as candidate}
            <article class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    <span class="rounded bg-gray-100 px-2 py-1 font-medium text-gray-700">{candidate.contribution_type_details?.name}</span>
                    <span>{candidate.state}</span>
                    <span>by {displayName(candidate.user_details)}</span>
                  </div>
                  <h3 class="mt-3 text-lg font-semibold text-gray-950">{candidate.title || 'Untitled submission'}</h3>
                  {#if candidate.notes}
                    <p class="mt-2 line-clamp-3 text-sm leading-6 text-gray-600">{candidate.notes}</p>
                  {/if}
                  {#if candidate.evidence_items?.length}
                    <div class="mt-3 flex flex-wrap gap-2">
                      {#each candidate.evidence_items as evidence, index}
                        {#if evidenceHref(evidence)}
                          <a
                            href={evidenceHref(evidence)}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="rounded border border-gray-200 px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:border-[#19A663] hover:text-[#137f4c]"
                          >
                            Evidence {index + 1}
                          </a>
                        {/if}
                      {/each}
                    </div>
                  {/if}
                </div>

                <div class="flex shrink-0 gap-2">
                  {#each [0, 1, 2, 3] as score}
                    <button
                      type="button"
                      disabled={saving.has(candidate.id)}
                      onclick={() => scoreCandidate(candidate, score)}
                      title={scoreLabels[score]}
                      class="h-10 w-10 rounded-md border text-sm font-semibold transition-colors disabled:opacity-60 {candidate.own_score === score ? 'border-[#19A663] bg-[#19A663] text-white' : 'border-gray-200 bg-white text-gray-700 hover:border-[#19A663]'}"
                    >
                      {score}
                    </button>
                  {/each}
                </div>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    {:else if activeTab === 'admin' && access.can_admin}
      <div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {#if adminLoading}
          <div class="flex justify-center p-10">
            <div class="h-8 w-8 animate-spin rounded-full border-b-2 border-primary-600"></div>
          </div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
              <thead class="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <tr>
                  <th class="px-4 py-3">Project</th>
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
                      <div class="font-medium text-gray-950">{row.title || 'Untitled submission'}</div>
                      <div class="mt-1 text-xs text-gray-500">{row.contribution_type_details?.name} · {displayName(row.user_details)}</div>
                    </td>
                    <td class="px-4 py-4 font-semibold text-gray-950">{row.median_score ?? '-'}</td>
                    <td class="px-4 py-4 text-gray-700">{row.reviewer_count}</td>
                    <td class="px-4 py-4 text-gray-700">{row.spread ?? '-'}</td>
                    <td class="px-4 py-4">
                      <span class="rounded-full px-2.5 py-1 text-xs font-semibold {decisionClass(row)}">
                        {decisionLabel(row.decision)}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>
