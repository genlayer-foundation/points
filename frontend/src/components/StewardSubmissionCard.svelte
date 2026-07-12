<script>
  import { untrack } from 'svelte';
  import { format } from '../lib/dates.js';
  import ContributionCard from './ContributionCard.svelte';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';
  import CRMNotesPanel from './CRMNotesPanel.svelte';
  import AIReviewSummary from './AIReviewSummary.svelte';
  import AIFeedbackDialog from './AIFeedbackDialog.svelte';
  import Avatar from './Avatar.svelte';
  import Icons from './Icons.svelte';
  import EvidenceUrlCard from './EvidenceUrlCard.svelte';
  import { stewardAPI } from '../lib/api.js';
  import { parseMarkdown, parseUserMarkdown } from '../lib/markdownLoader.js';
  import { showSuccess, showError } from '../lib/toastStore';
  import {
    RUBRIC_EXTRAS,
    RUBRIC_GATE_FAILURES,
    RUBRIC_SECTIONS,
    buildRubricReviewPayload,
    calculateRubricPoints,
    defaultRubricSections,
    hydrateRubricState,
    isProjectReviewFlow,
    validateRubricReviewState
  } from '../lib/rubricReview.js';

  let {
    submission,
    showReviewForm = true,
    onReview = null,
    onPropose = null,
    onQuestionProposal = null,
    reviewData = null,
    isProcessing = false,
    successMessage = '',
    contributionTypes = [],
    users = [],
    usersLoading = false,
    usersLoaded = false,
    multipliers = {},
    permissions = {},
    templates = [],
    notes = [],
    notesLoading = false,
    onAddNote = null,
    onUpdateNote = null,
    onToggleInteresting = null,
    onContributionTypeUpdate = null,
    onRequestUsers = null,
    currentUserId = null,
    acceptedEdit = null,
    canEditAccepted = false,
    acceptedUpdating = false,
    contributionTypeUpdating = false,
    onAcceptedEditChange = null,
    onAcceptedUpdate = null,
    enableRubricReview = false
  } = $props();

  let togglingInteresting = $state(false);
  let copyingSubmissionId = $state(false);
  let showUserPicker = $state(false);
  let showQuestionForm = $state(false);
  let questionFeedback = $state('');
  let questionSubmitting = $state(false);
  let questionTrigger = $state(null);
  let questionDialogElement = $state(null);
  let questionTextarea = $state(null);
  let submissionNotesExpanded = $state(false);
  let internalNotesExpanded = $state(false);
  let moreDetailsExpanded = $state(false);
  let expandedRubricReasons = $state(new Set());
  let feedbackDialogOpen = $state(false);
  let feedbackDialogAnchor = $state('decision');
  let lastQuestionSubmissionId = $state(null);
  /** @type {Array<Record<string, any>>} */
  let aiFeedbackRecords = $state([]);
  let aiFeedbackLoading = $state(false);
  let aiFeedbackLoaded = $state(false);
  let aiFeedbackError = $state('');
  let aiFeedbackContextKey = $state('');
  let aiFeedbackRequestId = 0;
  /** @type {string[]} */
  let rubricGateFailures = $state([]);
  let rubricSections = $state(defaultRubricSections());
  /** @type {string[]} */
  let rubricExtras = $state([]);
  let rubricOverallReason = $state('');

  let textOnlyEvidence = $derived(
    (submission.evidence_items || []).filter(evidence => !evidence?.url && evidence?.description)
  );
  let urlEvidence = $derived(
    (submission.evidence_items || []).filter(evidence => evidence?.url)
  );
  let moreInfoRequests = $derived(
    (submission.more_info_requests || []).filter(request => request?.message)
  );
  let showStaffResponse = $derived(Boolean(
    submission.staff_reply &&
    submission.state !== 'rejected' &&
    submission.state !== 'canceled' &&
    !(submission.state === 'more_info_needed' && moreInfoRequests.length > 0)
  ));
  let isProposalQuestioned = $derived(submission.proposal_review_status === 'questioned');
  let isProposalPendingReview = $derived(
    submission.has_proposal &&
    (submission.proposal_review_status === 'pending_review' || !submission.proposal_review_status)
  );
  let isOpenReviewState = $derived(
    submission.state === 'pending' || submission.state === 'more_info_needed'
  );
  let showHumanProposal = $derived(Boolean(submission.has_proposal && !submission.proposal_is_ai));
  let showAIProposal = $derived(Boolean(
    submission.ai_analysis && (!submission.has_proposal || submission.proposal_is_ai)
  ));
  let isCurrentProposalOwner = $derived(Boolean(
    currentUserId &&
    submission.proposed_by &&
    String(submission.proposed_by) === String(currentUserId)
  ));
  let hasAnyTypePermission = $derived(Boolean(
    permissions[submission.contribution_type]?.length
  ));
  let isFeedbackOwnSubmission = $derived(Boolean(
    currentUserId !== null &&
    currentUserId !== undefined &&
    submission.user !== null &&
    submission.user !== undefined &&
    String(submission.user) === String(currentUserId)
  ));
  let canFileFeedback = $derived(Boolean(
    showReviewForm &&
    !isFeedbackOwnSubmission &&
    currentUserId !== null &&
    currentUserId !== undefined &&
    submission.ai_analysis &&
    hasAnyTypePermission
  ));

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

  async function handleCopySubmissionId() {
    if (copyingSubmissionId) return;
    copyingSubmissionId = true;
    try {
      await writeClipboard(submission.id);
      showSuccess('Submission ID copied to clipboard');
    } catch (err) {
      showError('Failed to copy submission ID: ' + (err?.message || 'unknown error'));
    } finally {
      copyingSubmissionId = false;
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
    showReviewForm && !isProposalQuestioned && permissions[submission.contribution_type]?.includes('accept')
  );
  let canReject = $derived(
    showReviewForm && !isProposalQuestioned && permissions[submission.contribution_type]?.includes('reject')
  );
  let canRequestInfo = $derived(
    showReviewForm && !isProposalQuestioned && permissions[submission.contribution_type]?.includes('request_more_info')
  );
  let canPropose = $derived(
    showReviewForm &&
    permissions[submission.contribution_type]?.includes('propose') &&
    (!isProposalQuestioned || isCurrentProposalOwner)
  );
  let canChangeContributionType = $derived(
    showReviewForm &&
    !isProposalQuestioned &&
    (permissions[submission.contribution_type]?.includes('accept') ||
      permissions[submission.contribution_type]?.includes('reject'))
  );
  let canEditActiveProposalNote = $derived(
    canPropose &&
    submission.state === 'pending' &&
    submission.has_proposal &&
    !isProposalQuestioned &&
    currentUserId &&
    String(submission.proposed_by) === String(currentUserId)
  );
  let canQuestionProposal = $derived(Boolean(
    showReviewForm &&
    onQuestionProposal &&
    !submission.proposal_is_ai &&
    isOpenReviewState &&
    isProposalPendingReview &&
    currentUserId &&
    !isCurrentProposalOwner &&
    (
      permissions[submission.contribution_type]?.includes('accept') ||
      permissions[submission.contribution_type]?.includes('reject') ||
      permissions[submission.contribution_type]?.includes('request_more_info')
    )
  ));
  let activeProposalNoteId = $derived.by(() => {
    if (!canEditActiveProposalNote) return null;
    const proposalNotes = (notes || []).filter(note => note.is_proposal);
    if (!proposalNotes.length) return null;
    const latest = [...proposalNotes].sort((a, b) => {
      const timeDiff = new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      if (timeDiff !== 0) return timeDiff;

      const aId = Number(a.id);
      const bId = Number(b.id);
      if (Number.isFinite(aId) && Number.isFinite(bId)) return bId - aId;
      return String(b.id).localeCompare(String(a.id));
    })[0];
    return latest?.id ?? null;
  });
  function directPermissionFor(action) {
    if (action === 'accept') return canAccept;
    if (action === 'reject') return canReject;
    if (action === 'more_info') return canRequestInfo;
    return false;
  }

  function submissionModeFor(action) {
    if (directPermissionFor(action)) return 'final';
    if (canPropose) return 'proposal';
    return null;
  }

  let availableOutcomes = $derived(
    ['accept', 'more_info', 'reject'].filter(action => submissionModeFor(action))
  );
  let hasAnyAction = $derived(availableOutcomes.length > 0);

  // State for review form
  let reviewAction = $state(untrack(() => normalizeProposedAction(reviewData?.action) || 'accept'));
  let selectedSubmissionMode = $derived(submissionModeFor(reviewAction));

  // Filter templates by action type
  let acceptTemplates = $derived(templates.filter(t => t.action === 'accept'));
  let rejectTemplates = $derived(templates.filter(t => t.action === 'reject'));
  let moreInfoTemplates = $derived(templates.filter(t => t.action === 'more_info'));
  let proposeContextTemplates = $derived(
    reviewAction === 'reject' ? rejectTemplates :
    reviewAction === 'more_info' ? moreInfoTemplates :
    acceptTemplates
  );
  let selectedUser = $state(untrack(() => reviewData?.user || submission.user));
  let selectedType = $state(untrack(() => reviewData?.contribution_type || submission.contribution_type));
  let selectedProject = $state(untrack(() => reviewData?.project_contribution || submission.project_contribution?.id || ''));
  let acceptedProjects = $state([]);
  let acceptedProjectsLoading = $state(false);
  let acceptedProjectsError = $state('');
  let acceptedProjectsUser = $state(null);
  let acceptedProjectsLoaded = $state(false);
  let acceptedProjectsRequestId = 0;
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
  let selectedTypeDetails = $derived(
    contributionTypes.find(t => String(t.id) === String(selectedType)) ||
    (String(selectedType) === String(submission.contribution_type) ? submission.contribution_type_details : null)
  );
  let isSelectedMilestoneType = $derived(selectedTypeDetails?.slug === 'milestones');
  let isProjectReview = $derived(
    enableRubricReview && isProjectReviewFlow(
      reviewAction === 'accept'
        ? selectedTypeDetails?.review_flow
        : submission.contribution_type_details?.review_flow
    )
  );
  let rubricState = $derived({
    gateFailures: rubricGateFailures,
    sections: rubricSections,
    extras: rubricExtras,
    overallReason: rubricOverallReason
  });
  let hasRubricGateFailures = $derived(rubricGateFailures.length > 0);
  let isProposalRubric = $derived(selectedSubmissionMode === 'proposal');
  let showProjectRubric = $derived(
    isProjectReview && (
      reviewAction === 'accept' ||
      reviewAction === 'reject' ||
      selectedSubmissionMode === 'proposal'
    )
  );
  let showAwardEditor = $derived(
    reviewAction === 'accept' && (selectedSubmissionMode === 'final' || !isProjectReview)
  );
  let points = $state(untrack(() => reviewData?.points || submission.proposed_points || submission.contribution_type_details?.min_points || 0));
  let staffReply = $state(untrack(() => reviewData?.staff_reply || ''));
  let createHighlight = $state(untrack(() => reviewData?.create_highlight || false));
  let highlightTitle = $state(untrack(() => reviewData?.highlight_title || ''));
  let highlightDescription = $state(untrack(() => reviewData?.highlight_description || ''));
  let selectedTemplateId = $state(null);
  let outcomeDrafts = $state(untrack(() => ({
    [reviewAction]: {
      staffReply: reviewData?.staff_reply || '',
      templateId: null
    }
  })));
  let autoSelectedGateKey = $state(null);
  let autoSelectedGateTemplateText = $state('');
  let rubricPointsManuallyEdited = $state(false);

  $effect(() => {
    if (isProjectReview && !hasRubricGateFailures) {
      updateProjectRubricPoints(rubricState);
    }
  });

  // For ContributionSelection component
  let selectedCategory = $state(untrack(() => submission.contribution_type_details?.category || 'validator'));
  let selectedContributionTypeObj = $state(null);
  let selectedMission = $state(untrack(() => submission.mission || null));
  let isMilestoneSubmission = $derived(submission.contribution_type_details?.slug === 'milestones');
  let hasDistinctContributionDate = $derived(Boolean(
    submission.contribution_date &&
    String(submission.contribution_date).slice(0, 10) !== String(submission.created_at || '').slice(0, 10)
  ));
  let currentAIFeedbackRecord = $derived.by(() => {
    if (currentUserId === null || currentUserId === undefined || !submission.ai_analysis?.id) return null;
    return aiFeedbackRecords.find(record =>
      String(record.review_proposal_id) === String(submission.ai_analysis.id) &&
      String(record.reviewer_id) === String(currentUserId)
    ) || null;
  });

  // Track which submission's proposal we've auto-filled to avoid overwriting user edits
  let lastProposalFilled = $state(null);

  function normalizeAction(action) {
    if (action === 'request_more_info') return 'more_info';
    if (action === 'accept' || action === 'reject' || action === 'more_info' || action === 'propose') {
      return action;
    }
    return null;
  }

  function normalizeProposedAction(action) {
    const normalized = normalizeAction(action);
    return normalized === 'propose' ? null : normalized;
  }

  function actionLabel(action) {
    if (action === 'more_info') return 'Request info';
    if (action === 'reject') return 'Reject';
    return 'Accept';
  }

  function submitButtonLabel() {
    if (selectedSubmissionMode === 'proposal') {
      if (reviewAction === 'more_info') return 'Propose requesting information';
      if (reviewAction === 'reject') return 'Propose rejection';
      return 'Propose acceptance';
    }
    if (reviewAction === 'more_info') return 'Request information';
    if (reviewAction === 'reject') return 'Reject submission';
    return 'Accept contribution';
  }

  function hasAIAnchorFeedback(anchor) {
    if (!currentAIFeedbackRecord) return false;
    if (anchor === 'decision') return Boolean(currentAIFeedbackRecord.correct_decision);
    const criterion = currentAIFeedbackRecord.criteria?.[anchor];
    const corrected = Boolean(criterion && criterion.agree !== true);
    const claimed = (currentAIFeedbackRecord.error_claims || []).some(
      claim => (claim.anchor || '') === anchor
    );
    return corrected || claimed;
  }

  function canUseReviewAction(action) {
    const normalized = normalizeAction(action);
    return Boolean(normalized && normalized !== 'propose' && submissionModeFor(normalized));
  }

  function getDefaultAction() {
    return availableOutcomes[0] || 'accept';
  }

  // Auto-fill form from proposal data when available. Wait until this card has
  // permissions so proposal-only stewards do not get pinned to the accept view.
  $effect(() => {
    if (submission?.has_proposal && hasAnyAction && lastProposalFilled !== submission.id) {
      lastProposalFilled = submission.id;

      const action = normalizeProposedAction(submission.proposed_action) || 'accept';
      const proposalDraft = {
        staffReply: submission.proposed_staff_reply || '',
        templateId: submission.proposed_template || null
      };
      const nextDrafts = {
        ...outcomeDrafts,
        [action]: proposalDraft
      };

      if (canUseReviewAction(action)) {
        reviewAction = action;
        staffReply = proposalDraft.staffReply;
        selectedTemplateId = proposalDraft.templateId;
      } else {
        const fallbackAction = getDefaultAction();
        const fallbackDraft = nextDrafts[fallbackAction] || { staffReply: '', templateId: null };
        reviewAction = fallbackAction;
        staffReply = fallbackDraft.staffReply;
        selectedTemplateId = fallbackDraft.templateId;
      }
      outcomeDrafts = nextDrafts;

      selectedUser = submission.proposed_user || submission.user;
      selectedType = submission.proposed_contribution_type || submission.contribution_type;
      points = submission.proposed_points ?? submission.contribution_type_details?.min_points ?? 0;
      createHighlight = submission.proposed_create_highlight || false;
      highlightTitle = submission.proposed_highlight_title || '';
      highlightDescription = submission.proposed_highlight_description || '';

      const type = contributionTypes.find(t => t.id === selectedType);
      selectedCategory = type?.category || submission.contribution_type_details?.category || 'validator';

      if (submission.rubric_review) {
        applyRubricReview(submission.rubric_review);
      }
    }
  });

  $effect(() => {
    if (hasAnyAction && !canUseReviewAction(reviewAction)) {
      selectOutcome(getDefaultAction());
    }
  });

  $effect(() => {
    if (submission?.rubric_review && lastProposalFilled !== submission.id) {
      applyRubricReview(submission.rubric_review);
    }
  });

  $effect(() => {
    if (hasRubricGateFailures && reviewAction !== 'reject' && submissionModeFor('reject')) {
      selectOutcome('reject');
    }
  });

  $effect(() => {
    if (submission.id !== lastQuestionSubmissionId) {
      lastQuestionSubmissionId = submission.id;
      showQuestionForm = false;
      questionFeedback = '';
      return;
    }
    if (!canQuestionProposal) {
      showQuestionForm = false;
    }
  });

  $effect(() => {
    const nextContextKey = `${submission.id}:${submission.ai_analysis?.id ?? 'none'}`;
    if (nextContextKey !== aiFeedbackContextKey) {
      aiFeedbackContextKey = nextContextKey;
      aiFeedbackRequestId += 1;
      aiFeedbackRecords = [];
      aiFeedbackLoading = false;
      aiFeedbackLoaded = false;
      aiFeedbackError = '';
    }
  });

  // Sync selected contribution type with the ContributionSelection component
  $effect(() => {
    if (selectedContributionTypeObj && selectedContributionTypeObj.id !== selectedType) {
      // Only update if the type actually changed
      selectedType = selectedContributionTypeObj.id;
      rubricPointsManuallyEdited = false;
      // Update points to the minimum of the new type
      const type = contributionTypes.find(t => t.id === selectedType);
      if (type) {
        points = type.min_points;
      }
    }
  });

  $effect(() => {
    if (reviewAction === 'accept' && isSelectedMilestoneType && selectedUser) {
      loadAcceptedProjectsForSelectedUser(selectedUser);
    }
    if (!isSelectedMilestoneType) {
      acceptedProjectsError = '';
      acceptedProjectsLoaded = false;
    }
  });

  function canReviewContributionType(typeId) {
    return permissions[typeId]?.includes('accept') || permissions[typeId]?.includes('reject');
  }

  async function handleContributionSelectionChange(category, contributionType) {
    if (!contributionType || contributionTypeUpdating) return;
    if (String(contributionType.id) === String(submission.contribution_type)) return;
    if (!onContributionTypeUpdate || !canChangeContributionType) return;
    if (!canReviewContributionType(contributionType.id)) {
      showError('You need accept or reject permission on the selected type.');
      selectedType = submission.contribution_type;
      selectedContributionTypeObj = contributionTypes.find(
        type => String(type.id) === String(submission.contribution_type)
      ) || null;
      return;
    }
    await onContributionTypeUpdate(submission.id, contributionType.id);
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

  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return format(new Date(dateString), 'MMM d, yyyy HH:mm');
  }

  function adjustPoints(delta) {
    const type = selectedTypeDetails;
    if (!type) return;

    rubricPointsManuallyEdited = true;
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

  function getGateFailure(key) {
    return RUBRIC_GATE_FAILURES.find(gate => gate.key === key) || null;
  }

  function getGateFailureTemplate(key) {
    const gate = getGateFailure(key);
    if (!gate?.templateLabel) return null;
    return rejectTemplates.find(template => template.label === gate.templateLabel) || null;
  }

  function applyTemplate(template) {
    staffReply = template.text;
    selectedTemplateId = template.id;
  }

  function applyGateFailureTemplate(key) {
    const template = getGateFailureTemplate(key);
    if (!template) return;
    applyTemplate(template);
    autoSelectedGateKey = key;
    autoSelectedGateTemplateText = template.text;
  }

  function clearAutoGateTemplateIfUnchanged() {
    if (autoSelectedGateTemplateText && staffReply === autoSelectedGateTemplateText) {
      staffReply = '';
      selectedTemplateId = null;
    }
    autoSelectedGateKey = null;
    autoSelectedGateTemplateText = '';
  }

  function handleTemplateSelect(event) {
    const templateId = event.target.value;
    autoSelectedGateKey = null;
    autoSelectedGateTemplateText = '';
    if (!templateId) {
      selectedTemplateId = null;
      return;
    }
    const template = templates.find(t => String(t.id) === templateId);
    if (template) {
      applyTemplate(template);
    }
  }

  function applyRubricReview(review) {
    const state = hydrateRubricState(review);
    rubricGateFailures = state.gateFailures;
    rubricSections = state.sections;
    rubricExtras = state.extras;
    rubricOverallReason = state.overallReason;
    updateProjectRubricPoints(state);
  }

  function updateProjectRubricPoints(state = rubricState) {
    if (!isProjectReview || rubricPointsManuallyEdited || state.gateFailures?.length > 0) return;
    points = clampPointsToSelectedType(
      calculateRubricPoints(state, selectedTypeDetails?.rubric_extra_points)
    );
  }

  function markPointsManuallyEdited() {
    rubricPointsManuallyEdited = true;
  }

  function clampPointsToSelectedType(value) {
    const min = Number(selectedTypeDetails?.min_points);
    const max = Number(selectedTypeDetails?.max_points);
    let nextValue = value;

    if (Number.isFinite(min)) {
      nextValue = Math.max(min, nextValue);
    }
    if (Number.isFinite(max)) {
      nextValue = Math.min(max, nextValue);
    }

    return nextValue;
  }

  function toggleRubricGate(key) {
    if (rubricGateFailures.includes(key)) {
      const remainingGateFailures = rubricGateFailures.filter(item => item !== key);
      rubricGateFailures = remainingGateFailures;
      if (autoSelectedGateKey === key) {
        if (remainingGateFailures.length > 0 && staffReply === autoSelectedGateTemplateText) {
          applyGateFailureTemplate(remainingGateFailures[0]);
        } else {
          clearAutoGateTemplateIfUnchanged();
        }
      }
      return;
    }
    if (submissionModeFor('reject')) {
      selectOutcome('reject');
    }
    rubricGateFailures = [...rubricGateFailures, key];
    applyGateFailureTemplate(key);
  }

  function clearRubricGates() {
    rubricGateFailures = [];
    clearAutoGateTemplateIfUnchanged();
  }

  function toggleRubricExtra(key) {
    if (rubricExtras.includes(key)) {
      const nextExtras = rubricExtras.filter(item => item !== key);
      rubricExtras = nextExtras;
      updateProjectRubricPoints({ ...rubricState, extras: nextExtras });
      return;
    }
    const nextExtras = [...rubricExtras, key];
    rubricExtras = nextExtras;
    updateProjectRubricPoints({ ...rubricState, extras: nextExtras });
  }

  function updateRubricScore(sectionKey, score) {
    const nextSections = {
      ...rubricSections,
      [sectionKey]: {
        ...(rubricSections[sectionKey] || { reason: '' }),
        score: Number(score)
      }
    };
    rubricSections = nextSections;
    updateProjectRubricPoints({ ...rubricState, sections: nextSections });
  }

  function updateRubricReason(sectionKey, reason) {
    rubricSections = {
      ...rubricSections,
      [sectionKey]: {
        ...(rubricSections[sectionKey] || { score: 0 }),
        reason
      }
    };
  }

  function getRubricSectionReason(sectionKey) {
    return (rubricSections[sectionKey]?.reason || '').trim();
  }

  async function handleShowUserPicker() {
    showUserPicker = true;
    if (!usersLoaded && onRequestUsers) {
      await onRequestUsers();
    }
  }

  async function loadAcceptedProjectsForSelectedUser(userId) {
    const userKey = String(userId || '');
    if (!userKey) return;
    if (acceptedProjectsLoading && acceptedProjectsUser === userKey) return;
    if (acceptedProjectsLoaded && acceptedProjectsUser === userKey) return;

    const requestId = ++acceptedProjectsRequestId;
    const previousSelection = String(selectedProject || '');
    acceptedProjectsUser = userKey;
    acceptedProjects = [];
    acceptedProjectsError = '';
    acceptedProjectsLoaded = false;
    acceptedProjectsLoading = true;

    try {
      const response = await stewardAPI.getAcceptedProjectsForUser(userKey, submission.id);
      if (requestId !== acceptedProjectsRequestId) return;

      const projects = response.data || [];
      acceptedProjects = projects;
      acceptedProjectsLoaded = true;

      if (previousSelection && projects.some(project => String(project.id) === previousSelection)) {
        selectedProject = previousSelection;
        return;
      }

      const submissionProjectId = submission.project_contribution?.id;
      if (
        submissionProjectId &&
        String(selectedUser) === String(submission.user) &&
        projects.some(project => String(project.id) === String(submissionProjectId))
      ) {
        selectedProject = submissionProjectId;
      } else {
        selectedProject = '';
      }
    } catch (err) {
      if (requestId !== acceptedProjectsRequestId) return;
      acceptedProjectsError = err.response?.data?.detail || err.message || 'Failed to load accepted projects';
      acceptedProjectsUser = null;
      acceptedProjectsLoaded = false;
      selectedProject = '';
    } finally {
      if (requestId === acceptedProjectsRequestId) {
        acceptedProjectsLoading = false;
      }
    }
  }

  function handleReview() {
    if (onReview) {
      if (isProjectReview && reviewAction === 'accept' && hasRubricGateFailures) {
        showError('Clear all gate failures before accepting this project.');
        return;
      }
      if (reviewAction === 'accept' && isSelectedMilestoneType && !selectedProject) {
        showError('Select the accepted project this milestone belongs to.');
        return;
      }

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
      if (isSelectedMilestoneType) {
        data.project_contribution = selectedProject;
      }
      if (isProjectReview && (reviewAction === 'accept' || reviewAction === 'reject')) {
        data.rubric_review = buildRubricReviewPayload(rubricState);
      }
      onReview(submission.id, data);
    }
  }

  function handlePropose() {
    if (onPropose) {
      const proposalAction = reviewAction;
      if (isProjectReview) {
        const validationError = validateRubricReviewState(rubricState, proposalAction);
        if (validationError) {
          showError(validationError);
          return;
        }
      }

      const data = {
        proposed_action: proposalAction,
        proposed_staff_reply: staffReply,
        template_id: selectedTemplateId,
      };

      // Only include accept-specific fields when proposing accept
      if (proposalAction === 'accept') {
        if (!isProjectReview) {
          data.proposed_points = points;
        }
        data.proposed_contribution_type = selectedType;
        data.proposed_user = selectedUser;
        if (!isProjectReview) {
          data.proposed_create_highlight = createHighlight;
          data.proposed_highlight_title = highlightTitle;
          data.proposed_highlight_description = highlightDescription;
        }
      }

      if (isProjectReview) {
        data.rubric_review = buildRubricReviewPayload(rubricState);
      }

      onPropose(submission.id, data);
    }
  }

  function handleSubmitOutcome() {
    if (selectedSubmissionMode === 'final') {
      handleReview();
      return;
    }
    if (selectedSubmissionMode === 'proposal') {
      handlePropose();
    }
  }

  function selectOutcome(action) {
    if (!submissionModeFor(action)) return;
    if (action === reviewAction) return;
    outcomeDrafts = {
      ...outcomeDrafts,
      [reviewAction]: {
        staffReply,
        templateId: selectedTemplateId
      }
    };
    const nextDraft = outcomeDrafts[action] || { staffReply: '', templateId: null };
    reviewAction = action;
    staffReply = nextDraft.staffReply;
    selectedTemplateId = nextDraft.templateId;
    autoSelectedGateKey = null;
    autoSelectedGateTemplateText = '';
  }

  function toggleRubricReason(sectionKey) {
    const next = new Set(expandedRubricReasons);
    if (next.has(sectionKey)) next.delete(sectionKey);
    else next.add(sectionKey);
    expandedRubricReasons = next;
  }

  function openAIFeedback(anchor) {
    feedbackDialogAnchor = anchor;
    feedbackDialogOpen = true;
    loadAIFeedback();
  }

  async function handleQuestionProposal() {
    if (!onQuestionProposal) return;
    const message = questionFeedback.trim();
    if (!message) {
      showError('Add feedback before questioning this proposal.');
      return;
    }

    questionSubmitting = true;
    try {
      await onQuestionProposal(submission.id, message);
      questionFeedback = '';
      showQuestionForm = false;
      queueMicrotask(() => questionTrigger?.focus());
    } catch {
      // Parent reports the error; keep the form open so feedback is not lost.
    } finally {
      questionSubmitting = false;
    }
  }

  function openQuestionDialog() {
    if (!canQuestionProposal) return;
    showQuestionForm = true;
    queueMicrotask(() => questionTextarea?.focus());
  }

  function closeQuestionDialog() {
    if (questionSubmitting) return;
    showQuestionForm = false;
    questionFeedback = '';
    queueMicrotask(() => questionTrigger?.focus());
  }

  function handleQuestionDialogKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeQuestionDialog();
      return;
    }
    if (event.key !== 'Tab' || !questionDialogElement) return;
    const focusable = [...questionDialogElement.querySelectorAll(
      'button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'
    )];
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  /** @param {boolean} [force] */
  async function loadAIFeedback(force = false) {
    if (!submission.ai_analysis || aiFeedbackLoading) return null;
    if (aiFeedbackLoaded && !force) return aiFeedbackRecords;

    const contextKey = `${submission.id}:${submission.ai_analysis.id ?? 'none'}`;
    const requestId = ++aiFeedbackRequestId;
    aiFeedbackLoading = true;
    aiFeedbackError = '';

    try {
      const response = await stewardAPI.getAIFeedback(submission.id);
      if (requestId !== aiFeedbackRequestId || contextKey !== aiFeedbackContextKey) return;
      const records = Array.isArray(response.data)
        ? response.data
        : response.data?.results || [];
      aiFeedbackRecords = records;
      aiFeedbackLoaded = true;
      return records;
    } catch (error) {
      if (requestId !== aiFeedbackRequestId || contextKey !== aiFeedbackContextKey) return;
      const requestError = /** @type {any} */ (error);
      if (requestError.response?.status === 403) {
        aiFeedbackRecords = [];
        aiFeedbackLoaded = true;
        aiFeedbackError = '';
        return [];
      }
      aiFeedbackError = 'Could not load steward feedback.';
      showError('Failed to load AI review feedback: ' + (
        requestError.response?.data?.detail || requestError.message
      ));
      return null;
    } finally {
      if (requestId === aiFeedbackRequestId && contextKey === aiFeedbackContextKey) {
        aiFeedbackLoading = false;
      }
    }
  }

  /** @param {Record<string, any>} record */
  function handleAIFeedbackSaved(record) {
    if (!record) return;
    const existingIndex = aiFeedbackRecords.findIndex(item =>
      item.id === record.id || (
        String(item.review_proposal_id) === String(record.review_proposal_id) &&
        String(item.reviewer_id) === String(record.reviewer_id)
      )
    );
    if (existingIndex === -1) {
      aiFeedbackRecords = [record, ...aiFeedbackRecords];
    } else {
      aiFeedbackRecords = aiFeedbackRecords.map((item, index) => index === existingIndex ? record : item);
    }
    aiFeedbackLoaded = true;
    aiFeedbackError = '';
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

{#snippet socialLinks(user)}
  {#if user}
    {#each SOCIAL_PLATFORMS as platform}
      {@const connection = user[platform.key]}
      {#if connection?.platform_username}
        {#if platform.profileUrl}
          <a
            href={platform.profileUrl(connection.platform_username)}
            target="_blank"
            rel="noopener noreferrer"
            class="social-link"
            style="--social-color: {platform.color}"
            aria-label="{platform.label}: @{connection.platform_username}"
            title="{platform.label}: @{connection.platform_username}"
          >
            <span class="social-link-icon">{@html platform.icon}</span>
            <span class="social-link-name">{connection.platform_username}</span>
          </a>
        {:else}
          <span
            class="social-link social-link-static"
            style="--social-color: {platform.color}"
            aria-label="{platform.label}: {connection.platform_username}"
            title="{platform.label}: {connection.platform_username}"
          >
            <span class="social-link-icon">{@html platform.icon}</span>
            <span class="social-link-name">{connection.platform_username}</span>
          </span>
        {/if}
      {/if}
    {/each}
  {/if}
{/snippet}

{#snippet compactProjectRubric()}
  <section class="-mx-4 overflow-hidden border-y border-slate-200 bg-white">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-50 px-4 py-3">
        <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-2">
          <h4 class="text-sm font-semibold text-slate-950">Project rubric</h4>
          <span class="rounded-md bg-white px-2 py-1 text-xs font-semibold tabular-nums text-slate-700 shadow-[0_0_0_1px_rgba(15,23,42,0.10)]">
            {points} pts
          </span>
          <span class="rounded-md px-2 py-1 text-xs font-semibold {isProposalRubric ? 'bg-amber-100 text-amber-800' : 'bg-slate-200 text-slate-700'}">
            {isProposalRubric ? 'Proposal rubric' : 'Final review'}
          </span>
        </div>
      </div>
      {#if submission.ai_analysis && canFileFeedback}
        <button
          type="button"
          onclick={() => openAIFeedback('decision')}
          class="inline-flex min-h-10 items-center gap-2 rounded-md px-3 text-xs font-semibold text-sky-800 hover:bg-sky-100 active:scale-[0.96] transition-[background-color,transform]"
        >
          <Icons name="sparkle" size="xs" />
          {hasAIAnchorFeedback('decision') ? 'Edit AI decision feedback' : 'Review AI decision'}
        </button>
      {/if}
    </div>

    {#if reviewAction !== 'reject' && hasRubricGateFailures}
      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-red-200 bg-red-50 px-4 py-3">
        <p class="text-xs font-medium text-red-800">
          The loaded proposal contains gate failures. Clear them before submitting {actionLabel(reviewAction).toLowerCase()}.
        </p>
        <button
          type="button"
          onclick={clearRubricGates}
          class="min-h-10 rounded-md px-3 text-xs font-semibold text-red-800 hover:bg-red-100 active:scale-[0.96]"
        >
          Clear gate failures
        </button>
      </div>
    {/if}

    {#if reviewAction === 'reject'}
      <fieldset class="border-t border-slate-200 px-4 py-3">
        <legend class="sr-only">Project gate failures</legend>
        <p class="mb-2 text-xs font-semibold uppercase text-red-800">Gate failures</p>
        <div class="grid gap-2 sm:grid-cols-2">
          {#each RUBRIC_GATE_FAILURES as gate}
            <label class="flex min-h-10 cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-xs font-medium shadow-[0_0_0_1px_rgba(15,23,42,0.10)] {rubricGateFailures.includes(gate.key) ? 'bg-red-50 text-red-800' : 'bg-white text-slate-700 hover:bg-slate-50'}">
              <input
                type="checkbox"
                checked={rubricGateFailures.includes(gate.key)}
                onchange={() => toggleRubricGate(gate.key)}
                class="h-4 w-4 rounded border-slate-300 text-red-600 focus:ring-red-500"
              />
              <span>{gate.label}</span>
            </label>
          {/each}
        </div>
      </fieldset>
    {/if}

    <div class="divide-y divide-slate-200 border-t border-slate-200">
      {#each RUBRIC_SECTIONS as section}
        {@const sectionReason = getRubricSectionReason(section.key)}
        {@const aiSection = submission.ai_analysis?.sections?.[section.key]}
        <div class="px-4 py-3">
          <div class="grid items-center gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <label
                  for="steward-rubric-score-{submission.id}-{section.key}"
                  class="text-sm font-semibold text-slate-900"
                >
                  {section.label}
                </label>
                {#if aiSection}
                  <span class="rounded-md bg-sky-50 px-2 py-0.5 text-xs font-semibold tabular-nums text-sky-800">
                    AI {aiSection.score}/5
                  </span>
                {/if}
                {#if sectionReason}
                  <span class="text-xs font-medium text-emerald-700">Reason saved</span>
                {/if}
                {#if hasAIAnchorFeedback(section.key)}
                  <span class="text-xs font-medium text-amber-700">AI feedback saved</span>
                {/if}
              </div>
              {#if !isProposalRubric && sectionReason}
                <p class="mt-1 line-clamp-copy text-xs text-slate-600">{sectionReason}</p>
              {:else}
                <p class="mt-1 text-xs text-slate-500">{section.help}</p>
              {/if}
            </div>

            <select
              id="steward-rubric-score-{submission.id}-{section.key}"
              value={rubricSections[section.key]?.score ?? 0}
              onchange={(event) => updateRubricScore(section.key, event.currentTarget.value)}
              class="h-10 w-24 rounded-md bg-white px-2 text-sm font-semibold tabular-nums text-slate-900 shadow-[0_0_0_1px_rgba(15,23,42,0.16)] focus:outline-none focus:ring-2 focus:ring-slate-400"
            >
              {#each [0, 1, 2, 3, 4, 5] as scoreValue}
                <option value={scoreValue}>{scoreValue}/5</option>
              {/each}
            </select>

            <div class="flex items-center justify-end gap-1">
              {#if isProposalRubric}
                <button
                  type="button"
                  onclick={() => toggleRubricReason(section.key)}
                  aria-expanded={expandedRubricReasons.has(section.key)}
                  aria-controls="rubric-reason-{submission.id}-{section.key}"
                  class="min-h-10 rounded-md px-3 text-xs font-semibold text-slate-700 hover:bg-slate-100 active:scale-[0.96] transition-[background-color,transform]"
                >
                  {sectionReason ? 'Edit reason' : 'Add reason'}
                </button>
              {/if}
              {#if aiSection && canFileFeedback}
                <button
                  type="button"
                  onclick={() => openAIFeedback(section.key)}
                  class="min-h-10 rounded-md px-3 text-xs font-semibold text-sky-800 hover:bg-sky-100 active:scale-[0.96] transition-[background-color,transform]"
                >
                  {hasAIAnchorFeedback(section.key) ? 'Edit AI feedback' : 'Flag AI issue'}
                </button>
              {/if}
            </div>
          </div>

          {#if isProposalRubric && expandedRubricReasons.has(section.key)}
            <div id="rubric-reason-{submission.id}-{section.key}" class="mt-3">
              <label for="rubric-reason-input-{submission.id}-{section.key}" class="sr-only">
                {section.label} reason
              </label>
              <textarea
                id="rubric-reason-input-{submission.id}-{section.key}"
                value={rubricSections[section.key]?.reason || ''}
                oninput={(event) => updateRubricReason(section.key, event.currentTarget.value)}
                rows="2"
                maxlength="1000"
                placeholder="Optional reviewer rationale"
                class="w-full resize-y rounded-md bg-white px-3 py-2 text-sm text-slate-800 shadow-[0_0_0_1px_rgba(15,23,42,0.16)] focus:outline-none focus:ring-2 focus:ring-slate-400"
              ></textarea>
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <details class="border-t border-slate-200 px-4 py-3">
      <summary class="flex min-h-10 cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-slate-800">
        <span>Verified extras</span>
        <span class="text-xs font-medium text-slate-500">
          {rubricExtras.length} selected
        </span>
      </summary>
      <div class="mt-2 flex flex-wrap gap-2">
        {#each RUBRIC_EXTRAS as extra}
          <label class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-md bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-[0_0_0_1px_rgba(15,23,42,0.12)] hover:bg-slate-50">
            <input
              type="checkbox"
              checked={rubricExtras.includes(extra.key)}
              onchange={() => toggleRubricExtra(extra.key)}
              class="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
            />
            <span>{extra.label}</span>
          </label>
        {/each}
      </div>
    </details>

    {#if isProposalRubric}
      <div class="border-t border-slate-200 px-4 py-3">
        <label for="rubric-overall-{submission.id}" class="mb-1 block text-sm font-semibold text-slate-900">
          Overall reason <span class="text-red-600">*</span>
        </label>
        <textarea
          id="rubric-overall-{submission.id}"
          bind:value={rubricOverallReason}
          rows="3"
          maxlength="2000"
          placeholder="Summarize why this outcome should be proposed."
          class="w-full resize-y rounded-md bg-white px-3 py-2 text-sm text-slate-800 shadow-[0_0_0_1px_rgba(15,23,42,0.16)] focus:outline-none focus:ring-2 focus:ring-amber-400"
        ></textarea>
      </div>
    {:else if rubricOverallReason}
      <div class="border-t border-slate-200 px-4 py-3">
        <p class="text-xs font-semibold uppercase text-slate-500">Proposal rationale</p>
        <p class="mt-1 whitespace-pre-wrap text-sm text-slate-700">{rubricOverallReason}</p>
      </div>
    {/if}
  </section>
{/snippet}

<article class="overflow-hidden rounded-lg border-l-4 bg-white shadow-[0_10px_30px_rgba(15,23,42,0.08),0_0_0_1px_rgba(15,23,42,0.06)] {getStateBorderClass(submission.state)}">
  <header class="border-b border-slate-200 px-4 py-4 sm:px-5">
    <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div class="min-w-0">
        <div class="flex min-w-0 items-start gap-3">
          {#if submission.user_details?.id || submission.user_details?.address}
            <a
              href="/participant/{submission.user_details?.id ?? submission.user_details?.address}"
              class="flex min-w-0 items-center gap-3 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label="View {submission.user_details?.name || 'submitter'} profile"
            >
              <Avatar user={submission.user_details} size="md" clickable={false} />
              <span class="min-w-0">
                <span class="block truncate text-base font-semibold text-slate-950">
                  {submission.user_details?.name || submission.user_details?.address?.slice(0, 10) + '...'}
                </span>
                <span class="block text-xs font-medium text-primary-700">View profile</span>
              </span>
            </a>
          {:else}
            <Avatar user={submission.user_details} size="md" clickable={false} />
            <span class="truncate text-base font-semibold text-slate-950">
              {submission.user_details?.name || 'Unknown submitter'}
            </span>
          {/if}
        </div>

        <div class="mt-2 flex flex-wrap items-center gap-2 pl-0 sm:pl-[3.25rem]">
          {@render socialLinks(submission.user_details)}
          <span class="text-xs text-slate-500">Submitted {formatDate(submission.created_at)}</span>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 xl:justify-end">
        <button
          type="button"
          onclick={handleCopySubmissionId}
          disabled={copyingSubmissionId}
          class="inline-flex min-h-10 items-center gap-2 rounded-md px-3 text-xs font-semibold text-slate-700 hover:bg-slate-100 active:scale-[0.96] disabled:opacity-50 transition-[background-color,transform]"
          title="Copy submission ID"
        >
          <Icons name="document" size="xs" />
          {copyingSubmissionId ? 'Copying' : 'Copy ID'}
        </button>

        {#if onToggleInteresting}
          <label class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-md px-3 text-xs font-semibold {submission.is_interesting ? 'bg-violet-50 text-violet-800' : 'text-slate-600 hover:bg-slate-100'}">
            <input
              type="checkbox"
              checked={submission.is_interesting}
              disabled={togglingInteresting}
              onchange={handleToggleInteresting}
              class="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
            />
            <span>{submission.is_interesting ? 'Interesting' : 'Mark interesting'}</span>
          </label>
        {/if}

        {#if submission.has_proposal}
          <span class="rounded-md px-2.5 py-1 text-xs font-semibold {isProposalQuestioned ? 'bg-orange-100 text-orange-800' : 'bg-amber-100 text-amber-800'}">
            {isProposalQuestioned ? 'Proposal questioned' : 'Proposal'}
          </span>
        {/if}
        {#if submission.has_appeal}
          <span class="rounded-md bg-orange-100 px-2.5 py-1 text-xs font-semibold text-orange-800">Appealed</span>
        {/if}
        <span class="rounded-md px-2.5 py-1 text-xs font-semibold {getStateClass(submission.state)}">
          {submission.state_display}
        </span>
      </div>
    </div>
  </header>

  <div class="grid gap-0 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
    <section class="min-w-0 space-y-4 border-b border-slate-200 p-4 sm:p-5 lg:border-b-0 lg:border-r">
      <dl class="grid gap-3 sm:grid-cols-2">
        <div>
          <dt class="text-xs font-semibold uppercase text-slate-500">Contribution type</dt>
          <dd class="mt-1 text-sm font-medium text-slate-900">
            {submission.contribution_type_details?.name || getTypeName(submission.contribution_type)}
            <span class="ml-1 font-normal tabular-nums text-slate-500">
              {submission.contribution_type_details?.min_points}-{submission.contribution_type_details?.max_points} pts
            </span>
          </dd>
        </div>
        {#if submission.mission}
          <div>
            <dt class="text-xs font-semibold uppercase text-slate-500">Mission</dt>
            <dd class="mt-1 text-sm font-medium text-slate-900">{submission.mission.name}</dd>
          </div>
        {/if}
      </dl>

      {#if submission.project_contribution}
        <div class="border-t border-slate-200 pt-3">
          <p class="text-xs font-semibold uppercase text-slate-500">Linked project</p>
          <div class="mt-1 flex flex-wrap items-center gap-2">
            <span class="text-sm font-medium text-slate-900">{submission.project_contribution.title}</span>
            {#if isMilestoneSubmission && submission.milestone_version}
              <span class="rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
                Milestone v{submission.milestone_version}
              </span>
            {/if}
            {#if submission.project_contribution.link}
              <a href={submission.project_contribution.link} class="inline-flex min-h-10 items-center text-xs font-semibold text-primary-700 hover:underline">
                View project
              </a>
            {/if}
            {#if submission.project_contribution.github_url}
              <a
                href={submission.project_contribution.github_url}
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex min-h-10 items-center gap-1 text-xs font-semibold text-primary-700 hover:underline"
              >
                Repository <Icons name="externalLink" size="xs" />
              </a>
            {/if}
          </div>
        </div>
      {/if}

      {#if hasDistinctContributionDate}
        <div class="overflow-hidden rounded-lg shadow-[0_0_0_1px_rgba(15,23,42,0.10)]">
          <button
            type="button"
            onclick={() => moreDetailsExpanded = !moreDetailsExpanded}
            aria-expanded={moreDetailsExpanded}
            aria-controls="submission-more-details-{submission.id}"
            class="flex min-h-10 w-full items-center justify-between gap-3 px-3 text-left text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <span>More details</span>
            <Icons name="chevronDown" size="sm" className="transition-transform {moreDetailsExpanded ? 'rotate-180' : ''}" />
          </button>
          {#if moreDetailsExpanded}
            <div id="submission-more-details-{submission.id}" class="border-t border-slate-200 px-3 py-2">
              <p class="text-xs font-semibold uppercase text-slate-500">Contribution date</p>
              <p class="mt-1 text-sm text-slate-800">{formatDate(submission.contribution_date)}</p>
            </div>
          {/if}
        </div>
      {/if}

      {#if submission.notes}
        <div class="overflow-hidden rounded-lg shadow-[0_0_0_1px_rgba(15,23,42,0.10)]">
          <button
            type="button"
            onclick={() => submissionNotesExpanded = !submissionNotesExpanded}
            aria-expanded={submissionNotesExpanded}
            aria-controls="submission-notes-{submission.id}"
            aria-label="{submissionNotesExpanded ? 'Hide' : 'Show'} submission notes"
            class="flex min-h-11 w-full items-center justify-between gap-3 px-3 text-left hover:bg-slate-50"
          >
            <span class="text-sm font-semibold text-slate-900">Submission notes</span>
            <Icons name="chevronDown" size="sm" className="text-slate-500 transition-transform {submissionNotesExpanded ? 'rotate-180' : ''}" />
          </button>
          {#if submissionNotesExpanded}
            <div id="submission-notes-{submission.id}" class="markdown-content border-t border-slate-200 px-3 py-3 text-sm text-slate-800">
              {@html parseUserMarkdown(submission.notes)}
            </div>
          {:else}
            <p class="notes-preview whitespace-pre-line px-3 pb-3 text-sm text-slate-600">
              {submission.notes}
            </p>
          {/if}
        </div>
      {/if}

      {#if submission.has_appeal && submission.appeal_reason}
        <div class="rounded-lg bg-orange-50 p-3 shadow-[0_0_0_1px_rgba(234,88,12,0.20)]">
          <p class="text-xs font-semibold uppercase text-orange-800">Appeal reason</p>
          <p class="mt-1 whitespace-pre-wrap text-sm text-orange-950">{submission.appeal_reason}</p>
        </div>
      {/if}

      {#if moreInfoRequests.length > 0}
        <div class="rounded-lg bg-sky-50 p-3 shadow-[0_0_0_1px_rgba(2,132,199,0.18)]">
          <div class="flex items-center justify-between gap-2">
            <p class="text-xs font-semibold uppercase text-sky-800">Information requests</p>
            <span class="text-xs font-semibold tabular-nums text-sky-700">{moreInfoRequests.length}</span>
          </div>
          <div class="mt-2 divide-y divide-sky-200">
            {#each moreInfoRequests as request, index (request.id || index)}
              <div class="py-2 first:pt-0 last:pb-0">
                <div class="markdown-content text-sm text-sky-950">{@html parseMarkdown(request.message)}</div>
                {#if request.user_name || request.created_at}
                  <p class="mt-1 text-xs text-sky-700">
                    {request.user_name ? 'Requested by ' + request.user_name : 'Requested'}
                    {request.created_at ? ' on ' + formatDate(request.created_at) : ''}
                  </p>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if submission.evidence_items?.length > 0}
        <div class="border-t border-slate-200 pt-3">
          <h4 class="text-sm font-semibold text-slate-900">Evidence</h4>
          {#if urlEvidence.length > 0}
            <div class="mt-2 space-y-2">
              {#each urlEvidence as evidence}
                <EvidenceUrlCard {evidence} compact={true} />
              {/each}
            </div>
          {/if}
          {#if textOnlyEvidence.length > 0}
            <ul class="mt-2 space-y-1">
              {#each textOnlyEvidence as evidence}
                <li class="text-sm text-slate-600">{evidence.description}</li>
              {/each}
            </ul>
          {/if}
        </div>
      {/if}

      {#if showStaffResponse}
        <div class="rounded-lg bg-slate-50 p-3">
          <p class="text-xs font-semibold uppercase text-slate-500">Staff response</p>
          <div class="markdown-content mt-1 text-sm text-slate-700">{@html parseMarkdown(submission.staff_reply)}</div>
        </div>
      {/if}

      <div class="overflow-hidden rounded-lg shadow-[0_0_0_1px_rgba(15,23,42,0.10)]">
        <button
          type="button"
          onclick={() => internalNotesExpanded = !internalNotesExpanded}
          aria-expanded={internalNotesExpanded}
          aria-controls="internal-notes-{submission.id}"
          aria-label="{internalNotesExpanded ? 'Hide' : 'Show'} internal notes"
          class="flex min-h-11 w-full items-center justify-between gap-3 px-3 text-left hover:bg-slate-50"
        >
          <span class="text-sm font-semibold text-slate-900">Internal notes</span>
          <span class="flex items-center gap-2">
            {#if (submission.notes_count || notes.length) > 0}
              <span class="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold tabular-nums text-slate-600">
                {submission.notes_count || notes.length}
              </span>
            {/if}
            <Icons name="chevronDown" size="sm" className="text-slate-500 transition-transform {internalNotesExpanded ? 'rotate-180' : ''}" />
          </span>
        </button>
        {#if internalNotesExpanded}
          <div id="internal-notes-{submission.id}" class="border-t border-slate-200">
            <CRMNotesPanel
              submissionId={submission.id}
              {notes}
              loading={notesLoading}
              {onAddNote}
              {onUpdateNote}
              {activeProposalNoteId}
              embedded={true}
            />
          </div>
        {/if}
      </div>
    </section>

    <section class="min-w-0 space-y-4 bg-slate-50/50 p-4 sm:p-5">
      {#if isOpenReviewState}
        {#if showAIProposal}
          <AIReviewSummary
            {submission}
            aiAnalysis={submission.ai_analysis}
            feedbackRecords={aiFeedbackRecords}
            feedbackLoading={aiFeedbackLoading}
            feedbackLoaded={aiFeedbackLoaded}
            feedbackError={aiFeedbackError}
            {canFileFeedback}
            {currentUserId}
            onRequestFeedback={loadAIFeedback}
            onSaved={handleAIFeedbackSaved}
            onOpenFeedback={openAIFeedback}
          />
        {:else if showHumanProposal}
          <section class="rounded-lg bg-white p-3 shadow-[0_0_0_1px_rgba(217,119,6,0.24)]">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-xs font-semibold uppercase text-amber-700">
                  {isProposalQuestioned ? 'Human proposal questioned' : 'Human proposal'}
                </p>
                <p class="mt-1 text-sm text-slate-800">
                  <span class="font-semibold">{submission.proposed_by_details?.name || 'A steward'}</span>
                  proposed <span class="font-semibold lowercase">{actionLabel(normalizeProposedAction(submission.proposed_action))}</span>
                  {#if submission.proposed_at}
                    <span class="text-slate-500"> on {formatDate(submission.proposed_at)}</span>
                  {/if}
                </p>
              </div>
              {#if canQuestionProposal}
                <button
                  bind:this={questionTrigger}
                  type="button"
                  onclick={openQuestionDialog}
                  class="min-h-10 rounded-md px-3 text-xs font-semibold text-orange-800 hover:bg-orange-50 active:scale-[0.96] transition-[background-color,transform]"
                >
                  Question proposal
                </button>
              {/if}
            </div>
            {#if isProposalQuestioned}
              <div class="mt-3 border-t border-orange-200 pt-3">
                <p class="text-xs font-semibold text-orange-800">
                  Feedback from {submission.proposal_questioned_by_details?.name || 'a steward'}
                  {submission.proposal_questioned_at ? ' on ' + formatDate(submission.proposal_questioned_at) : ''}
                </p>
                <p class="mt-1 whitespace-pre-wrap text-sm text-orange-950">{submission.proposal_review_feedback}</p>
              </div>
            {/if}
            {#if submission.ai_analysis && canFileFeedback}
              <AIReviewSummary
                controlsOnly={true}
                {submission}
                aiAnalysis={submission.ai_analysis}
                feedbackRecords={aiFeedbackRecords}
                feedbackLoading={aiFeedbackLoading}
                feedbackLoaded={aiFeedbackLoaded}
                feedbackError={aiFeedbackError}
                {canFileFeedback}
                {currentUserId}
                onRequestFeedback={loadAIFeedback}
                onSaved={handleAIFeedbackSaved}
                onOpenFeedback={openAIFeedback}
              />
            {/if}
          </section>
        {/if}

        {#if hasAnyAction}
          <section class="overflow-hidden rounded-lg bg-white shadow-[0_8px_24px_rgba(15,23,42,0.06),0_0_0_1px_rgba(15,23,42,0.08)]">
            <div class="border-b border-slate-200 px-4 pt-4">
              <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h3 class="text-sm font-semibold text-slate-950">Review outcome</h3>
                </div>
                <span class="rounded-md px-2.5 py-1 text-xs font-semibold {selectedSubmissionMode === 'proposal' ? 'bg-amber-100 text-amber-800' : 'bg-slate-900 text-white'}">
                  {selectedSubmissionMode === 'proposal' ? 'Submits a proposal' : 'Final decision'}
                </span>
              </div>

              <div
                class="grid gap-1 {availableOutcomes.length === 1 ? 'grid-cols-1' : availableOutcomes.length === 2 ? 'grid-cols-2' : 'grid-cols-3'}"
                role="group"
                aria-label="Review outcome"
              >
                {#each availableOutcomes as outcome}
                  <button
                    type="button"
                    aria-pressed={reviewAction === outcome}
                    title="{actionLabel(outcome)} will be submitted as {submissionModeFor(outcome) === 'proposal' ? 'a proposal' : 'a final decision'}"
                    onclick={() => selectOutcome(outcome)}
                    class="min-h-11 rounded-t-md px-2 text-sm font-semibold transition-colors {reviewAction === outcome ? (outcome === 'accept' ? 'bg-emerald-600 text-white' : outcome === 'reject' ? 'bg-red-600 text-white' : 'bg-sky-600 text-white') : 'text-slate-600 hover:bg-slate-100'}"
                  >
                    {actionLabel(outcome)}
                  </button>
                {/each}
              </div>
            </div>

            <div class="space-y-4 p-4">
              {#if showProjectRubric}
                {@render compactProjectRubric()}
              {/if}

              {#if showAwardEditor}
                <section class="space-y-4 border-t border-slate-200 pt-4">
                  <div class="flex flex-wrap items-end gap-3">
                    <div class="min-w-[15rem] flex-1">
                      <p class="mb-1 text-xs font-semibold uppercase text-slate-500">Assign contribution to</p>
                      <div class="flex items-center gap-2">
                        <Avatar user={selectedUserDetails} size="sm" />
                        {#if showUserPicker && users.length > 0}
                          <select
                            bind:value={selectedUser}
                            class="h-10 min-w-0 flex-1 rounded-md bg-white px-3 text-sm text-slate-800 shadow-[0_0_0_1px_rgba(15,23,42,0.16)]"
                          >
                            {#each users as user}
                              <option value={user.id}>{user.display_name}</option>
                            {/each}
                          </select>
                        {:else}
                          <span class="min-w-0 flex-1 truncate text-sm font-medium text-slate-800">{selectedUserLabel}</span>
                          <button
                            type="button"
                            onclick={handleShowUserPicker}
                            disabled={usersLoading}
                            class="min-h-10 rounded-md px-3 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                          >
                            {usersLoading ? 'Loading' : 'Change'}
                          </button>
                        {/if}
                      </div>
                    </div>

                    <div>
                      <label for="points-input-{submission.id}" class="mb-1 block text-xs font-semibold uppercase text-slate-500">Points</label>
                      <div class="inline-flex h-10 items-stretch rounded-md bg-white shadow-[0_0_0_1px_rgba(15,23,42,0.16)]">
                        <button
                          type="button"
                          onclick={() => adjustPoints(points > 10 ? -5 : -1)}
                          class="w-10 text-lg font-semibold text-slate-600 hover:bg-slate-50 active:scale-[0.96]"
                          aria-label="Decrease points"
                        >-</button>
                        <input
                          id="points-input-{submission.id}"
                          type="number"
                          bind:value={points}
                          oninput={markPointsManuallyEdited}
                          class="w-16 border-x border-slate-200 text-center text-sm font-semibold tabular-nums text-slate-900 focus:outline-none"
                        />
                        <button
                          type="button"
                          onclick={() => adjustPoints(points > 10 ? 5 : 1)}
                          class="w-10 text-lg font-semibold text-slate-600 hover:bg-slate-50 active:scale-[0.96]"
                          aria-label="Increase points"
                        >+</button>
                      </div>
                    </div>

                    <div class="min-w-[6rem]">
                      <p class="mb-1 text-xs font-semibold uppercase text-slate-500">Final points</p>
                      <p class="text-xl font-semibold tabular-nums text-slate-950">{getFinalPoints()}</p>
                    </div>
                  </div>

                  <details class="rounded-lg bg-slate-50 p-3">
                    <summary class="min-h-10 cursor-pointer list-none text-sm font-semibold text-slate-800">
                      Contribution assignment settings
                    </summary>
                    <div class="mt-3">
                      <ContributionSelection
                        bind:selectedCategory
                        bind:selectedContributionType={selectedContributionTypeObj}
                        bind:selectedMission
                        defaultContributionType={selectedType}
                        defaultMission={submission.mission?.id}
                        onlySubmittable={false}
                        stewardMode={true}
                        providedContributionTypes={contributionTypes}
                        onSelectionChange={handleContributionSelectionChange}
                      />
                    </div>
                  </details>

                  {#if selectedSubmissionMode === 'final' && isSelectedMilestoneType}
                    <div class="rounded-lg bg-indigo-50 p-3 shadow-[0_0_0_1px_rgba(79,70,229,0.18)]">
                      <label for="project-contribution-{submission.id}" class="mb-2 block text-sm font-semibold text-indigo-950">
                        Related project <span class="text-red-600">*</span>
                      </label>
                      {#if acceptedProjectsLoading}
                        <p class="text-sm text-indigo-700">Loading accepted projects...</p>
                      {:else if acceptedProjectsError}
                        <p class="text-sm text-red-700">{acceptedProjectsError}</p>
                      {:else if acceptedProjects.length === 0}
                        <p class="text-sm text-amber-800">This user has no accepted project contributions.</p>
                      {:else}
                        <select
                          id="project-contribution-{submission.id}"
                          bind:value={selectedProject}
                          class="h-10 w-full rounded-md bg-white px-3 text-sm text-slate-900 shadow-[0_0_0_1px_rgba(79,70,229,0.20)]"
                        >
                          <option value="">Select accepted project...</option>
                          {#each acceptedProjects as project}
                            <option value={project.id}>{project.title} (next v{project.next_milestone_version || 1})</option>
                          {/each}
                        </select>
                      {/if}
                    </div>
                  {/if}

                  <details class="rounded-lg bg-yellow-50 p-3">
                    <summary class="flex min-h-10 cursor-pointer list-none items-center gap-2 text-sm font-semibold text-yellow-950">
                      <Icons name="star" size="sm" className="text-yellow-600" />
                      Feature this contribution
                    </summary>
                    <div class="mt-3 space-y-3">
                      <label class="flex min-h-10 items-center gap-2 text-sm font-medium text-yellow-950">
                        <input type="checkbox" bind:checked={createHighlight} class="h-4 w-4 rounded border-yellow-300 text-yellow-600" />
                        Create dashboard highlight
                      </label>
                      {#if createHighlight}
                        <input
                          type="text"
                          bind:value={highlightTitle}
                          placeholder="Feature title"
                          class="h-10 w-full rounded-md bg-white px-3 text-sm shadow-[0_0_0_1px_rgba(161,98,7,0.22)]"
                        />
                        <textarea
                          bind:value={highlightDescription}
                          placeholder="Why this contribution should be highlighted"
                          rows="3"
                          class="w-full resize-y rounded-md bg-white px-3 py-2 text-sm shadow-[0_0_0_1px_rgba(161,98,7,0.22)]"
                        ></textarea>
                      {/if}
                    </div>
                  </details>
                </section>
              {/if}

              <div>
                <label for="review-note-{submission.id}" class="mb-1 block text-sm font-semibold text-slate-900">
                  {reviewAction === 'reject' ? 'Rejection reason' : reviewAction === 'more_info' ? 'Information needed' : 'Reviewer note'}
                  {reviewAction === 'accept' ? ' (optional)' : ''}
                </label>
                {#if proposeContextTemplates.length > 0}
                  <select
                    aria-label="Select reviewer response template"
                    value={selectedTemplateId || ''}
                    onchange={handleTemplateSelect}
                    class="mb-2 h-10 w-full rounded-md bg-white px-3 text-sm text-slate-700 shadow-[0_0_0_1px_rgba(15,23,42,0.16)]"
                  >
                    <option value="">Select a template</option>
                    {#each proposeContextTemplates as template}
                      <option value={template.id}>{template.label}</option>
                    {/each}
                  </select>
                {/if}
                <textarea
                  id="review-note-{submission.id}"
                  bind:value={staffReply}
                  rows="3"
                  placeholder={reviewAction === 'reject' ? 'Explain why this submission should be rejected.' : reviewAction === 'more_info' ? 'Describe the information the submitter should provide.' : 'Add an optional note for the submitter.'}
                  class="w-full resize-y rounded-md bg-white px-3 py-2 text-sm text-slate-800 shadow-[0_0_0_1px_rgba(15,23,42,0.16)] focus:outline-none focus:ring-2 focus:ring-slate-400"
                ></textarea>
              </div>

              {#if successMessage}
                <p class="rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800" role="status">{successMessage}</p>
              {/if}

              <button
                type="button"
                onclick={handleSubmitOutcome}
                disabled={isProcessing || !selectedSubmissionMode}
                class="flex min-h-11 w-full items-center justify-center rounded-md px-4 text-sm font-semibold text-white shadow-sm active:scale-[0.96] disabled:cursor-not-allowed disabled:opacity-50 transition-[background-color,transform] {selectedSubmissionMode === 'proposal' ? 'bg-amber-600 hover:bg-amber-700' : reviewAction === 'accept' ? 'bg-emerald-600 hover:bg-emerald-700' : reviewAction === 'reject' ? 'bg-red-600 hover:bg-red-700' : 'bg-sky-600 hover:bg-sky-700'}"
              >
                {isProcessing ? 'Submitting...' : submitButtonLabel()}
              </button>
            </div>
          </section>
        {:else}
          <div class="rounded-lg bg-white p-4 text-sm text-slate-600 shadow-[0_0_0_1px_rgba(15,23,42,0.08)]">
            No review actions are available for this contribution type.
          </div>
        {/if}
      {:else if submission.state === 'accepted' && submission.contribution}
        <ContributionCard contribution={submission.contribution} submission={submission} showExpand={true} />

        {#if canEditAccepted && acceptedEdit}
          <section class="rounded-lg bg-white p-4 shadow-[0_0_0_1px_rgba(16,185,129,0.22)]">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h4 class="text-sm font-semibold text-slate-950">Accepted contribution settings</h4>
                <p class="mt-1 text-xs text-slate-500">
                  Saved: {submission.contribution.frozen_global_points ?? submission.contribution.points ?? 0} points
                </p>
              </div>
              {#if submission.contribution.highlight}
                <span class="rounded-md bg-yellow-100 px-2 py-1 text-xs font-semibold text-yellow-800">Featured</span>
              {/if}
            </div>
            <div class="mt-4 space-y-3">
              <label class="block text-sm font-semibold text-slate-800">
                Awarded points
                <input
                  type="number"
                  min="0"
                  value={acceptedEdit.points}
                  oninput={(event) => onAcceptedEditChange?.(submission.id, 'points', event.currentTarget.value === '' ? '' : event.currentTarget.valueAsNumber)}
                  disabled={acceptedUpdating}
                  class="mt-1 h-10 w-32 rounded-md bg-white px-3 tabular-nums shadow-[0_0_0_1px_rgba(15,23,42,0.16)]"
                />
              </label>
              <input
                type="text"
                value={acceptedEdit.highlight_title}
                oninput={(event) => onAcceptedEditChange?.(submission.id, 'highlight_title', event.currentTarget.value)}
                disabled={acceptedUpdating}
                placeholder="Feature title"
                class="h-10 w-full rounded-md bg-white px-3 text-sm shadow-[0_0_0_1px_rgba(15,23,42,0.16)]"
              />
              <textarea
                value={acceptedEdit.highlight_description}
                oninput={(event) => onAcceptedEditChange?.(submission.id, 'highlight_description', event.currentTarget.value)}
                disabled={acceptedUpdating}
                placeholder="Feature description"
                rows="3"
                class="w-full resize-y rounded-md bg-white px-3 py-2 text-sm shadow-[0_0_0_1px_rgba(15,23,42,0.16)]"
              ></textarea>
              <button
                type="button"
                onclick={() => onAcceptedUpdate?.(submission.id)}
                disabled={acceptedUpdating}
                class="min-h-11 w-full rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white hover:bg-emerald-700 active:scale-[0.96] disabled:opacity-50"
              >
                {acceptedUpdating ? 'Saving...' : 'Save accepted changes'}
              </button>
            </div>
          </section>
        {/if}
      {:else if submission.state === 'rejected' && submission.staff_reply}
        <div class="rounded-lg bg-red-50 p-4 shadow-[0_0_0_1px_rgba(220,38,38,0.18)]">
          <h4 class="text-sm font-semibold text-red-950">Rejection reason</h4>
          <div class="markdown-content mt-2 text-sm text-red-800">{@html parseMarkdown(submission.staff_reply)}</div>
        </div>
      {:else if submission.state === 'canceled'}
        <div class="rounded-lg bg-white p-4 text-sm text-slate-700 shadow-[0_0_0_1px_rgba(15,23,42,0.08)]">Canceled by user</div>
      {/if}
    </section>
  </div>
</article>

{#if showQuestionForm}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
    role="presentation"
    onclick={(event) => event.target === event.currentTarget && closeQuestionDialog()}
  >
    <div
      bind:this={questionDialogElement}
      role="dialog"
      aria-modal="true"
      aria-labelledby="question-proposal-title-{submission.id}"
      tabindex="-1"
      onkeydown={handleQuestionDialogKeydown}
      class="w-full max-w-lg overflow-hidden rounded-lg bg-white shadow-2xl"
    >
      <div class="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <h2 id="question-proposal-title-{submission.id}" class="text-base font-semibold text-slate-950">Question proposal</h2>
          <p class="mt-1 text-sm text-slate-600">Send focused feedback to the proposing steward.</p>
        </div>
        <button
          type="button"
          onclick={closeQuestionDialog}
          disabled={questionSubmitting}
          class="min-h-10 min-w-10 rounded-md text-xl text-slate-500 hover:bg-slate-100 active:scale-[0.96]"
          aria-label="Close question proposal dialog"
        >&times;</button>
      </div>
      <div class="px-5 py-4">
        <label for="question-proposal-{submission.id}" class="mb-1 block text-sm font-semibold text-slate-900">Feedback</label>
        <textarea
          bind:this={questionTextarea}
          id="question-proposal-{submission.id}"
          bind:value={questionFeedback}
          rows="5"
          maxlength="2000"
          placeholder="Explain what should be reconsidered or changed."
          class="w-full resize-y rounded-md bg-white px-3 py-2 text-sm text-slate-800 shadow-[0_0_0_1px_rgba(15,23,42,0.18)] focus:outline-none focus:ring-2 focus:ring-orange-400"
        ></textarea>
      </div>
      <div class="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">
        <button
          type="button"
          onclick={closeQuestionDialog}
          disabled={questionSubmitting}
          class="min-h-10 rounded-md px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100"
        >Cancel</button>
        <button
          type="button"
          onclick={handleQuestionProposal}
          disabled={questionSubmitting || !questionFeedback.trim()}
          class="min-h-10 rounded-md bg-orange-600 px-4 text-sm font-semibold text-white hover:bg-orange-700 active:scale-[0.96] disabled:opacity-50"
        >
          {questionSubmitting ? 'Sending...' : 'Question proposal'}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if submission.ai_analysis}
  <AIFeedbackDialog
    open={feedbackDialogOpen}
    anchor={feedbackDialogAnchor}
    {submission}
    aiAnalysis={submission.ai_analysis}
    feedbackRecords={aiFeedbackRecords}
    feedbackLoading={aiFeedbackLoading}
    feedbackLoaded={aiFeedbackLoaded}
    feedbackError={aiFeedbackError}
    {canFileFeedback}
    {currentUserId}
    onRequestFeedback={loadAIFeedback}
    onSaved={handleAIFeedbackSaved}
    onClose={() => feedbackDialogOpen = false}
  />
{/if}

<style>
  .markdown-content :global(ul) {
    list-style-type: disc;
    margin-left: 1.25rem;
  }

  .markdown-content :global(ol) {
    list-style-type: decimal;
    margin-left: 1.25rem;
  }

  .markdown-content :global(a) {
    color: rgb(3 105 161);
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .notes-preview {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .line-clamp-copy {
    display: -webkit-box;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 1;
  }

  .social-link {
    display: inline-flex;
    min-height: 2.5rem;
    max-width: 10rem;
    align-items: center;
    gap: 0.375rem;
    border-radius: 0.375rem;
    padding: 0 0.625rem;
    color: var(--social-color);
    background: color-mix(in srgb, var(--social-color) 9%, white);
    font-size: 0.6875rem;
    font-weight: 600;
    text-decoration: none;
  }

  a.social-link:hover {
    background: color-mix(in srgb, var(--social-color) 15%, white);
  }

  .social-link-icon {
    display: inline-flex;
    flex: 0 0 auto;
  }

  .social-link-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .social-link-static {
    cursor: default;
  }

  summary::-webkit-details-marker {
    display: none;
  }
</style>
