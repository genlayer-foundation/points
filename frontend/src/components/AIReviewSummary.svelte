<script>
  import Icons from './Icons.svelte';
  import { stewardAPI } from '../lib/api.js';
  import { parseUserMarkdown } from '../lib/markdownLoader.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import { RUBRIC_SECTIONS } from '../lib/rubricReview.js';
  import { AI_REVIEW_DECISIONS } from '../lib/aiFeedback.js';

  /** @typedef {Record<string, any>} FeedbackRecord */
  /** @type {{
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
   *   onOpenFeedback?: ((anchor: string) => void) | null,
   *   controlsOnly?: boolean
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
    onSaved = null,
    onOpenFeedback = null,
    controlsOnly = false
  } = $props();

  let expanded = $state(false);
  let submittingAccurate = $state(false);
  let requestSequence = 0;
  let activeContext = $state('');

  let currentRecord = $derived.by(() => {
    if (!feedbackLoaded || currentUserId === null || currentUserId === undefined) return null;
    return (feedbackRecords || []).find(record => (
      String(record.review_proposal_id) === String(aiAnalysis?.id) &&
      String(record.reviewer_id) === String(currentUserId)
    )) || null;
  });
  let decisionLabel = $derived(
    AI_REVIEW_DECISIONS.find(decision => decision.key === aiAnalysis?.action)?.label ||
    aiAnalysis?.action ||
    'Not provided'
  );
  let synthesisHasFeedback = $derived(Boolean(
    currentRecord?.error_claims?.some(isSynthesisClaim)
  ));
  let hasDecisionCorrection = $derived(Boolean(currentRecord?.correct_decision));
  let synthesisContent = $derived(aiAnalysis?.synthesis || aiAnalysis?.overall_reason || '');

  $effect(() => {
    const context = `${submission?.id ?? 'none'}:${aiAnalysis?.id ?? 'none'}`;
    if (context === activeContext) return;
    activeContext = context;
    requestSequence += 1;
    submittingAccurate = false;
    expanded = false;
  });

  function toggleExpanded() {
    expanded = !expanded;
  }

  /** @param {Record<string, any>} claim */
  function isSynthesisClaim(claim) {
    return claim.anchor === 'synthesis';
  }

  /** @param {string} anchor */
  function openFeedback(anchor) {
    onOpenFeedback?.(anchor);
  }

  function handleFeedbackMenu(event) {
    const anchor = event.currentTarget.value;
    if (!anchor) return;
    openFeedback(anchor);
    event.currentTarget.value = '';
  }

  async function markAccurate() {
    if (!canFileFeedback || submittingAccurate) return;
    const context = activeContext;
    const requestId = ++requestSequence;
    submittingAccurate = true;
    try {
      let records = feedbackLoaded ? feedbackRecords : null;
      if (!feedbackLoaded && onRequestFeedback) {
        records = await onRequestFeedback();
      }
      if (requestId !== requestSequence || context !== activeContext) return;

      const existingRecord = Array.isArray(records)
        ? records.find(record => (
            String(record.review_proposal_id) === String(aiAnalysis?.id) &&
            String(record.reviewer_id) === String(currentUserId)
          ))
        : currentRecord;
      const payload = {
        verdict: 'agree',
        ...(aiAnalysis?.id !== null && aiAnalysis?.id !== undefined
          ? { review_proposal_id: aiAnalysis.id }
          : {}),
        ...(existingRecord?.updated_at
          ? { expected_updated_at: existingRecord.updated_at }
          : {})
      };
      const response = await stewardAPI.submitAIFeedback(submission.id, payload);
      if (requestId !== requestSequence || context !== activeContext) return;

      let refreshFailed = false;
      if (onSaved) {
        try {
          await onSaved(response.data);
        } catch {
          refreshFailed = true;
        }
      }
      if (requestId !== requestSequence || context !== activeContext) return;
      if (refreshFailed) {
        showError('Feedback was saved, but the local view could not be refreshed.');
      } else {
        showSuccess('AI review marked accurate');
      }
    } catch (error) {
      if (requestId !== requestSequence || context !== activeContext) return;
      const requestError = /** @type {any} */ (error);
      if (requestError.response?.status === 409) {
        try {
          await onRequestFeedback?.(true);
        } catch {
          // The stale-write message still tells the reviewer how to recover.
        }
        showError('Feedback changed in another session. Review the latest feedback before marking it accurate.');
        return;
      }
      showError(`Failed to mark AI review accurate: ${errorMessage(error)}`);
    } finally {
      if (requestId === requestSequence && context === activeContext) submittingAccurate = false;
    }
  }

  /** @param {any} error */
  function errorMessage(error) {
    const data = error?.response?.data;
    if (typeof data?.detail === 'string') return data.detail;
    if (typeof data === 'string') return data;
    return error?.message || 'Unknown error';
  }
</script>

{#snippet feedbackActions()}
  {#if feedbackLoaded && currentRecord?.verdict === 'agree'}
    <span class="inline-flex min-h-10 items-center rounded-md bg-emerald-50 px-3 text-xs font-semibold text-emerald-800 ring-1 ring-inset ring-emerald-200">
      Marked accurate
    </span>
  {:else}
    <button
      type="button"
      onclick={markAccurate}
      disabled={submittingAccurate || feedbackLoading}
      class="inline-flex min-h-10 items-center gap-1.5 rounded-md px-3 text-xs font-semibold text-emerald-800 transition-transform hover:bg-emerald-50 active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50"
    >
      {#if submittingAccurate}
        <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-emerald-200 border-t-emerald-700"></span>
      {/if}
      Mark AI accurate
    </button>
  {/if}
  <label class="sr-only" for="ai-feedback-menu-{submission.id}">Open AI feedback section</label>
  <select
    id="ai-feedback-menu-{submission.id}"
    value=""
    onchange={handleFeedbackMenu}
    class="min-h-10 rounded-md border-0 bg-slate-100 px-3 text-xs font-semibold text-slate-700 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-400"
    aria-label="Open AI feedback section"
  >
    <option value="">Review AI feedback</option>
    <option value="decision">{hasDecisionCorrection ? 'Edit decision feedback' : 'Review decision'}</option>
    {#each RUBRIC_SECTIONS.filter(section => aiAnalysis?.sections?.[section.key]) as section}
      <option value={section.key}>Review {section.label}</option>
    {/each}
    <option value="synthesis">{synthesisHasFeedback ? 'Edit synthesis feedback' : 'Review synthesis'}</option>
  </select>
{/snippet}

{#if controlsOnly}
  <div class="flex flex-wrap items-center justify-between gap-2 border-t border-amber-200 bg-amber-50/60 px-3 py-2">
    <span class="text-xs font-semibold uppercase text-amber-800">AI benchmark</span>
    {#if canFileFeedback}
      <div class="flex flex-wrap items-center gap-1.5">{@render feedbackActions()}</div>
    {/if}
  </div>
{:else}
<section class="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-inset ring-slate-200">
  <div class="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-center">
    <button
      type="button"
      onclick={toggleExpanded}
      class="flex min-h-11 min-w-0 flex-1 items-center justify-between gap-3 rounded-md px-1 text-left transition-transform hover:bg-slate-50 active:scale-[0.99]"
      aria-expanded={expanded}
      aria-controls="ai-review-synthesis-{submission.id}"
      aria-label="{expanded ? 'Hide' : 'Show'} AI review synthesis"
    >
      <span class="flex min-w-0 items-center gap-2.5">
        <span class="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100">
          <Icons name="sparkle" size="sm" />
        </span>
        <span class="min-w-0">
          <span class="block text-sm font-semibold text-slate-950">AI review</span>
          <span class="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
            <span>Recommends {decisionLabel}</span>
            {#if aiAnalysis?.confidence}
              <span aria-hidden="true">&middot;</span>
              <span class="capitalize">{aiAnalysis.confidence} confidence</span>
            {/if}
          </span>
        </span>
      </span>
      <Icons
        name="chevronDown"
        size="sm"
        className="flex-shrink-0 text-slate-500 transition-transform {expanded ? 'rotate-180' : ''}"
      />
    </button>

    {#if canFileFeedback}
      <div class="flex flex-wrap items-center gap-1.5 sm:justify-end">
        {@render feedbackActions()}
      </div>
    {/if}
  </div>

  {#if feedbackError && !feedbackLoaded}
    <p class="border-t border-red-100 bg-red-50 px-4 py-2 text-xs text-red-700" role="alert">{feedbackError}</p>
  {/if}

  {#if expanded}
    <div id="ai-review-synthesis-{submission.id}" class="border-t border-slate-200 px-4 py-3">
      <p class="text-xs font-semibold uppercase text-slate-500">Synthesis</p>
      {#if synthesisContent}
        <div class="markdown-content mt-1.5 text-sm leading-6 text-slate-700">
          {@html parseUserMarkdown(synthesisContent)}
        </div>
      {:else}
        <p class="mt-1.5 text-sm italic text-slate-500">No synthesis was provided.</p>
      {/if}
      {#if canFileFeedback}
        <div class="mt-2 flex justify-end">
          <button
            type="button"
            onclick={() => openFeedback('synthesis')}
            class="min-h-10 rounded-md px-3 text-xs font-semibold text-amber-800 transition-transform hover:bg-amber-50 active:scale-[0.96]"
          >
            {synthesisHasFeedback ? 'Edit synthesis feedback' : 'Flag synthesis issue'}
          </button>
        </div>
      {/if}
    </div>
  {/if}
</section>
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
