<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import ContributionCard from './ContributionCard.svelte';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';
  import Link from '../lib/components/Link.svelte';
  import Avatar from './Avatar.svelte';
  import Badge from './Badge.svelte';
  
  let {
    submission,
    showReviewForm = false,
    onReview = null,
    onCancel = null,
    reviewData = null,
    isProcessing = false,
    successMessage = '',
    contributionTypes = [],
    users = [],
    multipliers = {},
    isOwnSubmission = false
  } = $props();
  
  // State for review form
  let reviewAction = $state(reviewData?.action || 'accept');
  let selectedUser = $state(reviewData?.user || submission.user);
  let selectedType = $state(reviewData?.contribution_type || submission.contribution_type);
  let points = $state(reviewData?.points || submission.suggested_points || submission.contribution_type_details?.min_points || 0);
  let staffReply = $state(reviewData?.staff_reply || '');
  let createHighlight = $state(reviewData?.create_highlight || false);
  let highlightTitle = $state(reviewData?.highlight_title || '');
  let highlightDescription = $state(reviewData?.highlight_description || '');
  
  // For ContributionSelection component
  let selectedCategory = $state(submission.contribution_type_details?.category || 'validator');
  let selectedContributionTypeObj = $state(null);
  let selectedMission = $state(submission.mission || null);
  
  // Reset form when submission changes
  $effect(() => {
    if (submission) {
      // Only reset if no existing review data
      if (!reviewData) {
        reviewAction = 'accept';
        selectedUser = submission.user;
        selectedType = submission.contribution_type;
        points = submission.contribution_type_details?.min_points || 0;
        staffReply = '';
        createHighlight = false;
        highlightTitle = '';
        highlightDescription = '';
        selectedCategory = submission.contribution_type_details?.category || 'validator';
      }
    }
  });
  
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
    const type = contributionTypes.find(t => t.id === selectedType);
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
        highlight_description: highlightDescription
      };
      onReview(submission.id, data);
    }
  }
</script>

<div class="bg-white shadow-lg rounded-lg border-l-4 {getStateBorderClass(submission.state)}">
  <!-- Header -->
  <div class="px-6 py-4 border-b {getStateBackgroundClass(submission.state)}">
    <div class="flex justify-between items-start">
      <div>
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
      <span class="px-3 py-1 rounded-full text-sm font-medium {getStateClass(submission.state)}">
        {submission.state_display}
      </span>
    </div>
  </div>
  
  <!-- Content -->
  <div class="px-6 py-4">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:items-start">
      <!-- Left Column - Submission Details -->
      <div class="space-y-4">
        {#if !isOwnSubmission}
          <div>
            <h4 class="text-sm font-medium text-gray-700">User</h4>
            <div class="mt-1 flex items-center gap-3">
              <Avatar
                user={submission.user_details}
                size="xs"
                clickable={true}
              />
              <span class="text-sm text-gray-900">
                {submission.user_details?.name || submission.user_details?.address?.slice(0, 8) + '...'}
              </span>
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
            <p class="mt-1 text-sm text-gray-900">{submission.notes}</p>
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
        
        {#if submission.staff_reply && submission.state !== 'rejected'}
          <div class="bg-gray-50 p-3 rounded">
            <h4 class="text-sm font-medium text-gray-700 mb-1">Staff Response</h4>
            <p class="text-sm text-gray-600">{submission.staff_reply}</p>
          </div>
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
          <div class="border {reviewAction === 'accept' ? 'border-green-200' : reviewAction === 'reject' ? 'border-red-200' : 'border-blue-200'} rounded-lg">
            <!-- Action Toggle Buttons -->
            <div class="flex">
              <button
                type="button"
                onclick={() => reviewAction = 'accept'}
                class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'accept' ? 'bg-green-600 text-white' : 'bg-green-50 text-green-700 hover:bg-green-100'} border-r border-gray-200"
              >
                Accept
              </button>
              <button
                type="button"
                onclick={() => reviewAction = 'reject'}
                class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'reject' ? 'bg-red-600 text-white' : 'bg-red-50 text-red-700 hover:bg-red-100'} border-r border-gray-200"
              >
                Reject
              </button>
              <button
                type="button"
                onclick={() => reviewAction = 'more_info'}
                class="flex-1 px-3 py-2.5 text-sm font-medium transition-colors {reviewAction === 'more_info' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}"
              >
                Request Info
              </button>
            </div>
            
            <!-- Dynamic Form Content -->
            {#if reviewAction === 'accept'}
              <div class="p-4 bg-green-50">
                <div class="space-y-3">
                  {#if users.length > 0}
                    <div>
                      <label class="block text-sm font-medium text-gray-700">
                        Assign Contribution To
                      </label>
                      <div class="mt-1 flex items-center gap-2">
                        <Avatar
                          user={users.find(u => u.id === selectedUser)}
                          size="sm"
                        />
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
                      </div>
                      <p class="text-xs text-gray-500 mt-1">
                        The contribution will be assigned to this user
                      </p>
                    </div>
                  {/if}
                  
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
                        Range: {contributionTypes.find(t => t.id === selectedType)?.min_points || 0}-{contributionTypes.find(t => t.id === selectedType)?.max_points || 100}
                      </p>
                    </div>
                    
                    <div>
                      <label class="block text-sm font-medium text-gray-700 mb-2">
                        Final Points
                      </label>
                      <div class="text-2xl font-bold text-green-700">
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
                          Featured contributions are highlighted on the dashboard and earn special recognition
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
                            placeholder="Describe why this contribution is being featured..."
                            rows="3"
                            class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-yellow-500"
                          ></textarea>
                        </div>
                      </div>
                    {/if}
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      Note (optional)
                    </label>
                    <textarea
                      bind:value={staffReply}
                      placeholder="Add an optional note for this contribution..."
                      rows="3"
                      class="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                    ></textarea>
                  </div>

                  <button
                    onclick={handleReview}
                    disabled={isProcessing}
                    class="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
                  >
                    {isProcessing ? 'Processing...' : 'Accept & Create Contribution'}
                  </button>
                </div>
              </div>
            {:else if reviewAction === 'reject'}
              <div class="p-4 bg-red-50">
                <div class="space-y-3">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      Rejection Reason
                    </label>
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
        {:else if submission.state === 'accepted' && submission.contribution}
          <!-- Show contribution details if accepted -->
          <ContributionCard
            contribution={submission.contribution}
            submission={submission}
            showExpand={true}
          />
        {:else if submission.state === 'rejected' && submission.staff_reply}
          <div class="border border-red-200 rounded-lg p-4 bg-red-50">
            <h4 class="text-sm font-medium text-red-900 mb-2">Rejection Reason</h4>
            <p class="text-sm text-red-700">{submission.staff_reply}</p>
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