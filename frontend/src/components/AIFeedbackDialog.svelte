<script>
  import { tick } from 'svelte';
  import Icons from './Icons.svelte';
  import { stewardAPI } from '../lib/api.js';
  import { parseUserMarkdown } from '../lib/markdownLoader.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import { RUBRIC_GATE_FAILURES, RUBRIC_SECTIONS } from '../lib/rubricReview.js';
  import {
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
   *   open?: boolean,
   *   anchor?: string,
   *   submission: Record<string, any>,
   *   aiAnalysis: Record<string, any>,
   *   feedbackRecords?: FeedbackRecord[],
   *   feedbackLoading?: boolean,
   *   feedbackLoaded?: boolean,
   *   feedbackError?: string,
   *   canFileFeedback?: boolean,
   *   currentUserId?: string | number | null,
   *   onRequestFeedback?: ((force?: boolean) => any) | null,
   *   onSaved?: ((record: FeedbackRecord) => any) | null,
   *   onClose?: (() => void) | null
   * }} */
  let {
    open = false,
    anchor = 'decision',
    submission,
    aiAnalysis,
    feedbackRecords = [],
    feedbackLoading = false,
    feedbackLoaded = false,
    feedbackError = '',
    canFileFeedback = false,
    currentUserId = null,
    onRequestFeedback = null,
    onSaved = null,
    onClose = null
  } = $props();

  /** @type {HTMLElement | null} */
  let dialogPanel = $state(null);
  /** @type {FeedbackRecord[]} */
  let loadedRecords = $state([]);
  /** @type {FeedbackRecord | null} */
  let conflictRecord = $state(null);
  /** @type {FeedbackState} */
  let feedbackState = $state(initFeedbackState());
  let ready = $state(false);
  let localLoading = $state(false);
  let localLoadError = $state('');
  let submitting = $state(false);
  let cycleKey = $state('');
  let requestSequence = 0;
  let claimSequence = 0;

  let activeSection = $derived(
    RUBRIC_SECTIONS.find(section => section.key === anchor) || null
  );
  let isDecision = $derived(anchor === 'decision');
  let isSynthesis = $derived(anchor === 'synthesis');
  let activeAnalysisSection = $derived(activeSection ? aiAnalysis?.sections?.[activeSection.key] : null);
  let synthesisContent = $derived(aiAnalysis?.synthesis || aiAnalysis?.overall_reason || '');
  let currentRecord = $derived.by(() => {
    if (currentUserId === null || currentUserId === undefined) return null;
    return loadedRecords.find(record => (
      String(record.review_proposal_id) === String(aiAnalysis?.id) &&
      String(record.reviewer_id) === String(currentUserId)
    )) || null;
  });
  let feedbackPayload = $derived.by(() => buildFeedbackPayload(feedbackState));
  let savedPayload = $derived.by(() => (
    currentRecord ? buildFeedbackPayload(initFeedbackState(aiAnalysis, currentRecord)) : null
  ));
  let draftDiffersFromSaved = $derived(
    Boolean(savedPayload && JSON.stringify(savedPayload) !== JSON.stringify(feedbackPayload))
  );
  let hasNewFeedback = $derived(feedbackPayload.verdict !== 'agree');
  let canSave = $derived(
    canFileFeedback &&
    ready &&
    !localLoading &&
    !feedbackLoading &&
    !submitting &&
    !conflictRecord &&
    (currentRecord ? draftDiffersFromSaved : hasNewFeedback)
  );
  let dialogTitle = $derived(
    isDecision
      ? 'Review AI decision'
      : isSynthesis
        ? 'Review AI synthesis'
        : `Review ${activeSection?.label || 'AI criterion'}`
  );
  let anchorClaims = $derived.by(() => (
    isDecision
      ? []
      : (feedbackState.errorClaims || []).filter(claim => claim.anchor === anchor)
  ));

  $effect(() => {
    const nextCycleKey = open
      ? `${submission?.id ?? 'none'}:${aiAnalysis?.id ?? 'none'}:${anchor}`
      : '';
    if (nextCycleKey === cycleKey) return;

    cycleKey = nextCycleKey;
    requestSequence += 1;
    submitting = false;
    conflictRecord = null;
    localLoadError = '';

    if (!open) {
      ready = false;
      localLoading = false;
      return;
    }

    if (feedbackLoaded) {
      adoptRecords(feedbackRecords);
    } else {
      loadedRecords = [];
      feedbackState = initFeedbackState(aiAnalysis);
      ready = false;
      if (!feedbackLoading) requestRecords();
    }
  });

  $effect(() => {
    if (!open || ready || !feedbackLoaded) return;
    adoptRecords(feedbackRecords);
  });

  $effect(() => {
    if (!open || typeof document === 'undefined') return;

    const previousFocus = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    tick().then(() => dialogPanel?.focus());

    return () => {
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  });

  /** @param {FeedbackRecord[]} records */
  function adoptRecords(records) {
    loadedRecords = Array.isArray(records) ? [...records] : [];
    const record = loadedRecords.find(item => (
      String(item.review_proposal_id) === String(aiAnalysis?.id) &&
      String(item.reviewer_id) === String(currentUserId)
    )) || null;
    feedbackState = initFeedbackState(aiAnalysis, record);
    ready = true;
    localLoading = false;
    localLoadError = '';
  }

  async function requestRecords(force = false) {
    if (localLoading || feedbackLoading || !onRequestFeedback) {
      if (!onRequestFeedback) localLoadError = 'AI feedback could not be loaded.';
      return null;
    }

    const contextKey = cycleKey;
    const requestId = ++requestSequence;
    localLoading = true;
    localLoadError = '';
    try {
      const records = await onRequestFeedback(force);
      if (requestId !== requestSequence || cycleKey !== contextKey || !open) return null;
      if (Array.isArray(records)) adoptRecords(records);
      return records;
    } catch (error) {
      if (requestId !== requestSequence || cycleKey !== contextKey || !open) return null;
      localLoadError = errorMessage(error, 'AI feedback could not be loaded.');
      return null;
    } finally {
      if (requestId === requestSequence && cycleKey === contextKey) localLoading = false;
    }
  }

  function closeDialog() {
    if (!submitting) onClose?.();
  }

  /** @param {KeyboardEvent} event */
  function handleDialogKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeDialog();
      return;
    }
    if (event.key !== 'Tab' || !dialogPanel) return;

    const focusable = Array.from(dialogPanel.querySelectorAll(
      'button:not([disabled]), select:not([disabled]), textarea:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
    )).filter(element => !element.hasAttribute('hidden'));
    if (focusable.length === 0) {
      event.preventDefault();
      dialogPanel.focus();
      return;
    }

    const first = /** @type {HTMLElement} */ (focusable[0]);
    const last = /** @type {HTMLElement} */ (focusable[focusable.length - 1]);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
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

  /** @param {boolean} corrected */
  function setCriterionCorrected(corrected) {
    if (!activeSection) return;
    const current = feedbackState.criteria[activeSection.key];
    if (!corrected) {
      feedbackState.criteria[activeSection.key] = {
        overridden: false,
        min: null,
        max: null,
        reason: '',
        persisted: false
      };
      return;
    }
    feedbackState.criteria[activeSection.key] = {
      overridden: true,
      min: current?.overridden ? current.min : null,
      max: current?.overridden ? current.max : null,
      reason: current?.overridden ? current.reason : '',
      persisted: Boolean(current?.persisted)
    };
  }

  /** @param {'min' | 'max'} field @param {string} value */
  function setCriterionRange(field, value) {
    if (!activeSection) return;
    const criterion = feedbackState.criteria[activeSection.key];
    criterion[field] = value === '' ? null : Number(value);
    criterion.persisted = false;
  }

  /** @param {string} value */
  function setCriterionReason(value) {
    if (!activeSection) return;
    feedbackState.criteria[activeSection.key].reason = value;
  }

  function addClaim() {
    if (isDecision || anchorClaims.length > 0) return;
    claimSequence += 1;
    feedbackState.errorClaims.push({
      clientId: `new-${claimSequence}`,
      type: 'factual_error',
      text: '',
      evidenceRef: '',
      anchor
    });
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

  /** @param {FeedbackRecord} record */
  function replaceCurrentRecord(record) {
    loadedRecords = [
      ...loadedRecords.filter(item => !(
        String(item.review_proposal_id) === String(aiAnalysis?.id) &&
        String(item.reviewer_id) === String(currentUserId)
      )),
      record
    ];
  }

  function loadLatestFeedback() {
    if (!conflictRecord) return;
    replaceCurrentRecord(conflictRecord);
    feedbackState = initFeedbackState(aiAnalysis, conflictRecord);
    conflictRecord = null;
  }

  function keepDraftAfterConflict() {
    if (!conflictRecord?.updated_at) return;
    feedbackState.expectedUpdatedAt = conflictRecord.updated_at;
    conflictRecord = null;
  }

  /** @param {SubmitEvent} event */
  async function saveFeedback(event) {
    event.preventDefault();
    if (!canSave) return;

    const validationError = validateFeedbackState(feedbackState);
    if (validationError) {
      showError(validationError);
      return;
    }

    const contextKey = cycleKey;
    const requestId = ++requestSequence;
    submitting = true;
    try {
      const response = await stewardAPI.submitAIFeedback(
        submission.id,
        buildFeedbackPayload(feedbackState)
      );
      if (requestId !== requestSequence || cycleKey !== contextKey || !open) return;

      const record = response.data;
      replaceCurrentRecord(record);
      feedbackState = initFeedbackState(aiAnalysis, record);
      conflictRecord = null;

      let refreshFailed = false;
      if (onSaved) {
        try {
          await onSaved(record);
        } catch {
          refreshFailed = true;
        }
      }
      if (requestId !== requestSequence || cycleKey !== contextKey || !open) return;

      if (refreshFailed) {
        showError('Feedback was saved, but the local view could not be refreshed.');
      } else {
        showSuccess('AI review feedback saved');
      }
      onClose?.();
    } catch (error) {
      if (requestId !== requestSequence || cycleKey !== contextKey || !open) return;
      const requestError = /** @type {any} */ (error);
      if (requestError.response?.status === 409) {
        let records = null;
        if (onRequestFeedback) {
          try {
            records = await onRequestFeedback(true);
          } catch {
            records = null;
          }
        }
        if (requestId !== requestSequence || cycleKey !== contextKey || !open) return;
        const latestRecord = Array.isArray(records)
          ? records.find(record => (
              String(record.review_proposal_id) === String(aiAnalysis?.id) &&
              String(record.reviewer_id) === String(currentUserId)
            ))
          : null;
        if (latestRecord?.updated_at) {
          conflictRecord = latestRecord;
          showError('Feedback changed in another session. Choose whether to load the latest feedback or keep your draft.');
        } else {
          showError('Feedback changed in another session. Reload the page before saving again.');
        }
        return;
      }
      showError(`Failed to save AI review feedback: ${errorMessage(error, 'Unknown error')}`);
    } finally {
      if (requestId === requestSequence && cycleKey === contextKey) submitting = false;
    }
  }

  /** @param {any} error @param {string} fallback */
  function errorMessage(error, fallback) {
    const data = error?.response?.data;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data === 'string') return data;
    if (data && typeof data === 'object') {
      const first = Object.values(data)[0];
      if (Array.isArray(first) && first[0]) return String(first[0]);
      if (typeof first === 'string') return first;
    }
    return error?.message || fallback;
  }
</script>

{#snippet claimEditor()}
  <div class="space-y-3">
    {#if anchorClaims.length > 1}
      <div class="rounded-md bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900 ring-1 ring-inset ring-amber-200">
        This saved feedback has {anchorClaims.length} issues for this section. They are preserved, but no new issue can be added until the extras are removed.
      </div>
    {/if}

    {#each anchorClaims as claim, index (claim.clientId)}
      <fieldset class="rounded-md bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
        <div class="flex items-center justify-between gap-3">
          <legend class="text-xs font-semibold text-slate-700">
            Flagged issue{anchorClaims.length > 1 ? ` ${index + 1}` : ''}
          </legend>
          <button
            type="button"
            onclick={() => removeClaim(claim.clientId)}
            class="inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-500 transition-transform hover:bg-slate-200 hover:text-slate-800 active:scale-[0.96]"
            aria-label="Remove flagged issue"
            title="Remove flagged issue"
          >
            &times;
          </button>
        </div>

        <div class="mt-2 grid gap-3 sm:grid-cols-2">
          <label class="text-xs font-semibold text-slate-700">
            Issue type
            <select
              value={claim.type}
              onchange={(event) => updateClaim(claim.clientId, 'type', event.currentTarget.value)}
              class="mt-1 min-h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
              aria-label="Issue type"
            >
              {#each AI_REVIEW_CLAIM_TYPES as claimType}
                <option value={claimType.key}>{claimType.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-xs font-semibold text-slate-700">
            Evidence reference <span class="font-normal text-slate-500">(optional)</span>
            <input
              type="text"
              value={claim.evidenceRef}
              oninput={(event) => updateClaim(claim.clientId, 'evidenceRef', event.currentTarget.value)}
              maxlength="300"
              placeholder="URL, file, or line reference"
              class="mt-1 min-h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
              aria-label="Evidence reference"
            />
          </label>
        </div>

        <label class="mt-3 block text-xs font-semibold text-slate-700">
          What is wrong
          <textarea
            value={claim.text}
            oninput={(event) => updateClaim(claim.clientId, 'text', event.currentTarget.value)}
            rows="3"
            maxlength="500"
            placeholder="Describe the issue in one clear sentence."
            class="mt-1 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
            aria-label="What is wrong"
          ></textarea>
        </label>
      </fieldset>
    {/each}

    {#if anchorClaims.length === 0}
      <button
        type="button"
        onclick={addClaim}
        class="inline-flex min-h-10 items-center gap-2 rounded-md px-3 text-sm font-semibold text-amber-800 transition-transform hover:bg-amber-50 active:scale-[0.96]"
      >
        <Icons name="plus" size="sm" />
        Add flagged issue
      </button>
    {/if}
  </div>
{/snippet}

{#if open}
  <div class="fixed inset-0 z-[9000] flex items-center justify-center p-3 sm:p-6">
    <button
      type="button"
      class="absolute inset-0 cursor-default bg-slate-950/55"
      aria-label="Close AI feedback dialog"
      onclick={closeDialog}
    ></button>

    <div
      class="relative flex max-h-[min(46rem,calc(100vh-1.5rem))] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-2xl ring-1 ring-black/10 sm:max-h-[min(46rem,calc(100vh-3rem))]"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ai-feedback-dialog-title"
      tabindex="-1"
      bind:this={dialogPanel}
      onkeydown={handleDialogKeydown}
    >
      <header class="flex flex-shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-4 py-3 sm:px-5">
        <div class="min-w-0">
          <p class="text-xs font-semibold uppercase text-emerald-700">Benchmark feedback</p>
          <h2 id="ai-feedback-dialog-title" class="mt-0.5 text-lg font-semibold text-slate-950">{dialogTitle}</h2>
        </div>
        <button
          type="button"
          onclick={closeDialog}
          disabled={submitting}
          class="inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md text-xl text-slate-500 transition-transform hover:bg-slate-100 hover:text-slate-900 active:scale-[0.96] disabled:opacity-50"
          aria-label="Close AI feedback dialog"
          title="Close"
        >
          &times;
        </button>
      </header>

      {#if localLoading || (feedbackLoading && !ready)}
        <div class="flex min-h-48 items-center justify-center gap-2 px-5 text-sm text-slate-600" role="status">
          <span class="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-emerald-600"></span>
          Loading your saved feedback...
        </div>
      {:else if !ready}
        <div class="flex min-h-48 flex-col items-center justify-center gap-3 px-5 text-center" role="alert">
          <p class="max-w-sm text-sm text-red-700">{localLoadError || feedbackError || 'AI feedback could not be loaded.'}</p>
          <button
            type="button"
            onclick={() => requestRecords(true)}
            class="min-h-10 rounded-md px-3 text-sm font-semibold text-red-700 transition-transform hover:bg-red-50 active:scale-[0.96]"
          >
            Retry
          </button>
        </div>
      {:else}
        <form class="flex min-h-0 flex-1 flex-col" onsubmit={saveFeedback}>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5">
            {#if !canFileFeedback}
              <p class="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 ring-1 ring-inset ring-amber-200">
                You do not have permission to file AI review feedback.
              </p>
            {/if}

            {#if isDecision}
              <div class="rounded-md bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
                <p class="text-xs font-semibold uppercase text-slate-500">AI recommendation</p>
                <p class="mt-1 text-base font-semibold text-slate-950">
                  {AI_REVIEW_DECISIONS.find(decision => decision.key === aiAnalysis?.action)?.label || aiAnalysis?.action || 'Not provided'}
                </p>
              </div>

              <label class="mt-4 block text-sm font-semibold text-slate-800">
                Your assessment
                <select
                  value={feedbackState.decisionOverride}
                  onchange={(event) => setDecisionOverride(event.currentTarget.value)}
                  disabled={!canFileFeedback}
                  class="mt-1 min-h-11 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100 disabled:bg-slate-100"
                  aria-label="Correct AI decision"
                >
                  <option value="">Agree with AI decision</option>
                  {#each AI_REVIEW_DECISIONS.filter(decision => (
                    decision.key !== aiAnalysis?.action ||
                    decision.key === feedbackState.persistedDecisionOverride
                  )) as decision}
                    <option value={decision.key}>{decision.label}</option>
                  {/each}
                </select>
              </label>

              {#if feedbackState.decisionOverride === 'reject'}
                <fieldset class="mt-4">
                  <legend class="text-sm font-semibold text-slate-800">Gate failures</legend>
                  <div class="mt-2 grid gap-2 sm:grid-cols-2">
                    {#each RUBRIC_GATE_FAILURES as gate}
                      <label class="flex min-h-11 cursor-pointer items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700 ring-1 ring-inset ring-slate-200 hover:bg-red-50">
                        <input
                          type="checkbox"
                          checked={feedbackState.gateFailures.includes(gate.key)}
                          onchange={() => toggleGateFailure(gate.key)}
                          disabled={!canFileFeedback}
                          class="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
                        />
                        <span>{gate.label}</span>
                      </label>
                    {/each}
                  </div>
                </fieldset>
              {/if}
            {:else if activeSection}
              <div class="rounded-md bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
                <div class="flex items-center justify-between gap-3">
                  <p class="text-xs font-semibold uppercase text-slate-500">AI assessment</p>
                  <span class="rounded-full bg-white px-2.5 py-1 text-xs font-bold tabular-nums text-slate-800 ring-1 ring-inset ring-slate-200">
                    {activeAnalysisSection?.score ?? '-'} / 5
                  </span>
                </div>
                <p class="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                  {activeAnalysisSection?.reason || 'No criterion reasoning was provided.'}
                </p>
              </div>

              <fieldset class="mt-4">
                <legend class="text-sm font-semibold text-slate-800">Score assessment</legend>
                <div class="mt-2 grid grid-cols-2 gap-2">
                  <label class="flex min-h-11 cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm ring-1 ring-inset {feedbackState.criteria?.[activeSection.key]?.overridden ? 'bg-white text-slate-700 ring-slate-200' : 'bg-emerald-50 font-semibold text-emerald-900 ring-emerald-200'}">
                    <input
                      type="radio"
                      name="criterion-assessment"
                      checked={!feedbackState.criteria?.[activeSection.key]?.overridden}
                      onchange={() => setCriterionCorrected(false)}
                      disabled={!canFileFeedback}
                      class="h-4 w-4 border-slate-300 text-emerald-600 focus:ring-emerald-500"
                    />
                    Agree
                  </label>
                  <label class="flex min-h-11 cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm ring-1 ring-inset {feedbackState.criteria?.[activeSection.key]?.overridden ? 'bg-amber-50 font-semibold text-amber-900 ring-amber-200' : 'bg-white text-slate-700 ring-slate-200'}">
                    <input
                      type="radio"
                      name="criterion-assessment"
                      checked={feedbackState.criteria?.[activeSection.key]?.overridden}
                      onchange={() => setCriterionCorrected(true)}
                      disabled={!canFileFeedback}
                      class="h-4 w-4 border-slate-300 text-amber-600 focus:ring-amber-500"
                    />
                    Correct score
                  </label>
                </div>
              </fieldset>

              {#if feedbackState.criteria?.[activeSection.key]?.overridden}
                <div class="mt-3 rounded-md bg-amber-50/60 p-3 ring-1 ring-inset ring-amber-200">
                  <div class="grid grid-cols-2 gap-3">
                    <label class="text-xs font-semibold text-slate-700">
                      Minimum score
                      <select
                        value={feedbackState.criteria[activeSection.key].min ?? ''}
                        onchange={(event) => setCriterionRange('min', event.currentTarget.value)}
                        disabled={!canFileFeedback}
                        class="mt-1 min-h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                        aria-label="Minimum {activeSection.label} score"
                      >
                        <option value="">Choose</option>
                        {#each [0, 1, 2, 3, 4, 5] as score}<option value={score}>{score} / 5</option>{/each}
                      </select>
                    </label>
                    <label class="text-xs font-semibold text-slate-700">
                      Maximum score
                      <select
                        value={feedbackState.criteria[activeSection.key].max ?? ''}
                        onchange={(event) => setCriterionRange('max', event.currentTarget.value)}
                        disabled={!canFileFeedback}
                        class="mt-1 min-h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                        aria-label="Maximum {activeSection.label} score"
                      >
                        <option value="">Choose</option>
                        {#each [0, 1, 2, 3, 4, 5] as score}<option value={score}>{score} / 5</option>{/each}
                      </select>
                    </label>
                  </div>
                  <label class="mt-3 block text-xs font-semibold text-slate-700">
                    Why should the score change? <span class="font-normal text-slate-500">(optional)</span>
                    <textarea
                      value={feedbackState.criteria[activeSection.key].reason}
                      oninput={(event) => setCriterionReason(event.currentTarget.value)}
                      disabled={!canFileFeedback}
                      rows="2"
                      maxlength="500"
                      class="mt-1 w-full resize-y rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                      aria-label="Reason for {activeSection.label} score correction"
                    ></textarea>
                  </label>
                </div>
              {/if}

              <div class="mt-5 border-t border-slate-200 pt-4">
                <h3 class="text-sm font-semibold text-slate-900">Reasoning issue</h3>
                <p class="mt-1 text-xs leading-5 text-slate-500">Flag one concrete problem in the AI reasoning for this criterion.</p>
                <div class="mt-2">{@render claimEditor()}</div>
              </div>
            {:else if isSynthesis}
              <div class="rounded-md bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
                <p class="text-xs font-semibold uppercase text-slate-500">AI synthesis</p>
                {#if synthesisContent}
                  <div class="markdown-content mt-2 text-sm leading-6 text-slate-700">
                    {@html parseUserMarkdown(synthesisContent)}
                  </div>
                {:else}
                  <p class="mt-2 text-sm italic text-slate-500">No synthesis was provided.</p>
                {/if}
              </div>
              <div class="mt-4">
                <h3 class="text-sm font-semibold text-slate-900">Synthesis issue</h3>
                <p class="mt-1 text-xs leading-5 text-slate-500">Flag one concrete problem in the AI synthesis.</p>
                <div class="mt-2">{@render claimEditor()}</div>
              </div>
            {:else}
              <p class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-inset ring-red-200">
                This AI feedback section is not available.
              </p>
            {/if}

            {#if conflictRecord}
              <div class="mt-5 rounded-md bg-amber-50 p-3 ring-1 ring-inset ring-amber-300" role="alert">
                <p class="text-sm font-semibold text-amber-950">This feedback changed in another session.</p>
                <p class="mt-1 text-xs leading-5 text-amber-800">Load the latest saved version or keep this draft and overwrite it on the next save.</p>
                <div class="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onclick={loadLatestFeedback}
                    class="min-h-10 rounded-md bg-white px-3 text-sm font-semibold text-amber-900 ring-1 ring-inset ring-amber-300 transition-transform hover:bg-amber-100 active:scale-[0.96]"
                  >
                    Load latest
                  </button>
                  <button
                    type="button"
                    onclick={keepDraftAfterConflict}
                    class="min-h-10 rounded-md px-3 text-sm font-semibold text-amber-900 transition-transform hover:bg-amber-100 active:scale-[0.96]"
                  >
                    Keep my draft
                  </button>
                </div>
              </div>
            {/if}
          </div>

          <footer class="flex flex-shrink-0 items-center justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:px-5">
            <button
              type="button"
              onclick={closeDialog}
              disabled={submitting}
              class="min-h-10 rounded-md px-4 text-sm font-semibold text-slate-700 transition-transform hover:bg-slate-200 active:scale-[0.96] disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSave}
              class="inline-flex min-h-10 items-center gap-2 rounded-md bg-emerald-700 px-4 text-sm font-semibold text-white transition-transform hover:bg-emerald-800 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {#if submitting}
                <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white"></span>
              {/if}
              Save feedback
            </button>
          </footer>
        </form>
      {/if}
    </div>
  </div>
{/if}

<style>
  .markdown-content :global(p + p) {
    margin-top: 0.5rem;
  }

  .markdown-content :global(ul),
  .markdown-content :global(ol) {
    margin-left: 1.25rem;
  }
</style>
