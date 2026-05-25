<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import ContributionCard from './ContributionCard.svelte';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';
  import CRMNotesPanel from './CRMNotesPanel.svelte';
  import Link from '../lib/components/Link.svelte';
  import Avatar from './Avatar.svelte';
  import Badge from './Badge.svelte';
  import Icons from './Icons.svelte';
  import { parseMarkdown } from '../lib/markdownLoader.js';
  import { showSuccess, showError } from '../lib/toastStore';

  let {
    submission,
    showReviewForm = false,
    onReview = null,
    onPropose = null,
    onCancel = null,
    reviewData = null,
    isProcessing = false,
    successMessage = '',
    contributionTypes = [],
    users = [],
    usersLoading = false,
    usersLoaded = false,
    multipliers = {},
    isOwnSubmission = false,
    permissions = {},
    templates = [],
    notes = [],
    notesLoading = false,
    onAddNote = null,
    onToggleInteresting = null,
    onRequestNotes = null,
    onRequestUsers = null,
    onAppeal = null,
    acceptedEdit = null,
    canEditAccepted = false,
    acceptedUpdating = false,
    onAcceptedEditChange = null,
    onAcceptedUpdate = null
  } = $props();

  let togglingInteresting = $state(false);
  let copyingReviewContext = $state(false);
  let appealReason = $state('');
  let submittingAppeal = $state(false);
  let showUserPicker = $state(false);

  let canCopyReviewContext = $derived(
    showReviewForm && !isOwnSubmission && submission.state === 'pending'
  );

  function formatContextDate(dateString) {
    if (!dateString) return 'N/A';
    try {
      return format(new Date(dateString), 'yyyy-MM-dd HH:mm');
    } catch {
      return dateString;
    }
  }

  function textOrNone(value) {
    if (value === null || value === undefined || value === '') return 'None';
    return String(value);
  }

  function formatUserForContext(user) {
    if (!user) return 'N/A';
    const parts = [
      user.name || user.display_name,
      user.email,
      user.address,
    ].filter(Boolean);
    return parts.length ? parts.join(' | ') : 'N/A';
  }

  function formatEvidenceForContext() {
    if (!submission.evidence_items?.length) return 'None provided';
    return submission.evidence_items
      .map((evidence, index) => {
        const parts = [
          evidence.description ? `description: ${evidence.description}` : null,
          evidence.url ? `url: ${evidence.url}` : null,
        ].filter(Boolean);
        return `${index + 1}. ${parts.length ? parts.join(' | ') : 'Evidence item with no description or URL'}`;
      })
      .join('\n');
  }

  function formatInternalNotesForContext(contextNotes = notes) {
    if (!contextNotes?.length) return 'None';
    return contextNotes
      .map((note, index) => {
        const tags = [
          note.is_proposal ? 'proposal' : null,
          note.data?.confidence ? `confidence: ${note.data.confidence}` : null,
        ].filter(Boolean);
        const tagText = tags.length ? ` [${tags.join(', ')}]` : '';
        const author = note.user_name || note.author_details?.name || note.author_details?.address || note.author_name || 'Unknown steward';
        const message = note.message || note.text || '';
        return `${index + 1}. ${author}${tagText} (${formatContextDate(note.created_at)}): ${message}`;
      })
      .join('\n');
  }

  function buildReviewContext(contextNotes = notes) {
    const type = submission.contribution_type_details || {};
    const user = submission.user_details || {};
    const proposalLines = submission.has_proposal
      ? [
          `- Proposed action: ${textOrNone(submission.proposed_action)}`,
          `- Proposed by: ${textOrNone(submission.proposed_by_details?.name || submission.proposed_by_details?.address)}`,
          `- Proposed at: ${formatContextDate(submission.proposed_at)}`,
          `- Proposed staff reply: ${textOrNone(submission.proposed_staff_reply)}`,
        ].join('\n')
      : 'None';
    const appealLines = submission.has_appeal
      ? [
          '- Appealed: Yes',
          `- Appeal reason: ${textOrNone(submission.appeal_reason)}`,
        ].join('\n')
      : 'None';

    return [
      '# Steward Submission Review Context',
      '',
      '## Submission',
      `- ID: ${submission.id}`,
      `- State: ${submission.state_display || submission.state}`,
      `- Marked interesting: ${submission.is_interesting ? 'Yes' : 'No'}`,
      `- Submitted at: ${formatContextDate(submission.created_at)}`,
      `- Contribution date: ${formatContextDate(submission.contribution_date)}`,
      '',
      '## Contributor',
      `- User: ${formatUserForContext(user)}`,
      '',
      '## Contribution',
      `- Type: ${textOrNone(type.name || submission.contribution_type_name || getTypeName(submission.contribution_type))}`,
      `- Category: ${textOrNone(type.category)}`,
      `- Point range: ${type.min_points ?? 'N/A'}-${type.max_points ?? 'N/A'}`,
      `- Proposed points: ${textOrNone(submission.proposed_points)}`,
      `- Mission: ${textOrNone(submission.mission?.name)}`,
      '',
      '## Submitter Notes',
      textOrNone(submission.notes),
      '',
      '## Evidence',
      formatEvidenceForContext(),
      '',
      '## Appeal',
      appealLines,
      '',
      '## Internal CRM Notes',
      formatInternalNotesForContext(contextNotes),
      '',
      '## Proposal',
      proposalLines,
      '',
      '## Review Task',
      'Review whether the submission evidence supports the claimed contribution type, whether the proposed point value is appropriate, and whether more information is needed.',
    ].join('\n');
  }

  async function writeClipboard(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
  }

  async function handleCopyReviewContext() {
    if (copyingReviewContext) return;
    copyingReviewContext = true;
    try {
      let contextNotes = notes;
      if (onRequestNotes) {
        try {
          const fetched = await onRequestNotes(submission.id);
          if (Array.isArray(fetched)) contextNotes = fetched;
        } catch {
          showError('Could not load steward notes; copy aborted to avoid incomplete context.');
          return;
        }
      }

      await writeClipboard(buildReviewContext(contextNotes));
      showSuccess('Submission review context copied to clipboard');
    } catch (err) {
      showError('Failed to copy review context: ' + (err?.message || 'unknown error'));
    } finally {
      copyingReviewContext = false;
    }
  }

  async function handleToggleInteresting(event) {
    if (!onToggleInteresting) return;
    const checkbox = event.target;
    const next = checkbox.checked;
    togglingInteresting = true;
    try {
      await onToggleInteresting(submission.id, next);
    } catch {
      // Parent failed to persist; the prop hasn't changed, so resync the DOM
      // back to the underlying value to undo the browser's optimistic flip.
      checkbox.checked = submission.is_interesting;
    } finally {
      togglingInteresting = false;
    }
  }

  // Determine which actions this steward can take on this submission
  let canAccept = $derived(
    showReviewForm && permissions[submission.contribution_type]?.includes('accept')
  );
  let canReject = $derived(
    showReviewForm && permissions[submission.contribution_type]?.includes('reject')
  );
  let canRequestInfo = $derived(
    showReviewForm && permissions[submission.contribution_type]?.includes('request_more_info')
  );
  let canPropose = $derived(
    showReviewForm && permissions[submission.contribution_type]?.includes('propose')
  );
  let hasAnyAction = $derived(canAccept || canReject || canRequestInfo || canPropose);

  // State for review form
  let reviewAction = $state(reviewData?.action || 'accept');
  let proposedAction = $state('accept');

  // Filter templates by action type
  let acceptTemplates = $derived(templates.filter(t => t.action === 'accept'));
  let rejectTemplates = $derived(templates.filter(t => t.action === 'reject'));
  let moreInfoTemplates = $derived(templates.filter(t => t.action === 'more_info'));
  let proposeContextTemplates = $derived(
    reviewAction === 'propose' && proposedAction === 'reject' ? rejectTemplates :
    reviewAction === 'propose' && proposedAction === 'more_info' ? moreInfoTemplates :
    acceptTemplates
  );
  let selectedUser = $state(reviewData?.user || submission.user);
  let selectedType = $state(reviewData?.contribution_type || submission.contribution_type);
  let defaultSelectedUserDetails = $derived(
    String(selectedUser) === String(submission.user)
      ? submission.user_details
      : String(selectedUser) === String(submission.proposed_user)
        ? submission.proposed_user_details
        : null
  );
  let selectedUserDetails = $derived(
    showUserPicker
      ? users.find(u => String(u.id) === String(selectedUser)) || defaultSelectedUserDetails
      : defaultSelectedUserDetails
  );
  let selectedUserLabel = $derived(
    selectedUserDetails?.display_name ||
    selectedUserDetails?.name ||
    selectedUserDetails?.address ||
    (selectedUser ? `User #${selectedUser}` : 'Current submitter')
  );
  let selectedTypeDetails = $derived(contributionTypes.find(t => t.id === selectedType));
  let points = $state(reviewData?.points || submission.proposed_points || submission.contribution_type_details?.min_points || 0);
  let staffReply = $state(reviewData?.staff_reply || '');
  let createHighlight = $state(reviewData?.create_highlight || false);
  let highlightTitle = $state(reviewData?.highlight_title || '');
  let highlightDescription = $state(reviewData?.highlight_description || '');
  let selectedTemplateId = $state(null);

  // For ContributionSelection component
  let selectedCategory = $state(submission.contribution_type_details?.category || 'validator');
  let selectedContributionTypeObj = $state(null);
  let selectedMission = $state(submission.mission || null);

  // Track which submission's proposal we've auto-filled to avoid overwriting user edits
  let lastProposalFilled = $state(null);

  // Auto-fill form from proposal data when available
  $effect(() => {
    if (submission?.has_proposal && lastProposalFilled !== submission.id) {
      lastProposalFilled = submission.id;

      const action = submission.proposed_action || 'accept';

      if ((action === 'accept' && canAccept) ||
          (action === 'reject' && canReject) ||
          (action === 'more_info' && canRequestInfo)) {
        reviewAction = action;
      } else if (canPropose) {
        reviewAction = 'propose';
        proposedAction = action;
      } else {
        reviewAction = getDefaultAction();
        proposedAction = 'accept';
      }

      selectedUser = submission.proposed_user || submission.user;
      selectedType = submission.proposed_contribution_type || submission.contribution_type;
      points = submission.proposed_points ?? submission.contribution_type_details?.min_points ?? 0;
      staffReply = submission.proposed_staff_reply || '';
      createHighlight = submission.proposed_create_highlight || false;
      highlightTitle = submission.proposed_highlight_title || '';
      highlightDescription = submission.proposed_highlight_description || '';

      const type = contributionTypes.find(t => t.id === selectedType);
      selectedCategory = type?.category || submission.contribution_type_details?.category || 'validator';
    }
  });

  function getDefaultAction() {
    // Pick the first available action as default
    if (canAccept) return 'accept';
    if (canReject) return 'reject';
    if (canRequestInfo) return 'more_info';
    if (canPropose) return 'propose';
    return 'accept';
  }

  // Sync selected contribution type with the ContributionSelection component
  $effect(() => {
    if (selectedContributionTypeObj && selectedContributionTypeObj.id !== selectedType) {
      // Only update if the type actually changed
      selectedType = selectedContributionTypeObj.id;
      // Update points to the minimum of the new type
      const type = contributionTypes.find(t => t.id === selectedType);
      if (type) {
        points = type.min_points;
      }
    }
  });

  function handleContributionSelectionChange(category, contributionType) {
    // Handle contribution selection change
  }

  function getStateClass(state) {
    switch (state) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'accepted':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'canceled':
        return 'bg-gray-100 text-gray-700';
      case 'more_info_needed':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  }

  function getStateBorderClass(state) {
    switch (state) {
      case 'pending':
        return 'border-l-yellow-400';
      case 'accepted':
        return 'border-l-green-400';
      case 'rejected':
        return 'border-l-red-400';
      case 'canceled':
        return 'border-l-gray-400';
      case 'more_info_needed':
        return 'border-l-blue-400';
      default:
        return 'border-l-gray-400';
    }
  }

  function getStateBackgroundClass(state) {
    switch (state) {
      case 'pending':
        return 'bg-yellow-50';
      case 'accepted':
        return 'bg-green-50';
      case 'rejected':
        return 'bg-red-50';
      case 'canceled':
        return 'bg-gray-50';
      case 'more_info_needed':
        return 'bg-blue-50';
      default:
        return 'bg-gray-50';
    }
  }

  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return format(new Date(dateString), 'MMM d, yyyy HH:mm');
  }

  function adjustPoints(delta) {
    const type = selectedTypeDetails;
    if (!type) return;

    const newPoints = points + delta;
    points = Math.max(type.min_points, Math.min(type.max_points, newPoints));
  }

  function getFinalPoints() {
    const multiplier = multipliers[selectedType] || 1;
    return Math.round(points * multiplier);
  }

  function getTypeName(typeId) {
    const type = contributionTypes.find(t => t.id === typeId);
    return type?.name || 'Contribution';
  }

  function handleTemplateSelect(event) {
    const templateId = event.target.value;
    if (!templateId) {
      selectedTemplateId = null;
      return;
    }
    const template = templates.find(t => String(t.id) === templateId);
    if (template) {
      staffReply = template.text;
      selectedTemplateId = template.id;
    }
  }

  async function handleShowUserPicker() {
    showUserPicker = true;
    if (!usersLoaded && onRequestUsers) {
      await onRequestUsers();
    }
  }

  function handleReview() {
    if (onReview) {
      const data = {
        action: reviewAction,
        user: selectedUser,
        contribution_type: selectedType,
        points,
        staff_reply: staffReply,
        create_highlight: createHighlight,
        highlight_title: highlightTitle,
        highlight_description: highlightDescription,
        template_id: selectedTemplateId
      };
      onReview(submission.id, data);
    }
  }

  async function handleAppeal() {
    if (!onAppeal) return;
    const reason = appealReason.trim();
    if (!reason) return;
    submittingAppeal = true;
    try {
      await onAppeal(submission.id, reason);
      appealReason = '';
    } finally {
      submittingAppeal = false;
    }
  }

  function handlePropose() {
    if (onPropose) {
      const data = {
        proposed_action: proposedAction,
        proposed_staff_reply: staffReply,
        template_id: selectedTemplateId,
      };

      // Only include accept-specific fields when proposing accept
      if (proposedAction === 'accept') {
        data.proposed_points = points;
        data.proposed_contribution_type = selectedType;
        data.proposed_user = selectedUser;
        data.proposed_create_highlight = createHighlight;
        data.proposed_highlight_title = highlightTitle;
        data.proposed_highlight_description = highlightDescription;
      }

      onPropose(submission.id, data);
    }
  }

  const SOCIAL_PLATFORMS = [
    {
      key: 'github_connection',
      label: 'GitHub',
      color: '#24292f',
      profileUrl: (u) => `https://github.com/${u}`,
      icon: '<svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.45-1.15-1.11-1.46-1.11-1.46-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/></svg>',
    },
    {
      key: 'twitter_connection',
      label: 'X',
      color: '#000000',
      profileUrl: (u) => `https://x.com/${u}`,
      icon: '<svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>',
    },
    {
      key: 'discord_connection',
      label: 'Discord',
      color: '#5865F2',
      profileUrl: null,
      icon: '<svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/></svg>',
    },
  ];
</script>

{#snippet socialPills(user)}
  {#if user}
    {#each SOCIAL_PLATFORMS as platform}
      {@const connection = user[platform.key]}
      {#if connection?.platform_username}
        {#if platform.profileUrl}
          <a
            href={platform.profileUrl(connection.platform_username)}
            target="_blank"
            rel="noopener noreferrer"
            class="social-pill"
            style="background-color: {platform.color};"
            title="{platform.label}: @{connection.platform_username}"
          >
            <span class="social-pill-icon">{@html platform.icon}</span>
            <span class="social-pill-name">{connection.platform_username}</span>
          </a>
        {:else}
          <span
            class="social-pill"
            style="background-color: {platform.color};"
            title="{platform.label}: {connection.platform_username}"
          >
            <span class="social-pill-icon">{@html platform.icon}</span>
            <span class="social-pill-name">{connection.platform_username}</span>
          </span>
        {/if}
      {/if}
    {/each}
  {/if}
{/snippet}

<div class="bg-white shadow-lg rounded-lg border-l-4 {getStateBorderClass(submission.state)}">
  <!-- Header -->
  <div class="px-6 py-4 border-b {getStateBackgroundClass(submission.state)}">
    <div class="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-start">
      <div class="min-w-0">
        <h3 class="text-lg font-semibold flex items-center gap-2 flex-wrap">
          {#if isOwnSubmission}
            {#if submission.mission}
              <!-- Show mission name as title with Mission badge -->
              <span>{submission.mission.name}</span>
              <Badge
                badge={{
                  id: null,
                  name: 'Mission',
                  description: '',
                  points: 0
                }}
                color="indigo"
                size="sm"
                clickable={false}
                bold={false}
              />
            {:else}
              <!-- Show contribution type as title when no mission -->
              <span>{submission.contribution_type_name || getTypeName(submission.contribution_type)}</span>
            {/if}
          {:else}
            <div class="flex items-center gap-2">
              <Avatar
                user={submission.user_details}
                size="sm"
                clickable={true}
              />
              <span>{submission.user_details?.name || submission.user_details?.address?.slice(0, 8) + '...'}</span>
            </div>
          {/if}
        </h3>
        <p class="text-sm text-gray-600">
          Submitted {formatDate(submission.created_at)}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2 sm:justify-end">
        {#if canCopyReviewContext}
          <button
            type="button"
            onclick={handleCopyReviewContext}
            disabled={copyingReviewContext}
            class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 transition-colors"
            title="Copy review metadata, evidence, and internal notes for external LLM review"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16h8M8 12h8m-7 8h6a2 2 0 002-2V7.8a2 2 0 00-.59-1.41l-2.8-2.8A2 2 0 0012.2 3H9a2 2 0 00-2 2v13a2 2 0 002 2z" />
            </svg>
            <span>{copyingReviewContext ? 'Copying...' : 'Copy review context'}</span>
          </button>
        {/if}
        {#if !isOwnSubmission && onToggleInteresting}
          <label
            class="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium cursor-pointer select-none transition-colors {submission.is_interesting ? 'bg-purple-100 text-purple-800 hover:bg-purple-200' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}"
            title="Mark this submission as internally interesting"
          >
            <input
              type="checkbox"
              checked={submission.is_interesting}
              disabled={togglingInteresting}
              onchange={handleToggleInteresting}
              class="w-3.5 h-3.5 rounded border-gray-300 text-purple-600 focus:ring-purple-500 cursor-pointer"
            />
            <span>{submission.is_interesting ? 'Interesting' : 'Mark interesting'}</span>
          </label>
        {/if}
        {#if submission.has_proposal}
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
            Proposal
          </span>
        {/if}
        {#if !isOwnSubmission && submission.has_appeal}
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800" title="Submitter has appealed this submission">
            Appealed
          </span>
        {/if}
        {#if submission.notes_count > 0}
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            {submission.notes_count} note{submission.notes_count !== 1 ? 's' : ''}
          </span>
        {/if}
        <span class="px-3 py-1 rounded-full text-sm font-medium {getStateClass(submission.state)}">
          {submission.state_display}
        </span>
      </div>
    </div>
  </div>

  <!-- Content -->
  <div class="px-6 py-4">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:items-stretch">
      <!-- Left Column - Submission Details + CRM Notes -->
      <div class="flex flex-col gap-4">
        {#if !isOwnSubmission}
          <div>
            <h4 class="text-sm font-medium text-gray-700">User</h4>
            <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
              <Avatar
                user={submission.user_details}
                size="xs"
                clickable={true}
              />
              <span class="text-sm text-gray-900">
                {submission.user_details?.name || submission.user_details?.address?.slice(0, 8) + '...'}
              </span>
              {@render socialPills(submission.user_details)}
              <Link
                href="/participant/{submission.user_details?.address}"
                class="text-xs text-primary-600 hover:text-primary-700 hover:underline"
              >
                View Profile →
              </Link>
            </div>
          </div>

          <div>
            <h4 class="text-sm font-medium text-gray-700">Contribution Type</h4>
            <div class="mt-1 flex items-center gap-2 flex-wrap">
              <span class="text-sm text-gray-900">
                {submission.contribution_type_details?.name}
              </span>
              <span class="text-xs text-gray-500">
                ({submission.contribution_type_details?.min_points}-{submission.contribution_type_details?.max_points} points)
              </span>
            </div>
          </div>

          {#if submission.mission}
            <div>
              <h4 class="text-sm font-medium text-gray-700">Mission</h4>
              <div class="mt-1 flex items-center gap-2 flex-wrap">
                <span class="text-sm text-gray-900">
                  {submission.mission.name}
                </span>
              </div>
            </div>
          {/if}
        {/if}

        {#if isOwnSubmission && submission.mission}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Contribution Type</h4>
            <p class="mt-1 text-sm text-gray-900">
              {submission.contribution_type_name || getTypeName(submission.contribution_type)}
            </p>
          </div>
        {/if}

        <div>
          <h4 class="text-sm font-medium text-gray-700">Contribution Date</h4>
          <p class="mt-1 text-sm text-gray-900">{formatDate(submission.contribution_date)}</p>
        </div>

        {#if submission.notes}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Notes</h4>
            <div class="markdown-content mt-1 text-sm text-gray-900">{@html parseMarkdown(submission.notes)}</div>
          </div>
        {/if}

        {#if !isOwnSubmission && submission.has_appeal && submission.appeal_reason}
          <div class="border border-orange-200 rounded-lg p-3 bg-orange-50">
            <h4 class="text-sm font-medium text-orange-900 mb-1">Appeal reason</h4>
            <p class="text-sm text-orange-800 whitespace-pre-wrap">{submission.appeal_reason}</p>
          </div>
        {/if}

        {#if submission.evidence_items?.length > 0}
          <div>
            <h4 class="text-sm font-medium text-gray-700">Evidence</h4>
            <ul class="mt-1 space-y-1">
              {#each submission.evidence_items as evidence}
                <li class="text-sm text-gray-600">
                  {#if evidence.description}
                    • {evidence.description}
                  {/if}
                  {#if evidence.url}
                    <a href={evidence.url} target="_blank" class="text-primary-600 underline ml-1">
                      View URL
                    </a>
                  {/if}
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if submission.staff_reply && submission.state !== 'rejected' && submission.state !== 'canceled'}
          <div class="bg-gray-50 p-3 rounded">
            <h4 class="text-sm font-medium text-gray-700 mb-1">Staff Response</h4>
            <div class="markdown-content text-sm text-gray-600">{@html parseMarkdown(submission.staff_reply)}</div>
          </div>
        {/if}

        <!-- CRM Notes Panel (steward view only) -->
        {#if showReviewForm && !isOwnSubmission}
          <CRMNotesPanel
            submissionId={submission.id}
            {notes}
            loading={notesLoading}
            {onAddNote}
          />
        {/if}
      </div>

      <!-- Right Column - Action Forms or Status or Contribution Card -->
      <div class="flex flex-col gap-4">
        {#if submission.state === 'accepted' && submission.contribution && isOwnSubmission}
          <!-- Show contribution card for accepted submissions in My Submissions -->
          <ContributionCard
            contribution={submission.contribution}
            showUser={false}
            variant="compact"
          />
        {:else if showReviewForm && (submission.state === 'pending' || submission.state === 'more_info_needed')}
          <!-- Proposal Notice -->
          {#if submission.has_proposal}
            <div class="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span class="text-sm text-amber-800">
                  Proposed by <span class="font-medium">{submission.proposed_by_details?.name || 'a steward'}</span>
                  {#if submission.proposed_at}
                    on {formatDate(submission.proposed_at)}
                  {/if}
                </span>
              </div>
            </div>
          {/if}

          {#if hasAnyAction}
            <div class="border {reviewAction === 'accept' ? 'border-green-200' : reviewAction === 'reject' ? 'border-red-200' : reviewAction === 'propose' ? 'border-amber-200' : 'border-blue-200'} rounded-lg">
              <!-- Action Toggle Buttons - Only show actions the steward has permission for -->
              <div class="flex flex-wrap">
                {#if canAccept}
                  <button
                    type="button"
                    onclick={() => reviewAction = 'accept'}
                    class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'accept' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-700 hover:bg-green-100'} border-r border-gray-200"
                  >
                    Accept
                  </button>
                {/if}
                {#if canReject}
                  <button
                    type="button"
                    onclick={() => reviewAction = 'reject'}
                    class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'reject' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-700 hover:bg-red-100'} border-r border-gray-200"
                  >
                    Reject
                  </button>
                {/if}
                {#if canRequestInfo}
                  <button
                    type="button"
                    onclick={() => reviewAction = 'more_info'}
                    class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'more_info' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'} border-r border-gray-200"
                  >
                    Request Info
                  </button>
                {/if}
                {#if canPropose}
                  <button
                    type="button"
                    onclick={() => reviewAction = 'propose'}
                    class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'propose' ? 'bg-amber-600 text-white' : 'bg-amber-50 text-amber-700 hover:bg-amber-100'}"
                  >
                    Propose
                  </button>
                {/if}
              </div>

              <!-- Dynamic Form Content -->
              {#if reviewAction === 'accept' || reviewAction === 'propose'}
                <div class="p-4 {reviewAction === 'accept' ? 'bg-green-50' : 'bg-amber-50'}">
                  <div class="space-y-3">
                    {#if reviewAction === 'propose'}
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Proposed Action</label>
                        <div class="flex gap-2">
                          <button type="button" onclick={() => proposedAction = 'accept'}
                            class="flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors {proposedAction === 'accept' ? 'bg-green-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}">
                            Accept
                          </button>
                          <button type="button" onclick={() => proposedAction = 'reject'}
                            class="flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors {proposedAction === 'reject' ? 'bg-red-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}">
                            Reject
                          </button>
                          <button type="button" onclick={() => proposedAction = 'more_info'}
                            class="flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors {proposedAction === 'more_info' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}">
                            Request Info
                          </button>
                        </div>
                      </div>
                    {/if}
                    {#if reviewAction === 'accept' || proposedAction === 'accept'}
                    <div class="space-y-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700">
                        Assign Contribution To
                      </label>
                      <div class="mt-1 flex items-center gap-2">
                        <Avatar
                          user={selectedUserDetails}
                          size="sm"
                        />
                        {#if showUserPicker && users.length > 0}
                          <select
                            bind:value={selectedUser}
                            class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
                          >
                            {#each users as user}
                              <option value={user.id}>
                                {user.display_name}
                              </option>
                            {/each}
                          </select>
                        {:else}
                          <div class="flex-1 min-w-0 px-3 py-2 border border-gray-200 rounded-md text-sm bg-white text-gray-700 truncate">
                            {selectedUserLabel}
                          </div>
                          <button
                            type="button"
                            onclick={handleShowUserPicker}
                            disabled={usersLoading}
                            class="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            {usersLoading ? 'Loading...' : 'Change'}
                          </button>
                        {/if}
                      </div>
                      <p class="text-xs text-gray-500 mt-1">
                        The contribution will be assigned to this user
                      </p>
                    </div>

                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-2">
                        Contribution Type
                      </label>
                      <ContributionSelection
                        bind:selectedCategory
                        bind:selectedContributionType={selectedContributionTypeObj}
                        bind:selectedMission
                        defaultContributionType={submission.contribution_type}
                        defaultMission={submission.mission?.id}
                        onlySubmittable={false}
                        stewardMode={true}
                        providedContributionTypes={contributionTypes}
                        onSelectionChange={handleContributionSelectionChange}
                      />
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                          Points
                        </label>
                        <div class="inline-flex items-center">
                          <button
                            onclick={() => adjustPoints(points > 10 ? -5 : -1)}
                            class="w-7 h-8 flex items-center justify-center bg-white hover:bg-gray-50 rounded-l-lg text-gray-600 hover:text-gray-800 font-bold transition-colors border border-r-0 border-gray-300"
                            type="button"
                          >
                            −
                          </button>
                          <input
                            type="number"
                            bind:value={points}
                            class="w-12 h-8 px-1 border-y border-gray-300 text-sm text-center font-semibold bg-white focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent focus:z-10"
                          />
                          <button
                            onclick={() => adjustPoints(points > 10 ? 5 : 1)}
                            class="w-7 h-8 flex items-center justify-center bg-white hover:bg-gray-50 rounded-r-lg text-gray-600 hover:text-gray-800 font-bold transition-colors border border-l-0 border-gray-300"
                            type="button"
                          >
                            +
                          </button>
                        </div>
                        <p class="text-xs text-gray-500 mt-1">
                          Range: {selectedTypeDetails?.min_points || 0}-{selectedTypeDetails?.max_points || 100}
                        </p>
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                          Final Points
                        </label>
                        <div class="text-2xl font-bold {reviewAction === 'accept' ? 'text-green-700' : 'text-amber-700'}">
                          {getFinalPoints()}
                        </div>
                        <p class="text-xs text-gray-500 mt-1">
                          ×{multipliers[selectedType] || 1} multiplier
                        </p>
                      </div>
                    </div>

                    <div class="border border-yellow-300 rounded-lg overflow-hidden">
                      <button
                        type="button"
                        onclick={() => createHighlight = !createHighlight}
                        class="w-full px-3 py-2 bg-yellow-50 hover:bg-yellow-100 transition-colors flex items-center justify-between text-left"
                      >
                        <span class="flex items-center gap-2">
                          <svg class="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                          </svg>
                          <span class="text-sm font-medium text-yellow-900">Feature this contribution</span>
                        </span>
                        <svg
                          class="w-4 h-4 text-yellow-600 transition-transform {createHighlight ? 'rotate-180' : ''}"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>

                      {#if createHighlight}
                        <div class="px-4 py-3 bg-white border-t border-yellow-300 space-y-3">
                          <p class="text-xs text-yellow-700 mb-2">
                            Highlighted contributions are displayed on the dashboard and earn special recognition
                          </p>

                          <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">
                              Feature Title <span class="text-red-500">*</span>
                            </label>
                            <input
                              type="text"
                              bind:value={highlightTitle}
                              placeholder="e.g., Outstanding Bug Discovery"
                              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
                            />
                          </div>

                          <div>
                            <label class="block text-sm font-medium text-gray-700 mb-1">
                              Feature Description <span class="text-red-500">*</span>
                            </label>
                            <textarea
                              bind:value={highlightDescription}
                              placeholder="Describe why this contribution is being highlighted..."
                              rows="3"
                              class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
                            ></textarea>
                          </div>
                        </div>
                      {/if}
                    </div>
                    </div>
                    {/if}

                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        {reviewAction === 'propose' && proposedAction === 'reject' ? 'Rejection Reason' : reviewAction === 'propose' && proposedAction === 'more_info' ? 'Information Needed' : 'Note (optional)'}
                      </label>
                      {#if proposeContextTemplates.length > 0}
                        <select
                          value={selectedTemplateId || ''}
                          onchange={handleTemplateSelect}
                          class="w-full px-3 py-1.5 mb-2 border border-gray-300 rounded-md text-sm bg-white text-gray-600"
                        >
                          <option value="">-- Select template --</option>
                          {#each proposeContextTemplates as template}
                            <option value={template.id}>{template.label}</option>
                          {/each}
                        </select>
                      {/if}
                      <textarea
                        bind:value={staffReply}
                        placeholder={reviewAction === 'propose' && proposedAction === 'reject' ? 'Please provide a reason for rejection...' : reviewAction === 'propose' && proposedAction === 'more_info' ? 'What additional information do you need?' : 'Add an optional note for this contribution...'}
                        rows="3"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 {reviewAction === 'accept' ? 'focus:ring-green-500' : 'focus:ring-amber-500'}"
                      ></textarea>
                    </div>

                    {#if reviewAction === 'accept'}
                      <button
                        onclick={handleReview}
                        disabled={isProcessing}
                        class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                      >
                        {isProcessing ? 'Processing...' : 'Accept & Create Contribution'}
                      </button>
                    {:else}
                      <!-- Propose action -->
                      <button
                        onclick={handlePropose}
                        disabled={isProcessing}
                        class="w-full px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                      >
                        {isProcessing ? 'Processing...' : 'Submit Proposal'}
                      </button>
                    {/if}
                  </div>
                </div>
              {:else if reviewAction === 'reject'}
                <div class="p-4 bg-red-50">
                  <div class="space-y-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Rejection Reason
                      </label>
                      {#if rejectTemplates.length > 0}
                        <select
                          value={selectedTemplateId || ''}
                          onchange={handleTemplateSelect}
                          class="w-full px-3 py-1.5 mb-2 border border-gray-300 rounded-md text-sm bg-white text-gray-600"
                        >
                          <option value="">-- Select template --</option>
                          {#each rejectTemplates as template}
                            <option value={template.id}>{template.label}</option>
                          {/each}
                        </select>
                      {/if}
                      <textarea
                        bind:value={staffReply}
                        placeholder="Please provide a reason for rejection..."
                        rows="4"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
                      ></textarea>
                    </div>

                    <button
                      onclick={handleReview}
                      disabled={isProcessing}
                      class="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                    >
                      {isProcessing ? 'Processing...' : 'Reject Submission'}
                    </button>
                  </div>
                </div>
              {:else if reviewAction === 'more_info'}
                <div class="p-4 bg-blue-50">
                  <div class="space-y-3">
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-1">
                        Information Needed
                      </label>
                      {#if moreInfoTemplates.length > 0}
                        <select
                          value={selectedTemplateId || ''}
                          onchange={handleTemplateSelect}
                          class="w-full px-3 py-1.5 mb-2 border border-gray-300 rounded-md text-sm bg-white text-gray-600"
                        >
                          <option value="">-- Select template --</option>
                          {#each moreInfoTemplates as template}
                            <option value={template.id}>{template.label}</option>
                          {/each}
                        </select>
                      {/if}
                      <textarea
                        bind:value={staffReply}
                        placeholder="What additional information do you need from the submitter?"
                        rows="4"
                        class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm bg-white"
                      ></textarea>
                    </div>

                    <button
                      onclick={handleReview}
                      disabled={isProcessing}
                      class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                    >
                      {isProcessing ? 'Processing...' : 'Request Information'}
                    </button>
                  </div>
                </div>
              {/if}
            </div>
          {/if}
        {:else if submission.state === 'accepted' && submission.contribution}
          <!-- Show contribution details if accepted -->
          <ContributionCard
            contribution={submission.contribution}
            submission={submission}
            showExpand={true}
          />

          {#if showReviewForm && canEditAccepted && acceptedEdit}
            <div class="overflow-hidden rounded-lg border border-emerald-200 bg-white shadow-sm">
              <div class="border-b border-emerald-100 bg-emerald-50/80 px-4 py-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                        <Icons name="points" size="sm" />
                      </span>
                      <h4 class="text-sm font-semibold text-gray-900">Accepted contribution settings</h4>
                    </div>
                    <p class="mt-1 text-xs text-emerald-800">
                      Currently saved: {submission.contribution.frozen_global_points ?? submission.contribution.points ?? 0} pts
                    </p>
                  </div>

                  {#if submission.contribution.highlight}
                    <span class="inline-flex items-center gap-1.5 rounded-full bg-yellow-100 px-2.5 py-1 text-xs font-medium text-yellow-800">
                      <Icons name="star" size="xs" />
                      Featured
                    </span>
                  {/if}
                </div>
              </div>

              <div class="space-y-4 p-4">
                <div>
                  <label for="accepted-points-{submission.id}" class="mb-1.5 block text-sm font-medium text-gray-800">
                    Awarded points
                  </label>
                  <div class="flex items-center gap-3">
                    <input
                      id="accepted-points-{submission.id}"
                      type="number"
                      min="0"
                      value={acceptedEdit.points}
                      oninput={(event) => onAcceptedEditChange?.(submission.id, 'points', event.currentTarget.value)}
                      disabled={acceptedUpdating}
                      class="h-10 w-28 rounded-md border border-gray-300 px-3 text-sm font-semibold text-gray-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
                    />
                    <span class="text-sm text-gray-500">points after save</span>
                  </div>
                </div>

                <div class="rounded-md border border-yellow-200 bg-yellow-50/70 p-3">
                  <div class="mb-3 flex items-center gap-2">
                    <Icons name="star" size="sm" className="text-yellow-600" />
                    <h5 class="text-sm font-semibold text-yellow-950">Featured highlight</h5>
                  </div>
                  <p class="mb-3 text-xs text-yellow-900">
                    Fill both fields to feature this contribution. Clear both fields to remove the feature.
                  </p>

                  <div class="space-y-3">
                    <div>
                      <label for="accepted-highlight-title-{submission.id}" class="mb-1 block text-xs font-medium uppercase text-yellow-900">
                        Title
                      </label>
                      <input
                        id="accepted-highlight-title-{submission.id}"
                        type="text"
                        value={acceptedEdit.highlight_title}
                        oninput={(event) => onAcceptedEditChange?.(submission.id, 'highlight_title', event.currentTarget.value)}
                        disabled={acceptedUpdating}
                        placeholder="Feature title"
                        class="w-full rounded-md border border-yellow-200 bg-white px-3 py-2 text-sm text-gray-900 focus:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-400 disabled:opacity-50"
                      />
                    </div>

                    <div>
                      <label for="accepted-highlight-description-{submission.id}" class="mb-1 block text-xs font-medium uppercase text-yellow-900">
                        Description
                      </label>
                      <textarea
                        id="accepted-highlight-description-{submission.id}"
                        value={acceptedEdit.highlight_description}
                        oninput={(event) => onAcceptedEditChange?.(submission.id, 'highlight_description', event.currentTarget.value)}
                        disabled={acceptedUpdating}
                        placeholder="Add the feature description"
                        rows="3"
                        class="w-full resize-y rounded-md border border-yellow-200 bg-white px-3 py-2 text-sm text-gray-900 focus:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-400 disabled:opacity-50"
                      ></textarea>
                    </div>
                  </div>
                </div>

                <div class="flex justify-end">
                  <button
                    type="button"
                    onclick={() => onAcceptedUpdate?.(submission.id)}
                    disabled={acceptedUpdating}
                    class="inline-flex items-center justify-center rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {acceptedUpdating ? 'Saving...' : 'Save accepted changes'}
                  </button>
                </div>
              </div>
            </div>
          {/if}
        {:else if submission.state === 'rejected'}
          {#if submission.staff_reply}
            <div class="border border-red-200 rounded-lg p-4 bg-red-50">
              <h4 class="text-sm font-medium text-red-900 mb-2">Rejection Reason</h4>
              <div class="markdown-content text-sm text-red-700">{@html parseMarkdown(submission.staff_reply)}</div>
            </div>
          {/if}
          {#if isOwnSubmission}
            {#if submission.has_appeal}
              <div class="border border-orange-200 rounded-lg p-3 bg-orange-50">
                <p class="text-sm text-orange-800">
                  You have already appealed this submission. Each submission can only be appealed once.
                </p>
              </div>
            {:else if onAppeal}
              <div class="border border-orange-200 rounded-lg p-3 bg-orange-50 space-y-2">
                <h4 class="text-sm font-medium text-orange-900">Appeal this rejection</h4>
                <p class="text-xs text-orange-700">
                  You can appeal this rejection once. Explain why you believe it should be reconsidered.
                </p>
                <textarea
                  bind:value={appealReason}
                  placeholder="Explain why you are appealing..."
                  rows="3"
                  maxlength="5000"
                  class="w-full px-3 py-2 border border-orange-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500"
                ></textarea>
                <div class="flex justify-end">
                  <button
                    onclick={handleAppeal}
                    disabled={submittingAppeal || !appealReason.trim()}
                    class="px-4 py-1.5 text-sm bg-orange-600 text-white rounded-md hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    {submittingAppeal ? 'Submitting...' : 'Submit Appeal'}
                  </button>
                </div>
              </div>
            {/if}
          {/if}
        {:else if submission.state === 'canceled'}
          <div class="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h4 class="text-sm font-medium text-gray-900 mb-2">Canceled</h4>
            <p class="text-sm text-gray-700">Canceled by user</p>
          </div>
        {:else if isOwnSubmission && submission.state === 'pending' && submission.has_appeal}
          <div class="border border-orange-200 rounded-lg p-3 bg-orange-50">
            <h4 class="text-sm font-medium text-orange-900 mb-1">Your appeal is under review</h4>
            <p class="text-xs text-orange-700">A steward will re-review your submission.</p>
          </div>
        {:else if isOwnSubmission && (submission.state === 'pending' || submission.state === 'more_info_needed')}
          <!-- Edit button for pending and more_info_needed submissions -->
          <div class="flex justify-end">
            <button
              onclick={() => {
                let url = `/contributions/${submission.id}`;
                if (submission.mission?.id) {
                  url += `?mission=${submission.mission.id}`;
                }
                push(url);
              }}
              class="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700"
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

  .social-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.125rem 0.5rem;
    border-radius: 9999px;
    color: white;
    font-size: 11px;
    line-height: 1.2;
    font-weight: 500;
    text-decoration: none;
    max-width: 140px;
  }
  a.social-pill:hover {
    filter: brightness(1.1);
  }
  .social-pill-icon {
    display: inline-flex;
    flex-shrink: 0;
  }
  .social-pill-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
