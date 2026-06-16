<script>
  import { onMount } from 'svelte';
  import { replace, querystring } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI, contributionsAPI, leaderboardAPI } from '../lib/api.js';
  import { stewardPermissions } from '../lib/stewardPermissions.js';
  import PaginationEnhanced from '../components/PaginationEnhanced.svelte';
  import SubmissionCard from '../components/SubmissionCard.svelte';
  import StewardSearchBar from '../components/StewardSearchBar.svelte';
  import { showSuccess, showError } from '../lib/toastStore';
  import { parseSearch } from '../lib/searchParser.js';
  import { searchToParams } from '../lib/searchToParams.js';
  import { prefetchMissions } from '../lib/missionsStore.js';

  let submissions = $state([]);
  let contributionTypes = $state([]);
  let users = $state([]);
  let usersLoading = $state(false);
  let usersLoaded = $state(false);
  let usersRequest = null;
  let loading = $state(true);
  let error = $state(null);
  let currentPage = $state(1);
  let totalCount = $state(0);
  let pageSize = $state(10);

  // Filters - Status dropdown + mission dropdown + search bar
  let stateFilter = $state('pending');
  let missions = $state([]);
  let searchQuery = $state('');
  let stewardsList = $state([]);
  let assigningSubmissions = $state(new Set());  // Track which submissions are being assigned
  let acceptedEdits = $state({});
  let updatingAccepted = $state(new Set());

  // Review states
  let processingSubmissions = $state(new Set());
  let multipliers = $state({});
  let reviewData = $state({});

  // Permissions & templates
  let permissionsMap = $state({});
  let templates = $state([]);
  const reviewPermissionActions = ['accept', 'reject', 'request_more_info'];
  let hasProposalPermission = $derived(
    Object.values(permissionsMap || {}).some(actions => actions.includes('propose'))
  );
  let hasReviewPermission = $derived(
    Object.values(permissionsMap || {}).some(actions =>
      reviewPermissionActions.some(action => actions.includes(action))
    )
  );
  let proposalOnlyMode = $derived(hasProposalPermission && !hasReviewPermission);
  let rejectTemplates = $derived(templates.filter(t => t.action === 'reject'));

  // CRM Notes state - keyed by submission ID
  let submissionNotes = $state({});
  let notesLoading = $state({});
  let submissionsRequestId = 0;
  let notesBatchRequestId = 0;
  const NOTES_CONCURRENCY = 4;

  // Bulk selection state
  let selectedSubmissions = $state(new Set());
  let showRejectDialog = $state(false);
  let rejectMessage = $state('');
  let bulkRejecting = $state(false);

  onMount(async () => {
    if (!$authState.isAuthenticated) {
      replace('/');
      return;
    }

    // Sync filters from URL
    const params = new URLSearchParams($querystring);
    if (params.has('status')) stateFilter = params.get('status');
    if (params.has('q')) searchQuery = params.get('q');

    // Prefetch missions for both categories to warm the cache
    // This prevents duplicate API calls from individual SubmissionCard components
    prefetchMissions([
      { is_active: true, category: 'validator' },
      { is_active: true, category: 'builder' },
      { include_inactive: true }  // Also prefetch all missions for defaultMission lookups
    ]);

    // Load permissions and templates in parallel with other data
    await Promise.all([
      loadPermissions(),
      loadTemplates(),
      loadContributionTypes(),
      loadStewards(),
      loadMissions()
    ]);
    await loadSubmissions();
  });

  async function loadPermissions() {
    try {
      await stewardPermissions.load();
      // Subscribe to get the current value
      stewardPermissions.subscribe(value => {
        permissionsMap = value;
      })();
    } catch (err) {
      // Error loading permissions silently handled
    }
  }

  async function loadTemplates() {
    try {
      const response = await stewardAPI.getTemplates();
      templates = response.data || [];
    } catch (err) {
      // Error loading templates silently handled
    }
  }

  async function loadUsers() {
    if (usersLoaded) return users;
    if (usersRequest) return usersRequest;

    usersLoading = true;
    usersRequest = (async () => {
      try {
        const response = await stewardAPI.getUsers();
        users = response.data;
        usersLoaded = true;
        return users;
      } catch (err) {
        showError('Failed to load users: ' + (err.response?.data?.detail || err.message));
        return users;
      } finally {
        usersLoading = false;
        usersRequest = null;
      }
    })();

    return usersRequest;
  }

  async function ensureUsersLoaded() {
    try {
      return await loadUsers();
    } catch (err) {
      return users;
    }
  }

  async function loadStewards() {
    try {
      const response = await stewardAPI.getStewards();
      // Response is array with: { id, user_id, name, address, user_details }
      stewardsList = response.data;
    } catch (err) {
      // Error loading stewards silently handled
    }
  }

  async function loadMissions() {
    try {
      const response = await contributionsAPI.getMissions({ include_inactive: true, page_size: 100 });
      missions = response.data.results || response.data || [];
    } catch (err) {
      // Error loading missions silently handled
    }
  }

  async function handleAssignment(submissionId, stewardId) {
    assigningSubmissions.add(submissionId);
    assigningSubmissions = new Set(assigningSubmissions);

    try {
      const response = await stewardAPI.assignSubmission(submissionId, {
        steward_id: stewardId === 'unassigned' ? null : stewardId
      });

      // Update submission in-place
      const idx = submissions.findIndex(s => s.id === submissionId);
      if (idx !== -1) {
        if (stewardId === 'unassigned') {
          submissions[idx] = { ...submissions[idx], assigned_to: null };
        } else {
          submissions[idx] = response.data;
        }
        submissions = [...submissions];
      }
      showSuccess('Assignment updated');
    } catch (err) {
      showError('Failed to update assignment: ' + (err.response?.data?.error || err.message));
    } finally {
      assigningSubmissions.delete(submissionId);
      assigningSubmissions = new Set(assigningSubmissions);
    }
  }

  async function loadContributionTypes() {
    try {
      // Fetch all contribution types by setting a high page_size
      const response = await contributionsAPI.getContributionTypes({ page_size: 100 });
      contributionTypes = response.data.results || response.data;

      // Load active multipliers
      try {
        const multipliersRes = await leaderboardAPI.getActiveMultipliers();
        const activeMultipliers = multipliersRes.data;

        // Build multipliers map
        contributionTypes.forEach(type => {
          const multiplier = activeMultipliers.find(m => m.contribution_type === type.id);
          multipliers[type.id] = multiplier ? multiplier.multiplier_value : 1;
        });
      } catch (err) {
        // Default all to 1 if error
        contributionTypes.forEach(type => {
          multipliers[type.id] = 1;
        });
      }
    } catch (err) {
      // Error loading contribution types silently handled
    }
  }

  function updateURL() {
    const urlParams = new URLSearchParams();
    if (stateFilter) urlParams.set('status', stateFilter);
    if (searchQuery) urlParams.set('q', searchQuery);
    const newUrl = urlParams.toString() ? `?${urlParams.toString()}` : '';
    window.history.replaceState({}, '', `/stewards/submissions${newUrl}`);
  }

  async function loadSubmissions() {
    const requestId = ++submissionsRequestId;
    loading = true;
    error = null;
    clearSelection();

    try {
      if (proposalOnlyMode && stateFilter !== 'pending') {
        stateFilter = 'pending';
        currentPage = 1;
      }

      // Update URL with current filters
      updateURL();

      // Build API params from search query
      const parsed = parseSearch(searchQuery);
      const currentUserId = $userStore.user?.id;
      const params = searchToParams(parsed, {
        contributionTypes,
        stewardsList,
        currentUserId,
        templates,
        missions
      });

      // The dropdown is the default status filter. Only a positive search
      // status overrides it; negated statuses are additive exclusions.
      if (stateFilter && (!parsed.filters.status || parsed.filters.status.negated)) {
        params.state = stateFilter;
      }
      if (proposalOnlyMode) {
        params.state = 'pending';
        delete params.exclude_state;
      }

      params.page = currentPage;
      params.page_size = pageSize;

      const response = await stewardAPI.getSubmissions(params);
      if (requestId !== submissionsRequestId) return;

      const loadedSubmissions = response.data.results || [];
      submissions = loadedSubmissions;
      totalCount = response.data.count || 0;

      // If we got no results and we're not on page 1, it means this page doesn't exist anymore
      // Try going to the previous page
      if (submissions.length === 0 && currentPage > 1 && totalCount > 0) {
        currentPage = currentPage - 1;
        // Recursively call loadSubmissions with the new page
        return loadSubmissions();
      }

      // Initialize review data for each submission
      loadedSubmissions.forEach(sub => {
        if (!reviewData[sub.id]) {
          reviewData[sub.id] = {
            action: 'accept',
            user: sub.user,
            contribution_type: sub.contribution_type,
            points: sub.proposed_points || sub.contribution_type_details?.min_points || 0,
            staff_reply: '',
            create_highlight: false,
            highlight_title: '',
            highlight_description: ''
          };
        }
        if (sub.state === 'accepted' && sub.contribution && !acceptedEdits[sub.id]) {
          acceptedEdits[sub.id] = getAcceptedEditData(sub);
        }
      });
      acceptedEdits = { ...acceptedEdits };

      loadVisibleNotes(loadedSubmissions, requestId);
    } catch (err) {
      if (requestId !== submissionsRequestId) return;

      // If we get a 404 error and we're not on page 1, it might mean the page doesn't exist
      // Try going to the previous page
      if (err.response?.status === 404 && currentPage > 1) {
        currentPage = currentPage - 1;
        // Recursively call loadSubmissions with the new page
        return loadSubmissions();
      }

      // For other errors, show appropriate message
      error = err.response?.status === 403
        ? 'You do not have permission to access steward tools'
        : 'Failed to load submissions';
    } finally {
      if (requestId === submissionsRequestId) {
        loading = false;
      }
    }
  }

  async function loadVisibleNotes(visibleSubmissions, requestId) {
    const ids = visibleSubmissions
      .filter(sub =>
        (sub.state === 'pending' || sub.state === 'more_info_needed') &&
        (sub.notes_count ?? 0) > 0
      )
      .map(sub => sub.id);

    if (ids.length === 0) return;

    const batchId = ++notesBatchRequestId;
    const loadingUpdates = {};
    ids.forEach(id => {
      loadingUpdates[id] = true;
    });
    notesLoading = { ...notesLoading, ...loadingUpdates };

    const loadedNotes = {};
    const finishedLoading = {};
    let nextIndex = 0;

    async function loadNext() {
      while (nextIndex < ids.length) {
        const id = ids[nextIndex];
        nextIndex += 1;

        try {
          const response = await stewardAPI.getNotes(id);
          loadedNotes[id] = response.data || [];
        } catch (err) {
          loadedNotes[id] = [];
        } finally {
          finishedLoading[id] = false;
        }
      }
    }

    const workerCount = Math.min(NOTES_CONCURRENCY, ids.length);
    await Promise.all(Array.from({ length: workerCount }, loadNext));

    if (requestId !== submissionsRequestId || batchId !== notesBatchRequestId) return;

    submissionNotes = { ...submissionNotes, ...loadedNotes };
    notesLoading = { ...notesLoading, ...finishedLoading };
  }

  async function loadNotes(submissionId) {
    notesLoading[submissionId] = true;
    notesLoading = { ...notesLoading };
    try {
      const response = await stewardAPI.getNotes(submissionId);
      const list = response.data || [];
      submissionNotes[submissionId] = list;
      submissionNotes = { ...submissionNotes };
      return list;
    } catch (err) {
      submissionNotes[submissionId] = [];
      submissionNotes = { ...submissionNotes };
      return [];
    } finally {
      notesLoading[submissionId] = false;
      notesLoading = { ...notesLoading };
    }
  }

  async function handleToggleInteresting(submissionId, isInteresting) {
    try {
      const response = await stewardAPI.toggleInteresting(submissionId, isInteresting);
      const idx = submissions.findIndex(s => s.id === submissionId);
      if (idx !== -1) {
        submissions[idx] = response.data;
        submissions = [...submissions];
      }
    } catch (err) {
      showError('Failed to update flag: ' + (err.response?.data?.detail || err.message));
      throw err;
    }
  }

  async function handleAddNote(submissionId, message) {
    try {
      await stewardAPI.addNote(submissionId, message);
      // Reload notes for this submission
      await loadNotes(submissionId);
    } catch (err) {
      showError('Failed to add note: ' + (err.response?.data?.detail || err.message));
    }
  }

  /**
   * @param {string | number} submissionId
   * @param {string | number} noteId
   * @param {string} message
   */
  async function handleUpdateNote(submissionId, noteId, message) {
    try {
      await stewardAPI.updateNote(submissionId, noteId, message);
      await loadNotes(submissionId);
      showSuccess('Proposal note updated');
    } catch (err) {
      showError('Failed to update note: ' + (err.response?.data?.detail || err.response?.data?.error || err.message));
      throw err;
    }
  }

  async function handleReview(submissionId, data) {
    processingSubmissions.add(submissionId);
    processingSubmissions = new Set(processingSubmissions);

    try {
      const apiData = {
        action: data.action,
        staff_reply: data.staff_reply
      };

      if (data.template_id) {
        apiData.template_id = data.template_id;
      }
      if (data.rubric_review) {
        apiData.rubric_review = data.rubric_review;
      }

      if (data.action === 'accept') {
        apiData.points = parseInt(data.points);
        apiData.contribution_type = data.contribution_type;
        apiData.user = parseInt(data.user);
        if (data.project_contribution) {
          apiData.project_contribution = data.project_contribution;
        }

        if (data.create_highlight) {
          apiData.create_highlight = true;
          apiData.highlight_title = data.highlight_title;
          apiData.highlight_description = data.highlight_description;
        }
      }

      const response = await stewardAPI.reviewSubmission(submissionId, apiData);
      const updatedSub = response.data;

      // Show success message
      showSuccess(getSuccessMessage(data.action));

      // Update in-place: remove if state no longer matches filter, otherwise update
      if (!stateFilter || stateFilter === updatedSub.state) {
        const idx = submissions.findIndex(s => s.id === submissionId);
        if (idx !== -1) {
          submissions[idx] = updatedSub;
          if (updatedSub.state === 'accepted' && updatedSub.contribution) {
            acceptedEdits[submissionId] = getAcceptedEditData(updatedSub);
            acceptedEdits = { ...acceptedEdits };
          } else if (acceptedEdits[submissionId]) {
            delete acceptedEdits[submissionId];
            acceptedEdits = { ...acceptedEdits };
          }
          submissions = [...submissions];
        }
        // Reload notes since review creates a CRM note
        loadNotes(submissionId);
      } else {
        submissions = submissions.filter(s => s.id !== submissionId);
        totalCount = Math.max(0, totalCount - 1);
      }
    } catch (err) {
      showError('Failed to review submission: ' + (err.response?.data?.detail || err.message));
    } finally {
      processingSubmissions.delete(submissionId);
      processingSubmissions = new Set(processingSubmissions);
    }
  }

  function getAcceptedEditData(submission) {
    const highlight = submission.contribution?.highlight;
    return {
      points: submission.contribution?.points ?? 0,
      highlight_title: highlight?.title || '',
      highlight_description: highlight?.description || ''
    };
  }

  function canEditAcceptedSubmission(submission) {
    return permissionsMap[submission.contribution_type]?.includes('accept');
  }

  function handleAcceptedEditChange(submissionId, field, value) {
    if (!acceptedEdits[submissionId]) return;

    acceptedEdits[submissionId] = {
      ...acceptedEdits[submissionId],
      [field]: value
    };
    acceptedEdits = { ...acceptedEdits };
  }

  async function handleAcceptedUpdate(submissionId) {
    const data = acceptedEdits[submissionId];
    if (!data) return;

    const highlightTitle = data.highlight_title?.trim() || '';
    const highlightDescription = data.highlight_description?.trim() || '';
    const createHighlight = Boolean(highlightTitle || highlightDescription);
    const points = Number(data.points);

    if (!Number.isFinite(points) || !Number.isInteger(points)) {
      showError('Please enter a valid whole-number point value');
      return;
    }

    if (createHighlight && (!highlightTitle || !highlightDescription)) {
      showError('Feature title and description are both required');
      return;
    }

    updatingAccepted.add(submissionId);
    updatingAccepted = new Set(updatingAccepted);

    try {
      const response = await stewardAPI.updateAcceptedSubmission(submissionId, {
        points,
        create_highlight: createHighlight,
        remove_highlight: Boolean(submissions.find(s => s.id === submissionId)?.contribution?.highlight && !createHighlight),
        highlight_title: highlightTitle,
        highlight_description: highlightDescription
      });

      const idx = submissions.findIndex(s => s.id === submissionId);
      if (idx !== -1) {
        submissions[idx] = response.data;
        acceptedEdits[submissionId] = getAcceptedEditData(response.data);
        submissions = [...submissions];
        acceptedEdits = { ...acceptedEdits };
      }
      showSuccess('Accepted post updated');
    } catch (err) {
      showError('Failed to update accepted post: ' + (err.response?.data?.detail || err.message));
    } finally {
      updatingAccepted.delete(submissionId);
      updatingAccepted = new Set(updatingAccepted);
    }
  }

  async function handlePropose(submissionId, data) {
    processingSubmissions.add(submissionId);
    processingSubmissions = new Set(processingSubmissions);

    try {
      const response = await stewardAPI.proposeSubmission(submissionId, data);

      // Update submission in-place with proposal data
      const idx = submissions.findIndex(s => s.id === submissionId);
      if (idx !== -1) {
        submissions[idx] = response.data;
        submissions = [...submissions];
      }
      // Also reload notes since a proposal creates a CRM note
      loadNotes(submissionId);
      showSuccess('Proposal submitted successfully');
    } catch (err) {
      showError('Failed to submit proposal: ' + (err.response?.data?.detail || err.message));
    } finally {
      processingSubmissions.delete(submissionId);
      processingSubmissions = new Set(processingSubmissions);
    }
  }

  function getSuccessMessage(action) {
    switch(action) {
      case 'accept': return 'Submission accepted successfully';
      case 'reject': return 'Submission rejected';
      case 'more_info': return 'Information request sent';
      default: return 'Action completed';
    }
  }

  function handlePageChange(event) {
    currentPage = event.detail;
    loadSubmissions();
  }

  function handlePageSizeChange(event) {
    pageSize = event.detail;
    currentPage = 1; // Reset to first page
    loadSubmissions();
  }

  function handleFilterChange() {
    currentPage = 1;
    loadSubmissions();
  }

  function handleSearchChange(query) {
    searchQuery = query;
    currentPage = 1;
    loadSubmissions();
  }

  // Bulk selection handlers
  function toggleSubmissionSelection(submissionId) {
    if (selectedSubmissions.has(submissionId)) {
      selectedSubmissions.delete(submissionId);
    } else {
      selectedSubmissions.add(submissionId);
    }
    selectedSubmissions = new Set(selectedSubmissions);
  }

  function clearSelection() {
    selectedSubmissions = new Set();
  }

  function openRejectDialog() {
    if (selectedSubmissions.size === 0) return;
    rejectMessage = '';
    showRejectDialog = true;
  }

  function closeRejectDialog() {
    showRejectDialog = false;
    rejectMessage = '';
  }

  async function handleBulkReject() {
    if (!rejectMessage.trim()) {
      showError('Please enter a rejection message');
      return;
    }

    if (selectedSubmissions.size === 0) {
      showError('No submissions selected');
      return;
    }

    bulkRejecting = true;

    try {
      const response = await stewardAPI.bulkRejectSubmissions(
        Array.from(selectedSubmissions),
        rejectMessage.trim()
      );

      const rejectedCount = response.data.rejected_count;
      showSuccess(`Successfully rejected ${rejectedCount} submission(s)`);
      closeRejectDialog();

      // Remove rejected submissions from the local array
      const rejectedIds = response.data.rejected_ids || Array.from(selectedSubmissions);
      submissions = submissions.filter(s => !rejectedIds.includes(s.id));
      totalCount = Math.max(0, totalCount - rejectedCount);
      clearSelection();
    } catch (err) {
      showError('Failed to reject submissions: ' + (err.response?.data?.error || err.message));
    } finally {
      bulkRejecting = false;
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <div class="flex justify-between items-center mb-6">
    <div>
      <h1 class="text-2xl font-bold">Review Submissions</h1>
      <p class="text-sm text-gray-600 mt-1">Review and manage user contribution submissions</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white shadow rounded-lg p-4 mb-6">
    <div class="flex flex-col md:flex-row gap-4">
      <!-- Status Filter -->
      <div class="w-full md:w-48 flex-shrink-0">
        <label for="state-filter" class="block text-sm font-medium text-gray-700 mb-1">
          Status
        </label>
        <select
          id="state-filter"
          bind:value={stateFilter}
          onchange={handleFilterChange}
          disabled={proposalOnlyMode}
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          {#if proposalOnlyMode}
            <option value="pending">Pending Review</option>
          {:else}
            <option value="">All</option>
            <option value="pending">Pending Review</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="canceled">Canceled</option>
            <option value="more_info_needed">More Info Needed</option>
          {/if}
        </select>
      </div>

      <!-- Search Bar -->
      <div class="flex-1">
        <label for="search-bar" class="block text-sm font-medium text-gray-700 mb-1">
          Search
        </label>
        <StewardSearchBar
          bind:value={searchQuery}
          {contributionTypes}
          {stewardsList}
          {templates}
          {missions}
          onSearch={handleSearchChange}
          placeholder="Search URL or text, or type sort:-reviewed..."
        />
      </div>
    </div>

    <div class="mt-3 text-sm text-gray-600">
      Total: <span class="font-semibold text-gray-900">{totalCount}</span> submissions
    </div>
  </div>

  <!-- Bulk Action Bar -->
  {#if selectedSubmissions.size > 0}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex flex-wrap items-center gap-4">
      <div class="flex items-center gap-2">
        <span class="font-medium text-red-900">
          {selectedSubmissions.size} selected
        </span>
        <button
          onclick={clearSelection}
          class="text-sm text-red-600 hover:text-red-800 underline"
        >
          Clear
        </button>
      </div>

      <div class="flex-1 flex justify-end">
        <button
          onclick={openRejectDialog}
          class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 font-medium transition-colors"
        >
          Reject Selected
        </button>
      </div>
    </div>
  {/if}

  <!-- Bulk Reject Dialog -->
  {#if showRejectDialog}
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          Reject {selectedSubmissions.size} Submission{selectedSubmissions.size > 1 ? 's' : ''}
        </h3>

        <div class="mb-4">
          <label for="reject-message" class="block text-sm font-medium text-gray-700 mb-2">
            Rejection Message
          </label>
          {#if rejectTemplates.length > 0}
            <select
              onchange={(e) => {
                const tpl = templates.find(t => String(t.id) === e.target.value);
                if (tpl) rejectMessage = tpl.text;
                e.target.value = '';
              }}
              class="w-full px-3 py-1.5 mb-2 border border-gray-300 rounded-md text-sm bg-white text-gray-600"
            >
              <option value="">-- Select template --</option>
              {#each rejectTemplates as template}
                <option value={template.id}>{template.label}</option>
              {/each}
            </select>
          {/if}
          <textarea
            id="reject-message"
            bind:value={rejectMessage}
            rows="4"
            placeholder="Enter the reason for rejection..."
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
          ></textarea>
        </div>

        <div class="flex justify-end gap-3">
          <button
            onclick={closeRejectDialog}
            disabled={bulkRejecting}
            class="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onclick={handleBulkReject}
            disabled={bulkRejecting || !rejectMessage.trim()}
            class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {bulkRejecting ? 'Rejecting...' : `Reject ${selectedSubmissions.size} Submission${selectedSubmissions.size > 1 ? 's' : ''}`}
          </button>
        </div>
      </div>
    </div>
  {/if}

  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if error}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if submissions.length === 0}
    <div class="text-center py-12 bg-white rounded-lg shadow">
      <p class="text-gray-600">No submissions found matching your filters.</p>
    </div>
  {:else}
    <!-- Top Pagination -->
    {#if totalCount > 10}
      <div class="mb-4">
        <PaginationEnhanced
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 25, 50, 100]}
          showPageSize={true}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      </div>
    {/if}

    <div class="space-y-4">
      {#each submissions as submission (submission.id)}
        <div class="submission-row">
          {#if submission.state === 'pending' || submission.state === 'more_info_needed'}
            <div class="mb-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-4 py-2 shadow-sm">
              <label class="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={selectedSubmissions.has(submission.id)}
                  onchange={() => toggleSubmissionSelection(submission.id)}
                  class="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer"
                />
                <span>Select for bulk action</span>
              </label>

              <label class="flex items-center gap-2 text-sm text-gray-700">
                <span class="font-medium">Assigned to</span>
                <select
                  value={submission.assigned_to || 'unassigned'}
                  onchange={(e) => handleAssignment(submission.id, e.target.value)}
                  disabled={assigningSubmissions.has(submission.id)}
                  class="max-w-[220px] px-3 py-1 text-sm border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  title="Assign to steward"
                >
                  <option value="unassigned">Unassigned</option>
                  {#each stewardsList as steward}
                    <option value={steward.user_id}>
                      {steward.name || steward.address?.slice(0, 10) + '...'}
                    </option>
                  {/each}
                </select>
              </label>
            </div>
          {/if}

          <SubmissionCard
            {submission}
            showReviewForm={true}
            onReview={handleReview}
            onPropose={handlePropose}
            reviewData={reviewData[submission.id]}
            isProcessing={processingSubmissions.has(submission.id)}
            successMessage={''}
            {contributionTypes}
            {users}
            {usersLoading}
            {usersLoaded}
            {multipliers}
            isOwnSubmission={false}
            permissions={permissionsMap}
            {templates}
            notes={submissionNotes[submission.id] || []}
            notesLoading={notesLoading[submission.id] || false}
            onAddNote={handleAddNote}
            onUpdateNote={handleUpdateNote}
            onToggleInteresting={handleToggleInteresting}
            onRequestUsers={ensureUsersLoaded}
            currentUserId={$userStore.user?.id}
            acceptedEdit={acceptedEdits[submission.id] || null}
            canEditAccepted={Boolean(submission.state === 'accepted' && submission.contribution && acceptedEdits[submission.id] && canEditAcceptedSubmission(submission))}
            acceptedUpdating={updatingAccepted.has(submission.id)}
            onAcceptedEditChange={handleAcceptedEditChange}
            onAcceptedUpdate={handleAcceptedUpdate}
            enableRubricReview={true}
          />
        </div>
      {/each}
    </div>

    <!-- Bottom Pagination -->
    {#if totalCount > 10}
      <div class="mt-6">
        <PaginationEnhanced
          {currentPage}
          totalItems={totalCount}
          itemsPerPage={pageSize}
          pageSizeOptions={[10, 25, 50, 100]}
          showPageSize={false}
          on:pageChange={handlePageChange}
          on:pageSizeChange={handlePageSizeChange}
        />
      </div>
    {/if}
  {/if}
</div>

<style>
  .submission-row {
    content-visibility: auto;
    contain-intrinsic-size: 900px;
  }
</style>
