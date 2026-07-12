<script>
  import Icons from './Icons.svelte';
  import { format } from '../lib/dates.js';
  import { parseUserMarkdown } from '../lib/markdownLoader.js';
  import { stewardAPI } from '../lib/api.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import {
    RUBRIC_EXTRAS,
    RUBRIC_GATE_FAILURES,
    RUBRIC_SECTIONS
  } from '../lib/rubricReview.js';
  import {
    AI_REVIEW_CLAIM_ANCHORS,
    AI_REVIEW_CLAIM_TYPES,
    AI_REVIEW_DECISIONS,
    buildFeedbackPayload,
    initFeedbackState,
    validateFeedbackState
  } from '../lib/aiFeedback.js';

  /**
   * @typedef {Record<string, any>} FeedbackRecord
   * @typedef {ReturnType<typeof initFeedbackState>} FeedbackState
   */
  /** @type {{
   *   submission: Record<string, any>,
   *   aiAnalysis: Record<string, any>,
   *   feedbackRecords?: FeedbackRecord[],
   *   feedbackLoading?: boolean,
   *   feedbackLoaded?: boolean,
   *   feedbackError?: string,
   *   canFileFeedback?: boolean,
   *   currentUserId?: string | number | null,
   *   onRequestFeedback?: (() => any) | null,
   *   onSaved?: ((record: FeedbackRecord) => any) | null
   * }} */
  let {
    submission,
    aiAnalysis,
    feedbackRecords = [],
    feedbackLoading = false,
    feedbackLoaded = false,
    feedbackError = '',
    canFileFeedback = false,
    currentUserId = null,
    onRequestFeedback = null,
    onSaved = null
  } = $props();

  let expanded = $state(false);
  let editing = $state(false);
  let submitting = $state(false);
  let submitRequestId = 0;
  let claimSequence = 0;
  /** @type {Set<string>} */
  let expandedReasons = $state(new Set());
  let activeAnalysisKey = $state('');
  let hydratedKey = $state('');
  /** @type {FeedbackState} */
  let feedbackState = $state({
    reviewProposalId: null,
    aiDecision: '',
    aiScores: {},
    persistedDecisionOverride: '',
    decisionOverride: '',
    gateFailures: [],
    criteria: {},
    errorClaims: []
  });

  let visibleSections = $derived.by(() => {
    const sections = aiAnalysis?.sections || {};
    return RUBRIC_SECTIONS
      .filter(section => section.key !== 'frontend_ux' && sections[section.key])
      .map(section => ({
        ...section,
        score: sections[section.key]?.score,
        reason: sections[section.key]?.reason || ''
      }));
  });
  let proposalRecords = $derived.by(() => {
    if (aiAnalysis?.id === null || aiAnalysis?.id === undefined) return [];
    return (feedbackRecords || []).filter(record =>
      String(record.review_proposal_id) === String(aiAnalysis.id)
    );
  });
  let feedbackCount = $derived.by(() => {
    const reviewers = new Set(
      proposalRecords.map(record => record.reviewer_id ?? `record-${record.id}`)
    );
    return reviewers.size;
  });
  let currentRecord = $derived.by(() => {
    if (currentUserId === null || currentUserId === undefined) return null;
    return proposalRecords.find(record => String(record.reviewer_id) === String(currentUserId)) || null;
  });
  let aiGateFailures = $derived.by(() => {
    const failures = new Set(aiAnalysis?.gate_failures || []);
    return RUBRIC_GATE_FAILURES.filter(gate => failures.has(gate.key));
  });
  let aiExtras = $derived.by(() => {
    const extras = new Set(aiAnalysis?.extras || []);
    return RUBRIC_EXTRAS.filter(extra => extras.has(extra.key));
  });
  let feedbackEditable = $derived(
    canFileFeedback && feedbackLoaded && !feedbackLoading && !submitting && (!currentRecord || editing)
  );
  let feedbackPayload = $derived.by(() => buildFeedbackPayload(feedbackState));
  let savedPayload = $derived.by(() => currentRecord
    ? buildFeedbackPayload(initFeedbackState(aiAnalysis, currentRecord))
    : null
  );
  let draftDiffersFromSaved = $derived(
    Boolean(savedPayload && JSON.stringify(savedPayload) !== JSON.stringify(feedbackPayload))
  );
  let hasDraftFeedback = $derived.by(() => Boolean(
    feedbackState.decisionOverride ||
    Object.values(feedbackState.criteria || {}).some(criterion => criterion?.overridden) ||
    (feedbackState.errorClaims || []).length > 0
  ));
  let showFeedbackFooter = $derived(
    (feedbackEditable || submitting) && (
      hasDraftFeedback ||
      (editing && draftDiffersFromSaved)
    )
  );
  let hiddenCriterion = $derived(feedbackState.criteria?.frontend_ux || null);
  let hasAdditionalFeedback = $derived(
    Boolean(hiddenCriterion?.overridden || claimsForAnchor('frontend_ux').length || claimsForAnchor('').length)
  );

  $effect(() => {
    const analysisKey = `${submission?.id ?? 'none'}:${aiAnalysis?.id ?? 'none'}`;
    if (analysisKey !== activeAnalysisKey) {
      activeAnalysisKey = analysisKey;
      submitRequestId += 1;
      submitting = false;
      expanded = false;
      editing = false;
      expandedReasons = new Set();
      feedbackState = initFeedbackState(aiAnalysis);
      hydratedKey = '';
    }

    const key = `${aiAnalysis?.id ?? 'none'}:${currentRecord?.id ?? 'none'}:${currentRecord?.updated_at ?? ''}`;
    if (!editing && key !== hydratedKey) {
      feedbackState = initFeedbackState(aiAnalysis, currentRecord);
      hydratedKey = key;
    }
  });

  /** @param {string | null | undefined} dateString */
  function formatDate(dateString) {
    if (!dateString) return '';
    return format(new Date(dateString), 'MMM d, yyyy HH:mm');
  }

  /** @param {string | null | undefined} key */
  function decisionLabel(key) {
    return AI_REVIEW_DECISIONS.find(decision => decision.key === key)?.label || key || 'Not provided';
  }

  /** @param {string} key */
  function claimTypeLabel(key) {
    return AI_REVIEW_CLAIM_TYPES.find(claimType => claimType.key === key)?.label || key;
  }

  /** @param {string} key */
  function anchorLabel(key) {
    if (!key) return 'General feedback';
    return AI_REVIEW_CLAIM_ANCHORS.find(anchor => anchor.key === key)?.label || key;
  }

  /** @param {string | null | undefined} key */
  function decisionTone(key) {
    if (key === 'accept') return 'bg-emerald-100 text-emerald-800 ring-emerald-200';
    if (key === 'reject') return 'bg-red-100 text-red-800 ring-red-200';
    if (key === 'more_info') return 'bg-blue-100 text-blue-800 ring-blue-200';
    return 'bg-slate-100 text-slate-700 ring-slate-200';
  }

  /** @param {string} verdict */
  function verdictPresentation(verdict) {
    if (verdict === 'agree') {
      return { label: 'Accurate', classes: 'bg-emerald-100 text-emerald-800 ring-emerald-200' };
    }
    if (verdict === 'disagree') {
      return { label: 'Disagrees', classes: 'bg-red-100 text-red-800 ring-red-200' };
    }
    return { label: 'Corrected', classes: 'bg-amber-100 text-amber-800 ring-amber-200' };
  }

  /** @param {{ overridden?: boolean, min?: number | null, max?: number | null } | null | undefined} value */
  function scoreRangeLabel(value) {
    if (!value?.overridden) return '';
    return value.min === value.max ? `${value.min}/5` : `${value.min}-${value.max}/5`;
  }

  /** @param {string} anchor */
  function claimsForAnchor(anchor) {
    return (feedbackState.errorClaims || []).filter(claim => (claim.anchor || '') === anchor);
  }

  function toggleExpanded() {
    expanded = !expanded;
    if (expanded && !feedbackLoaded && !feedbackLoading && onRequestFeedback) {
      onRequestFeedback();
    }
  }

  function requestFeedback() {
    if (!feedbackLoading && onRequestFeedback) onRequestFeedback();
  }

  /** @param {string} key */
  function toggleReason(key) {
    const next = new Set(expandedReasons);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    expandedReasons = next;
  }

  function startEditing() {
    feedbackState = initFeedbackState(aiAnalysis, currentRecord);
    hydratedKey = `${aiAnalysis?.id ?? 'none'}:${currentRecord?.id ?? 'none'}:${currentRecord?.updated_at ?? ''}`;
    editing = true;
    expanded = true;
  }

  function cancelEditing() {
    feedbackState = initFeedbackState(aiAnalysis, currentRecord);
    editing = false;
  }

  function resetFeedback() {
    feedbackState = initFeedbackState(aiAnalysis, currentRecord);
  }

  /** @param {string} value */
  function setDecisionOverride(value) {
    feedbackState.persistedDecisionOverride = '';
    feedbackState.decisionOverride = value;
    if (value !== 'reject') feedbackState.gateFailures = [];
  }

  /** @param {string} key */
  function toggleGateFailure(key) {
    const selected = new Set(feedbackState.gateFailures || []);
    if (selected.has(key)) selected.delete(key);
    else selected.add(key);
    feedbackState.gateFailures = [...selected];
  }

  /** @param {string} key @param {string} rawValue */
  function setCriterionOverride(key, rawValue) {
    if (!feedbackState.criteria[key]) {
      feedbackState.criteria[key] = { overridden: false, min: null, max: null, reason: '', persisted: false };
    }
    if (rawValue === '') {
      feedbackState.criteria[key] = { overridden: false, min: null, max: null, reason: '', persisted: false };
      return;
    }
    const score = Number(rawValue);
    feedbackState.criteria[key] = {
      ...feedbackState.criteria[key],
      overridden: true,
      min: score,
      max: score,
      persisted: false
    };
  }

  /** @param {string} key @param {string} rawValue */
  function setCriterionMaximum(key, rawValue) {
    feedbackState.criteria[key].max = Number(rawValue);
    feedbackState.criteria[key].persisted = false;
  }

  /** @param {string} key @param {string} value */
  function setCriterionReason(key, value) {
    feedbackState.criteria[key].reason = value;
  }

  /** @param {string} anchor */
  function addClaim(anchor) {
    claimSequence += 1;
    feedbackState.errorClaims.push({
      clientId: `new-${claimSequence}`,
      type: 'factual_error',
      text: '',
      evidenceRef: '',
      anchor
    });
    if (anchor) {
      const next = new Set(expandedReasons);
      next.add(anchor);
      expandedReasons = next;
    }
  }

  /** @param {string} clientId @param {'type' | 'text' | 'evidenceRef'} field @param {string} value */
  function updateClaim(clientId, field, value) {
    const claim = feedbackState.errorClaims.find(item => item.clientId === clientId);
    if (claim) claim[field] = value;
  }

  /** @param {string} clientId */
  function removeClaim(clientId) {
    feedbackState.errorClaims = feedbackState.errorClaims.filter(claim => claim.clientId !== clientId);
  }

  /** @param {any} error */
  function errorMessage(error) {
    const data = error?.response?.data;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data === 'string') return data;
    if (data && typeof data === 'object') {
      const first = Object.values(data)[0];
      if (Array.isArray(first) && first[0]) return String(first[0]);
      if (typeof first === 'string') return first;
    }
    return error?.message || 'Unknown error';
  }

  /** @param {ReturnType<typeof buildFeedbackPayload>} payload @param {string} successMessage */
  async function submit(payload, successMessage) {
    if (submitting) return;
    const contextKey = `${submission.id}:${aiAnalysis?.id ?? 'none'}`;
    const requestId = ++submitRequestId;
    const isCurrentRequest = () => (
      requestId === submitRequestId &&
      `${submission.id}:${aiAnalysis?.id ?? 'none'}` === contextKey
    );
    submitting = true;
    try {
      const response = await stewardAPI.submitAIFeedback(submission.id, payload);
      if (!isCurrentRequest()) return;
      const record = response.data;
      if (onSaved) await onSaved(record);
      if (!isCurrentRequest()) return;
      feedbackState = initFeedbackState(aiAnalysis, record);
      editing = false;
      showSuccess(successMessage);
    } catch (error) {
      if (!isCurrentRequest()) return;
      showError(`Failed to save AI review feedback: ${errorMessage(error)}`);
    } finally {
      if (isCurrentRequest()) submitting = false;
    }
  }

  async function markAccurate() {
    await submit(
      {
        verdict: 'agree',
        ...(aiAnalysis?.id !== null && aiAnalysis?.id !== undefined
          ? { review_proposal_id: aiAnalysis.id }
          : {})
      },
      'AI review marked accurate'
    );
  }

  async function saveFeedback() {
    const validationError = validateFeedbackState(feedbackState);
    if (validationError) {
      showError(validationError);
      return;
    }
    await submit(buildFeedbackPayload(feedbackState), 'AI review feedback saved');
  }
</script>

{#snippet claimRows(anchor = '')}
  {@const claims = claimsForAnchor(anchor)}
  {#if claims.length > 0}
    <div class="mt-3 space-y-2">
      {#each claims as claim (claim.clientId)}
        {#if feedbackEditable}
          <div class="rounded-md bg-amber-50/80 p-3 ring-1 ring-amber-200">
            <div class="flex items-start gap-2">
              <label class="min-w-0 flex-1 text-xs font-semibold text-amber-950">
                Flaw type
                <select
                  onchange={(event) => updateClaim(claim.clientId, 'type', event.currentTarget.value)}
                  class="mt-1 min-h-10 w-full rounded-md border border-amber-200 bg-white px-2.5 text-sm text-slate-800 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
                  aria-label="Flaw type for {anchorLabel(anchor)}"
                >
                  {#each AI_REVIEW_CLAIM_TYPES as claimType}
                    <option value={claimType.key} selected={claimType.key === claim.type}>{claimType.label}</option>
                  {/each}
                </select>
              </label>
              <button
                type="button"
                onclick={() => removeClaim(claim.clientId)}
                class="mt-4 inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md text-xl leading-none text-amber-700 hover:bg-amber-100 active:scale-[0.96]"
                aria-label="Remove flagged flaw"
                title="Remove flagged flaw"
              >
                &times;
              </button>
            </div>
            <label class="mt-2 block text-xs font-semibold text-amber-950">
              What is wrong
              <textarea
                value={claim.text}
                oninput={(event) => updateClaim(claim.clientId, 'text', event.currentTarget.value)}
                rows="2"
                maxlength="500"
                placeholder="Describe the flaw in one sentence."
                class="mt-1 w-full resize-y rounded-md border border-amber-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
                aria-label="Flaw description for {anchorLabel(anchor)}"
              ></textarea>
            </label>
            <label class="mt-2 block text-xs font-semibold text-amber-950">
              Evidence reference <span class="font-normal text-amber-700">(optional)</span>
              <input
                type="text"
                value={claim.evidenceRef}
                oninput={(event) => updateClaim(claim.clientId, 'evidenceRef', event.currentTarget.value)}
                maxlength="300"
                placeholder="contracts/File.py:method"
                class="mt-1 min-h-10 w-full rounded-md border border-amber-200 bg-white px-3 text-sm text-slate-800 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
                aria-label="Evidence reference for {anchorLabel(anchor)}"
              />
            </label>
            {#if !claim.evidenceRef.trim()}
              <p class="mt-1.5 text-xs text-amber-700">A code reference makes this easier to verify, but is not required.</p>
            {/if}
          </div>
        {:else}
          <div class="rounded-md bg-amber-50/80 px-3 py-2 ring-1 ring-amber-200">
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-amber-800 ring-1 ring-amber-200">
                {claimTypeLabel(claim.type)}
              </span>
              {#if claim.evidenceRef}
                <code class="break-all text-xs text-amber-800">{claim.evidenceRef}</code>
              {/if}
            </div>
            <p class="mt-1.5 whitespace-pre-wrap text-sm text-amber-950">{claim.text}</p>
          </div>
        {/if}
      {/each}
    </div>
  {/if}
{/snippet}

<section class="overflow-hidden rounded-lg border border-sky-200 bg-sky-50/70">
  <div class="flex flex-col sm:flex-row sm:items-center">
    <button
      type="button"
      onclick={toggleExpanded}
      class="flex min-h-12 min-w-0 flex-1 items-center justify-between gap-3 px-3 py-2 text-left hover:bg-sky-100/50 active:bg-sky-100"
      aria-expanded={expanded}
      aria-controls="ai-review-analysis-{submission.id}"
      aria-label="{expanded ? 'Hide' : 'Show'} AI review analysis"
    >
      <span class="flex min-w-0 items-center gap-2">
        <span class="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-sky-100 text-sky-700">
          <Icons name="sparkle" size="sm" />
        </span>
        <span class="min-w-0">
          <span class="block text-sm font-semibold text-sky-950">AI review analysis</span>
          {#if aiAnalysis?.created_at}
            <span class="block truncate text-xs text-sky-700">{formatDate(aiAnalysis.created_at)}</span>
          {/if}
        </span>
      </span>
      <span class="flex flex-shrink-0 items-center gap-2">
        {#if aiAnalysis?.confidence}
          <span class="rounded-full bg-white px-2 py-0.5 text-xs font-semibold capitalize text-sky-800 ring-1 ring-sky-200">
            {aiAnalysis.confidence}
          </span>
        {/if}
        <Icons name="chevronDown" size="sm" className="text-sky-700 transition-transform {expanded ? 'rotate-180' : ''}" />
      </span>
    </button>

    {#if feedbackLoaded && !feedbackLoading && (currentRecord || canFileFeedback || feedbackCount > 0)}
      <div class="flex min-h-12 flex-wrap items-center gap-2 border-t border-sky-200 px-3 py-1.5 sm:border-l sm:border-t-0">
        {#if currentRecord}
          {@const verdict = verdictPresentation(currentRecord.verdict)}
          <span class="rounded-full px-2.5 py-1 text-xs font-semibold ring-1 {verdict.classes}">
            {verdict.label}
          </span>
          {#if canFileFeedback}
            <button
              type="button"
              onclick={editing ? cancelEditing : startEditing}
              disabled={submitting}
              class="min-h-10 rounded-md px-2.5 text-xs font-semibold text-sky-800 hover:bg-sky-100 active:scale-[0.96] disabled:opacity-50"
            >
              {editing ? 'Cancel edit' : 'Edit'}
            </button>
          {/if}
        {:else if canFileFeedback && !hasDraftFeedback}
          <button
            type="button"
            onclick={markAccurate}
            disabled={submitting}
            class="inline-flex min-h-10 items-center gap-1.5 rounded-md bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-700 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {#if submitting}<span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>{/if}
            Accurate
          </button>
        {/if}
        {#if feedbackCount > 0}
          <span class="whitespace-nowrap text-xs text-sky-700">
            {feedbackCount} steward{feedbackCount === 1 ? '' : 's'} filed feedback
          </span>
        {/if}
      </div>
    {/if}
  </div>

  {#if expanded}
    <div id="ai-review-analysis-{submission.id}" class="border-t border-sky-200">
      {#if feedbackLoading}
        <div class="flex min-h-10 items-center gap-2 px-3 text-xs text-sky-700" role="status">
          <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-sky-300 border-t-sky-700"></span>
          Loading steward feedback...
        </div>
      {:else if feedbackError && !feedbackLoaded}
        <div class="flex flex-wrap items-center justify-between gap-2 bg-red-50 px-3 py-2 text-xs text-red-800" role="alert">
          <span>{feedbackError}</span>
          <button type="button" onclick={requestFeedback} class="min-h-10 rounded-md px-3 font-semibold hover:bg-red-100 active:scale-[0.96]">
            Retry
          </button>
        </div>
      {/if}

      <div class="divide-y divide-sky-200/80">
        <div class="px-3 py-3">
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-semibold uppercase text-sky-800">Decision</span>
            <span class="rounded-full px-2.5 py-1 text-xs font-semibold ring-1 {decisionTone(aiAnalysis?.action)}">
              AI: {decisionLabel(aiAnalysis?.action)}
            </span>
            {#if currentRecord?.correct_decision && !feedbackEditable}
              <span class="rounded-full px-2.5 py-1 text-xs font-semibold ring-1 {decisionTone(currentRecord.correct_decision)}">
                You: {decisionLabel(currentRecord.correct_decision)}
              </span>
            {/if}
            {#if feedbackEditable}
              <label class="min-w-[12rem] flex-1 sm:max-w-[15rem]">
                <span class="sr-only">Override AI decision</span>
                <select
                  onchange={(event) => setDecisionOverride(event.currentTarget.value)}
                  class="min-h-10 w-full rounded-md border border-sky-200 bg-white px-2.5 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                  aria-label="Override AI decision"
                >
                  <option value="" selected={!feedbackState.decisionOverride}>Agree with decision</option>
                  {#each AI_REVIEW_DECISIONS.filter(decision =>
                    decision.key !== aiAnalysis?.action ||
                    decision.key === feedbackState.persistedDecisionOverride
                  ) as decision}
                    <option value={decision.key} selected={decision.key === feedbackState.decisionOverride}>{decision.label}</option>
                  {/each}
                </select>
              </label>
            {/if}
          </div>

          {#if feedbackEditable && feedbackState.decisionOverride === 'reject'}
            <fieldset class="mt-3">
              <legend class="mb-2 text-xs font-semibold text-red-800">Gate failures</legend>
              <div class="grid gap-2 sm:grid-cols-2">
                {#each RUBRIC_GATE_FAILURES as gate}
                  <label class="flex min-h-10 cursor-pointer items-center gap-2 rounded-md bg-white px-3 py-2 text-xs font-medium text-slate-700 ring-1 ring-red-200 hover:bg-red-50">
                    <input
                      type="checkbox"
                      checked={feedbackState.gateFailures.includes(gate.key)}
                      onchange={() => toggleGateFailure(gate.key)}
                      class="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                    />
                    <span>{gate.label}</span>
                  </label>
                {/each}
              </div>
            </fieldset>
          {:else if currentRecord?.correct_decision === 'reject' && currentRecord.gate_failures?.length && !feedbackEditable}
            <div class="mt-2 flex flex-wrap gap-1.5">
              {#each RUBRIC_GATE_FAILURES.filter(gate => currentRecord.gate_failures.includes(gate.key)) as gate}
                <span class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">{gate.label}</span>
              {/each}
            </div>
          {/if}
        </div>

        {#each visibleSections as section}
          {@const criterionState = feedbackState.criteria?.[section.key]}
          {@const reasonExpanded = expandedReasons.has(section.key)}
          <section class="px-3 py-3" aria-labelledby="ai-criterion-{submission.id}-{section.key}">
            <div class="flex flex-wrap items-center gap-2">
              <h4 id="ai-criterion-{submission.id}-{section.key}" class="mr-auto text-sm font-semibold text-sky-950">
                {section.label}
              </h4>
              <span class="rounded-full bg-white px-2.5 py-1 text-xs font-bold tabular-nums text-sky-900 ring-1 ring-sky-200">
                AI: {section.score}/5
              </span>
              {#if criterionState?.overridden && !feedbackEditable}
                <span class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold tabular-nums text-amber-800 ring-1 ring-amber-200">
                  You: {scoreRangeLabel(criterionState)}
                </span>
              {/if}
              {#if feedbackEditable}
                <label>
                  <span class="sr-only">Override {section.label} score</span>
                  <select
                    onchange={(event) => setCriterionOverride(section.key, event.currentTarget.value)}
                    class="min-h-10 rounded-md border border-sky-200 bg-white px-2 text-xs font-semibold text-slate-700 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    aria-label="Override {section.label} score"
                  >
                    <option value="" selected={!criterionState?.overridden}>Agree</option>
                    {#each [0, 1, 2, 3, 4, 5] as score}
                      <option value={score} selected={criterionState?.overridden && score === criterionState.min}>
                        {score}/5{score === Number(section.score) ? ' (AI score; widen range)' : ''}
                      </option>
                    {/each}
                  </select>
                </label>
              {/if}
            </div>

            <div class="mt-2 min-w-0 rounded-md bg-white/75 px-3 py-2 ring-1 ring-sky-100">
              {#if section.reason}
                <div
                  id="ai-reason-{submission.id}-{section.key}"
                  class="markdown-content min-w-0 break-words text-sm text-sky-950 {reasonExpanded ? '' : 'line-clamp-3'}"
                >
                  {@html parseUserMarkdown(section.reason)}
                </div>
              {:else}
                <p id="ai-reason-{submission.id}-{section.key}" class="break-words text-sm italic text-sky-700">No criterion reason provided.</p>
              {/if}
              <div class="mt-1.5 flex flex-wrap items-center justify-end gap-1">
                {#if section.reason}
                  <button
                    type="button"
                    onclick={() => toggleReason(section.key)}
                    class="inline-flex min-h-10 items-center gap-1 rounded-md px-2 text-xs font-semibold text-sky-700 hover:bg-sky-100 active:scale-[0.96]"
                    aria-expanded={reasonExpanded}
                    aria-controls="ai-reason-{submission.id}-{section.key}"
                  >
                    {reasonExpanded ? 'Show less' : 'Show full reasoning'}
                    <Icons name="chevronDown" size="xs" className="transition-transform {reasonExpanded ? 'rotate-180' : ''}" />
                  </button>
                {/if}
                {#if feedbackEditable}
                  <button
                    type="button"
                    onclick={() => addClaim(section.key)}
                    class="min-h-10 rounded-md px-2 text-xs font-semibold text-amber-700 hover:bg-amber-50 active:scale-[0.96]"
                  >
                    Flag flaw
                  </button>
                {/if}
              </div>
            </div>

            {#if feedbackEditable && criterionState?.overridden}
              <div class="mt-2 grid gap-2 sm:grid-cols-[auto_1fr]">
                <label class="flex min-h-10 items-center gap-2 text-xs font-semibold text-sky-900">
                  <span>Range to</span>
                  <select
                    onchange={(event) => setCriterionMaximum(section.key, event.currentTarget.value)}
                    class="min-h-10 rounded-md border border-sky-200 bg-white px-2 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    aria-label="Maximum {section.label} score"
                  >
                    {#each [0, 1, 2, 3, 4, 5].filter(score => score >= (criterionState.min ?? 0)) as score}
                      <option value={score} selected={score === criterionState.max}>{score}/5</option>
                    {/each}
                  </select>
                </label>
                <label>
                  <span class="sr-only">Reason for {section.label} score correction</span>
                  <input
                    type="text"
                    value={criterionState.reason}
                    oninput={(event) => setCriterionReason(section.key, event.currentTarget.value)}
                    maxlength="500"
                    placeholder="Why should this score change?"
                    class="min-h-10 w-full rounded-md border border-sky-200 bg-white px-3 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    aria-label="Reason for {section.label} score correction"
                  />
                </label>
              </div>
            {:else if criterionState?.overridden && criterionState.reason}
              <p class="mt-2 text-xs text-amber-800">{criterionState.reason}</p>
            {/if}

            {@render claimRows(section.key)}
          </section>
        {/each}

        {#if aiGateFailures.length > 0 || aiExtras.length > 0}
          <div class="grid gap-3 px-3 py-3 sm:grid-cols-2">
            {#if aiGateFailures.length > 0}
              <div>
                <p class="mb-1.5 text-xs font-semibold uppercase text-red-800">AI gate failures</p>
                <div class="flex flex-wrap gap-1.5">
                  {#each aiGateFailures as gate}
                    <span class="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 ring-1 ring-red-200">{gate.label}</span>
                  {/each}
                </div>
              </div>
            {/if}
            {#if aiExtras.length > 0}
              <div>
                <p class="mb-1.5 text-xs font-semibold uppercase text-emerald-800">Verified extras</p>
                <div class="flex flex-wrap gap-1.5">
                  {#each aiExtras as extra}
                    <span class="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-800 ring-1 ring-emerald-200">{extra.label}</span>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        {/if}

        <section class="px-3 py-3" aria-labelledby="ai-synthesis-{submission.id}">
          <div class="flex flex-wrap items-center gap-2">
            <h4 id="ai-synthesis-{submission.id}" class="mr-auto text-sm font-semibold text-sky-950">Synthesis</h4>
            {#if feedbackEditable}
              <button
                type="button"
                onclick={() => addClaim('synthesis')}
                class="min-h-10 rounded-md px-2 text-xs font-semibold text-amber-700 hover:bg-amber-50 active:scale-[0.96]"
              >
                Flag flaw
              </button>
            {/if}
          </div>
          <div class="mt-1 min-w-0 rounded-md bg-white/75 px-3 py-2 ring-1 ring-sky-100">
            {#if aiAnalysis?.synthesis}
              <div
                id="ai-synthesis-reason-{submission.id}"
                class="markdown-content min-w-0 break-words text-sm text-sky-950 {expandedReasons.has('synthesis') ? '' : 'line-clamp-3'}"
              >
                {@html parseUserMarkdown(aiAnalysis.synthesis)}
              </div>
            {:else if aiAnalysis?.overall_reason}
              <p
                id="ai-synthesis-reason-{submission.id}"
                class="break-words whitespace-pre-wrap text-sm text-sky-950 {expandedReasons.has('synthesis') ? '' : 'line-clamp-3'}"
              >
                {aiAnalysis.overall_reason}
              </p>
            {:else}
              <p class="text-sm italic text-sky-700">No synthesis provided.</p>
            {/if}
            {#if aiAnalysis?.synthesis || aiAnalysis?.overall_reason}
              <div class="mt-1 flex justify-end">
                <button
                  type="button"
                  onclick={() => toggleReason('synthesis')}
                  class="inline-flex min-h-10 items-center gap-1 rounded-md px-2 text-xs font-semibold text-sky-700 hover:bg-sky-100 active:scale-[0.96]"
                  aria-expanded={expandedReasons.has('synthesis')}
                  aria-controls="ai-synthesis-reason-{submission.id}"
                >
                  {expandedReasons.has('synthesis') ? 'Show less' : 'Show full synthesis'}
                  <Icons name="chevronDown" size="xs" className="transition-transform {expandedReasons.has('synthesis') ? 'rotate-180' : ''}" />
                </button>
              </div>
            {/if}
          </div>
          {@render claimRows('synthesis')}
        </section>

        {#if hasAdditionalFeedback}
          <section class="px-3 py-3" aria-label="Additional saved feedback">
            <h4 class="text-xs font-semibold uppercase text-slate-600">Additional saved feedback</h4>
            {#if hiddenCriterion?.overridden}
              <div class="mt-2 rounded-md bg-white px-3 py-2 ring-1 ring-slate-200">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-sm font-semibold text-slate-800">Frontend / UX</span>
                  <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">You: {scoreRangeLabel(hiddenCriterion)}</span>
                </div>
                {#if hiddenCriterion.reason}<p class="mt-1 text-xs text-slate-600">{hiddenCriterion.reason}</p>{/if}
              </div>
            {/if}
            {@render claimRows('frontend_ux')}
            {@render claimRows('')}
          </section>
        {/if}
      </div>

      {#if showFeedbackFooter}
        <div class="flex flex-wrap items-center justify-between gap-2 border-t border-sky-200 bg-white/85 px-3 py-2">
          <button
            type="button"
            onclick={resetFeedback}
            disabled={submitting}
            class="min-h-10 rounded-md px-3 text-sm font-medium text-slate-600 hover:bg-slate-100 active:scale-[0.96] disabled:opacity-50"
          >
            Reset
          </button>
          <button
            type="button"
            onclick={saveFeedback}
            disabled={submitting}
            class="inline-flex min-h-10 items-center gap-2 rounded-md bg-sky-700 px-4 text-sm font-semibold text-white hover:bg-sky-800 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {#if submitting}<span class="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>{/if}
            {submitting ? 'Saving feedback...' : 'Save feedback'}
          </button>
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .markdown-content {
    overflow-wrap: anywhere;
  }

  .markdown-content :global(pre) {
    max-width: 100%;
    overflow-x: auto;
    white-space: pre;
  }

  .markdown-content :global(pre code) {
    overflow-wrap: normal;
    word-break: normal;
  }
</style>
