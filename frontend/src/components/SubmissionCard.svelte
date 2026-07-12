<script>
  import { push } from 'svelte-spa-router';
  import { format } from '../lib/dates.js';
  import { parseMarkdown, parseUserMarkdown } from '../lib/markdownLoader.js';
  import { showError, showSuccess } from '../lib/toastStore.js';
  import Badge from './Badge.svelte';
  import ContributionCard from './ContributionCard.svelte';
  import EvidenceUrlCard from './EvidenceUrlCard.svelte';

  /** @type {{
   *   submission: Record<string, any>,
   *   onAppeal?: ((submissionId: string | number, reason: string) => Promise<unknown>) | null
   * }} */
  let { submission, onAppeal = null } = $props();

  /** @type {Record<string, { badge: string, border: string, header: string }>} */
  const STATE_STYLES = {
    pending: {
      badge: 'bg-yellow-100 text-yellow-800',
      border: 'border-l-yellow-400',
      header: 'bg-yellow-50'
    },
    accepted: {
      badge: 'bg-green-100 text-green-800',
      border: 'border-l-green-400',
      header: 'bg-green-50'
    },
    rejected: {
      badge: 'bg-red-100 text-red-800',
      border: 'border-l-red-400',
      header: 'bg-red-50'
    },
    canceled: {
      badge: 'bg-gray-100 text-gray-700',
      border: 'border-l-gray-400',
      header: 'bg-gray-50'
    },
    more_info_needed: {
      badge: 'bg-blue-100 text-blue-800',
      border: 'border-l-blue-400',
      header: 'bg-blue-50'
    }
  };
  const DEFAULT_STATE_STYLE = {
    badge: 'bg-gray-100 text-gray-800',
    border: 'border-l-gray-400',
    header: 'bg-gray-50'
  };

  let appealReason = $state('');
  let submittingAppeal = $state(false);
  let copyingSubmissionId = $state(false);

  let stateStyle = $derived(STATE_STYLES[submission.state] || DEFAULT_STATE_STYLE);
  let contributionTypeName = $derived(
    submission.contribution_type_name ||
    submission.contribution_type_details?.name ||
    'Contribution'
  );
  let isMilestoneSubmission = $derived(
    submission.contribution_type_details?.slug === 'milestones'
  );
  let textOnlyEvidence = $derived(
    (submission.evidence_items || []).filter(
      (/** @type {Record<string, any>} */ evidence) => !evidence?.url && evidence?.description
    )
  );
  let urlEvidence = $derived(
    (submission.evidence_items || []).filter(
      (/** @type {Record<string, any>} */ evidence) => evidence?.url
    )
  );
  let moreInfoRequests = $derived(
    (submission.more_info_requests || []).filter(
      (/** @type {Record<string, any>} */ request) => request?.message
    )
  );
  let showStaffResponse = $derived(Boolean(
    submission.staff_reply &&
    submission.state !== 'rejected' &&
    submission.state !== 'canceled' &&
    !(submission.state === 'more_info_needed' && moreInfoRequests.length > 0)
  ));

  /** @param {string | null | undefined} dateString */
  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return format(new Date(dateString), 'MMM d, yyyy HH:mm');
  }

  /** @param {string | number} text */
  async function writeClipboard(text) {
    const clipboardText = String(text);
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(clipboardText);
      return;
    }

    const textArea = document.createElement('textarea');
    textArea.value = clipboardText;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    try {
      textArea.focus();
      textArea.select();
      if (!document.execCommand('copy')) {
        throw new Error('Clipboard copy was rejected');
      }
    } finally {
      textArea.remove();
    }
  }

  async function handleCopySubmissionId() {
    if (copyingSubmissionId) return;
    copyingSubmissionId = true;
    try {
      await writeClipboard(submission.id);
      showSuccess('Submission ID copied to clipboard');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'unknown error';
      showError('Failed to copy submission ID: ' + message);
    } finally {
      copyingSubmissionId = false;
    }
  }

  async function handleAppeal() {
    const reason = appealReason.trim();
    if (!onAppeal || !reason || submittingAppeal) return;

    submittingAppeal = true;
    try {
      await onAppeal(submission.id, reason);
      appealReason = '';
    } finally {
      submittingAppeal = false;
    }
  }

  function editSubmission() {
    const missionQuery = submission.mission?.id ? `?mission=${submission.mission.id}` : '';
    push(`/contributions/${submission.id}${missionQuery}`);
  }
</script>

<div class="rounded-lg border-l-4 bg-white shadow-lg {stateStyle.border}">
  <div class="border-b px-6 py-4 {stateStyle.header}">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="min-w-0">
        <h3 class="flex flex-wrap items-center gap-2 text-lg font-semibold">
          {#if submission.mission}
            <span>{submission.mission.name}</span>
            <Badge
              badge={{
                id: null,
                name: 'Mission',
                description: '',
                points: 0,
                actionId: null,
                actionName: '',
                evidenceUrl: ''
              }}
              color="indigo"
              size="sm"
              clickable={false}
              bold={false}
            />
          {:else}
            <span>{contributionTypeName}</span>
          {/if}
          {#if isMilestoneSubmission && submission.milestone_version}
            <span class="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
              v{submission.milestone_version}
            </span>
          {/if}
        </h3>
        <p class="text-sm text-gray-600">Submitted {formatDate(submission.created_at)}</p>
      </div>

      <div class="flex flex-wrap items-center gap-2 sm:justify-end">
        <button
          type="button"
          onclick={handleCopySubmissionId}
          disabled={copyingSubmissionId}
          class="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
          title="Copy submission ID"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16h8M8 12h8m-7 8h6a2 2 0 002-2V7.8a2 2 0 00-.59-1.41l-2.8-2.8A2 2 0 0012.2 3H9a2 2 0 00-2 2v13a2 2 0 002 2z" />
          </svg>
          <span>{copyingSubmissionId ? 'Copying...' : 'Copy ID'}</span>
        </button>
        <span class="rounded-full px-3 py-1 text-sm font-medium {stateStyle.badge}">
          {submission.state_display}
        </span>
      </div>
    </div>
  </div>

  <div class="px-6 py-4">
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:items-start">
      <div class="flex flex-col gap-4">
        {#if submission.mission}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Contribution Type</h4>
            <p class="mt-1 text-sm text-gray-900">{contributionTypeName}</p>
          </div>
        {/if}

        {#if submission.project_contribution}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Linked Project</h4>
            <div class="mt-1 flex flex-wrap items-center gap-2">
              <p class="text-sm text-gray-900">{submission.project_contribution.title}</p>
              {#if isMilestoneSubmission && submission.milestone_version}
                <span class="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
                  Milestone v{submission.milestone_version}
                </span>
              {/if}
              {#if submission.project_contribution.link}
                <a href={submission.project_contribution.link} class="text-xs text-primary-600 hover:text-primary-700 hover:underline">
                  View Project
                </a>
              {/if}
              {#if submission.project_contribution.github_url}
                <a
                  href={submission.project_contribution.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-xs text-primary-600 hover:text-primary-700 hover:underline"
                >
                  Project Repository
                </a>
              {/if}
            </div>
          </div>
        {/if}

        <div>
          <h4 class="text-sm font-medium text-gray-700">Contribution Date</h4>
          <p class="mt-1 text-sm text-gray-900">{formatDate(submission.contribution_date)}</p>
        </div>

        {#if submission.notes}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Notes</h4>
            <div class="markdown-content mt-1 text-sm text-gray-900">{@html parseUserMarkdown(submission.notes)}</div>
          </div>
        {/if}

        {#if moreInfoRequests.length > 0}
          <div class="rounded-lg border border-blue-200 bg-blue-50 p-3">
            <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h4 class="text-sm font-medium text-blue-950">More information requested</h4>
              {#if moreInfoRequests.length > 1}
                <span class="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                  {moreInfoRequests.length} requests
                </span>
              {/if}
            </div>
            <div class="divide-y divide-blue-100">
              {#each moreInfoRequests as request, index (request.id || index)}
                <div class="{index === 0 ? 'pt-0' : 'pt-3'} {index === moreInfoRequests.length - 1 ? 'pb-0' : 'pb-3'}">
                  <div class="markdown-content text-sm text-blue-900">{@html parseMarkdown(request.message)}</div>
                  <p class="mt-2 text-xs text-blue-700">
                    {request.user_name ? `Requested by ${request.user_name}` : 'Requested'}
                    {#if request.created_at}on {formatDate(request.created_at)}{/if}
                  </p>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if submission.evidence_items?.length > 0}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Evidence</h4>
            {#if urlEvidence.length > 0}
              <div class="mt-2 flex flex-col gap-2">
                {#each urlEvidence as evidence}
                  <EvidenceUrlCard {evidence} compact={true} />
                {/each}
              </div>
            {/if}
            {#if textOnlyEvidence.length > 0}
              <ul class="mt-2 space-y-1">
                {#each textOnlyEvidence as evidence}
                  <li class="text-sm text-gray-600">{evidence.description}</li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}

        {#if showStaffResponse}
          <div class="rounded bg-gray-50 p-3">
            <h4 class="mb-1 text-sm font-medium text-gray-700">Staff Response</h4>
            <div class="markdown-content text-sm text-gray-600">{@html parseMarkdown(submission.staff_reply)}</div>
          </div>
        {/if}
      </div>

      <div class="flex flex-col gap-4">
        {#if submission.state === 'accepted' && submission.contribution}
          <ContributionCard contribution={submission.contribution} showUser={false} variant="compact" />
        {:else if submission.state === 'rejected'}
          {#if submission.staff_reply}
            <div class="rounded-lg border border-red-200 bg-red-50 p-4">
              <h4 class="mb-2 text-sm font-medium text-red-900">Rejection Reason</h4>
              <div class="markdown-content text-sm text-red-700">{@html parseMarkdown(submission.staff_reply)}</div>
            </div>
          {/if}

          {#if submission.has_appeal}
            <div class="rounded-lg border border-orange-200 bg-orange-50 p-3">
              <p class="text-sm text-orange-800">
                You have already appealed this submission. Each submission can only be appealed once.
              </p>
            </div>
          {:else if onAppeal}
            <div class="space-y-2 rounded-lg border border-orange-200 bg-orange-50 p-3">
              <h4 class="text-sm font-medium text-orange-900">Appeal this rejection</h4>
              <p class="text-xs text-orange-700">
                You can appeal this rejection once. Explain why you believe it should be reconsidered.
              </p>
              <textarea
                bind:value={appealReason}
                aria-label="Appeal reason"
                placeholder="Explain why you are appealing..."
                rows="3"
                maxlength="5000"
                class="w-full rounded-md border border-orange-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              ></textarea>
              <div class="flex justify-end">
                <button
                  type="button"
                  onclick={handleAppeal}
                  disabled={submittingAppeal || !appealReason.trim()}
                  class="rounded-md bg-orange-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {submittingAppeal ? 'Submitting...' : 'Submit Appeal'}
                </button>
              </div>
            </div>
          {/if}
        {:else if submission.state === 'canceled'}
          <div class="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <h4 class="mb-2 text-sm font-medium text-gray-900">Canceled</h4>
            <p class="text-sm text-gray-700">Canceled by user</p>
          </div>
        {:else if submission.state === 'pending' && submission.has_appeal}
          <div class="rounded-lg border border-orange-200 bg-orange-50 p-3">
            <h4 class="mb-1 text-sm font-medium text-orange-900">Your appeal is under review</h4>
            <p class="text-xs text-orange-700">A steward will re-review your submission.</p>
          </div>
        {:else if submission.state === 'pending' || submission.state === 'more_info_needed'}
          <div class="flex justify-end">
            <button
              type="button"
              onclick={editSubmission}
              class="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Edit
            </button>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

<style>
  .markdown-content :global(ul) {
    list-style-type: disc;
    margin-left: 1.5rem;
  }

  .markdown-content :global(ol) {
    list-style-type: decimal;
    margin-left: 1.5rem;
  }
</style>
