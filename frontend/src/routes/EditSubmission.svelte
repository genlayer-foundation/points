<script>
  import { push, querystring } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  import ConfirmDialog from '../components/ConfirmDialog.svelte';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';
  import SocialLink from '../components/SocialLink.svelte';
  import { userStore } from '../lib/userStore';
  import { getContributionTypes } from '../lib/api/contributions.js';
  import { parseMarkdown } from '../lib/markdownLoader.js';

  let { params = {} } = $props();

  let submission = $state(null);
  let loading = $state(true);
  let submitting = $state(false);
  let error = $state('');
  let authChecked = $state(false);
  let showDeleteDialog = $state(false);

  // Contribution type selection state
  let selectedCategory = $state('validator');
  let selectedContributionType = $state(null);
  let selectedMission = $state(null);
  let defaultContributionTypeId = $state(null);
  let missionIdFromUrl = $state(null);  // Mission ID from URL parameter

  // Form data
  let formData = $state({
    contribution_type: '',
    contribution_date: '',
    title: '',
    notes: '',
    mission: null
  });

  // Evidence slots for editing
  let evidenceSlots = $state([]);

  // Flag to track if form has been initialized
  let formInitialized = $state(false);

  // All evidence URL types collected from contribution types
  let allEvidenceUrlTypes = $state([]);

  // Update form data when submission changes (only on initial load)
  $effect(() => {
    if (submission && !loading && !formInitialized) {
      formData = {
        contribution_type: submission.contribution_type,
        contribution_date: submission.contribution_date ? submission.contribution_date.split('T')[0] : '',
        title: submission.title || '',
        notes: submission.notes || '',
        mission: submission.mission || null
      };

      formInitialized = true;
    }
  });

  // Sync selectedContributionType with formData.contribution_type
  $effect(() => {
    if (selectedContributionType) {
      formData.contribution_type = selectedContributionType.id;
      // Clear error when a contribution type is selected
      if (error === 'Please select a contribution type') {
        error = '';
      }
    }
  });

  // Sync selectedMission with formData.mission
  $effect(() => {
    formData.mission = selectedMission || null;
  });

  function handleSelectionChange(category, contributionType) {
    // Selection changed
  }

  // --- Evidence URL type detection & validation ---

  function detectUrlType(url) {
    if (!url || !allEvidenceUrlTypes.length) return null;
    for (const urlType of allEvidenceUrlTypes) {
      if (urlType.is_generic) continue;
      for (const pattern of urlType.url_patterns || []) {
        try {
          if (new RegExp(pattern, 'i').test(url)) return urlType;
        } catch (e) { continue; }
      }
    }
    return allEvidenceUrlTypes.find(t => t.is_generic) || null;
  }

  let acceptedEvidenceTypes = $derived(
    selectedContributionType?.accepted_evidence_url_types?.length
      ? selectedContributionType.accepted_evidence_url_types
      : []
  );

  // Social account linking for evidence ownership
  const ownershipPlatformMap = {
    twitter: { platform: 'twitter', label: 'X', field: 'twitter_connection', initiateUrl: '/api/auth/twitter/' },
    github: { platform: 'github', label: 'GitHub', field: 'github_connection', initiateUrl: '/api/auth/github/' },
  };

  let evidenceRequiredAccounts = $derived.by(() => {
    const user = $userStore.user;
    if (!user) return [];
    const needed = new Set();
    for (const slot of evidenceSlots) {
      const type = slot.selectedType;
      if (!type || type.is_generic) continue;
      const slugToAccount = {
        'x-post': 'twitter',
        'github-repo': 'github',
        'github-file': 'github',
      };
      const account = slugToAccount[type.slug];
      if (account) {
        const info = ownershipPlatformMap[account];
        if (info && !user[info.field]) needed.add(account);
      }
    }
    return Array.from(needed);
  });

  function handleEvidenceSocialLinked(updatedUser) {
    userStore.setUser(updatedUser);
  }

  function handleEvidenceTypeChange(index, slug) {
    const urlType = acceptedEvidenceTypes.find(t => t.slug === slug) || null;
    evidenceSlots[index].selectedType = urlType;
  }

  function addEvidenceSlot() {
    // New evidence doesn't have an id - backend will create it
    evidenceSlots = [...evidenceSlots, { description: '', url: '', selectedType: null }];
  }

  function removeEvidenceSlot(index) {
    evidenceSlots = evidenceSlots.filter((_, i) => i !== index);
  }
  
  function normalizeUrl(url) {
    if (!url || url.trim() === '') return url;
    
    // Check if URL already has a protocol
    const hasProtocol = /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(url);
    
    if (!hasProtocol) {
      // Add https:// if no protocol is present
      return 'https://' + url;
    }
    
    return url;
  }
  
  function handleUrlBlur(index) {
    if (evidenceSlots[index]) {
      evidenceSlots[index].url = normalizeUrl(evidenceSlots[index].url);
      const detected = detectUrlType(evidenceSlots[index].url);
      evidenceSlots[index].detectedType = detected;
      if (detected && !evidenceSlots[index].selectedType) {
        evidenceSlots[index].selectedType = detected;
      }
    }
  }

  async function loadData() {
    if (!$authState.isAuthenticated) {
      loading = false;
      authChecked = true;
      return;
    }

    loading = true;
    try {
      // Load submission
      const submissionResponse = await api.get(`/submissions/${params.id}/`);
      submission = submissionResponse.data;

      // Check if editing is allowed
      if (!submission.can_edit) {
        error = 'This submission cannot be edited';
        return;
      }

      // Set the default contribution type and mission for the selector
      defaultContributionTypeId = submission.contribution_type;

      // Load contribution types to collect evidence URL types
      try {
        const allTypes = await getContributionTypes();
        const urlTypeMap = new Map();
        for (const ct of allTypes) {
          for (const ut of ct.accepted_evidence_url_types || []) {
            if (!urlTypeMap.has(ut.slug)) urlTypeMap.set(ut.slug, ut);
          }
        }
        allEvidenceUrlTypes = Array.from(urlTypeMap.values()).sort(
          (a, b) => (a.order || 0) - (b.order || 0)
        );
      } catch (e) {
        allEvidenceUrlTypes = [];
      }

      // Form data will be populated by the $effect

      // Load existing evidence into editable slots (with id for existing items)
      if (submission.evidence_items && submission.evidence_items.length > 0) {
        evidenceSlots = submission.evidence_items.map(item => {
          const detected = item.url ? detectUrlType(item.url) : null;
          return {
            id: item.id,
            description: item.description || '',
            url: item.url || '',
            detectedType: detected,
            selectedType: detected,
          };
        });
      }

    } catch (err) {
      if (err.response?.status === 404) {
        error = 'Submission not found';
      } else if (err.response?.status === 403) {
        error = 'You do not have permission to view this submission';
      } else {
        error = 'Failed to load submission';
      }
    } finally {
      loading = false;
      authChecked = true;
    }
  }
  
  // React to auth state changes
  $effect(() => {
    if (params.id) {
      loadData();
    }
  });
  
  onMount(async () => {
    // Parse query parameters for mission ID (similar to SubmitContribution.svelte)
    const urlParams = new URLSearchParams($querystring);
    const missionParam = urlParams.get('mission');
    if (missionParam) {
      missionIdFromUrl = parseInt(missionParam);
    }

    // Wait a moment for auth state to be verified
    await new Promise(resolve => setTimeout(resolve, 100));
    if (params.id) {
      loadData();
    }
  });
  
  async function handleSubmit(event) {
    event.preventDefault();

    // Validate required fields
    if (!formData.contribution_type) {
      error = 'Please select a contribution type';
      return;
    }

    if (!formData.contribution_date) {
      error = 'Please select a contribution date';
      return;
    }

    // Validate evidence slots - URL is required for each evidence item
    for (let i = 0; i < evidenceSlots.length; i++) {
      const slot = evidenceSlots[i];
      const hasDescription = slot.description && slot.description.trim().length > 0;
      const hasUrl = slot.url && slot.url.trim().length > 0;

      if (hasDescription && !hasUrl) {
        error = `Evidence ${i + 1}: A URL is required for each evidence item`;
        return;
      }
      if (hasUrl && !hasDescription) {
        error = `Evidence ${i + 1}: Please provide a description along with the URL`;
        return;
      }
    }

    // Validate that user has provided at least one evidence item with a URL
    const filledSlots = evidenceSlots.filter(slot => {
      const hasDescription = slot.description && slot.description.trim().length > 0;
      const hasUrl = slot.url && slot.url.trim().length > 0;
      return hasDescription && hasUrl;
    });

    if (filledSlots.length === 0) {
      error = 'Please add at least one evidence item with a URL to support your contribution';
      return;
    }

    // Client-side: validate that selected evidence type matches the URL
    for (let i = 0; i < filledSlots.length; i++) {
      const slot = filledSlots[i];
      if (slot.selectedType && !slot.selectedType.is_generic) {
        const detected = detectUrlType(slot.url);
        if (detected && !detected.is_generic && detected.slug !== slot.selectedType.slug) {
          error = `Evidence ${i + 1}: The URL doesn't look like a ${slot.selectedType.name}. It was detected as ${detected.name}.`;
          return;
        }
      }
    }

    submitting = true;
    error = '';

    try {
      // Prepare evidence items (formset pattern)
      // Include all slots that have content
      const evidence_items = filledSlots.map(slot => {
        const item = {
          description: slot.description || '',
          url: slot.url ? normalizeUrl(slot.url) : ''
        };
        // Include id for existing evidence (items with id will be updated)
        if (slot.id) {
          item.id = slot.id;
        }
        return item;
      });

      const updateData = {
        contribution_type: parseInt(formData.contribution_type),
        contribution_date: formData.contribution_date + 'T00:00:00Z',
        title: formData.title || '',
        notes: formData.notes || '',
        mission: formData.mission || null,
        evidence_items: evidence_items  // Send all evidence in one request
      };

      await api.put(`/submissions/${params.id}/`, updateData);

      // Store success message in sessionStorage to show on My Submissions page
      sessionStorage.setItem('submissionUpdateSuccess', 'Your submission has been saved successfully.');

      // Redirect immediately to my submissions
      push('/my-submissions');

    } catch (err) {
      if (err.response?.data?.evidence_items) {
        const evidenceErrors = err.response.data.evidence_items;
        if (Array.isArray(evidenceErrors) && evidenceErrors.length > 0) {
          const first = evidenceErrors[0];
          error = first.message || JSON.stringify(first);
        } else {
          error = typeof evidenceErrors === 'string'
            ? evidenceErrors
            : JSON.stringify(evidenceErrors);
        }
      } else {
        error = err.response?.data?.error || err.response?.data?.detail || 'Failed to update submission';
      }
    } finally {
      submitting = false;
    }
  }

  function handleDeleteSubmission() {
    showDeleteDialog = true;
  }

  async function confirmDelete() {
    showDeleteDialog = false;
    submitting = true;
    error = '';

    try {
      await api.delete(`/submissions/${params.id}/`);

      // Store success message in sessionStorage to show on My Submissions page
      sessionStorage.setItem('submissionUpdateSuccess', 'Your submission has been removed.');

      // Redirect to my submissions
      push('/my-submissions');

    } catch (err) {
      error = err.response?.data?.error || 'Failed to delete submission';
    } finally {
      submitting = false;
    }
  }

  function cancelDelete() {
    showDeleteDialog = false;
  }
</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold mb-6">Edit Submission</h1>
  
  {#if !authChecked || loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if !$authState.isAuthenticated}
    <div class="bg-white shadow rounded-lg p-8">
      <div class="text-center">
        <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <h3 class="text-lg font-medium text-gray-900 mb-2">Authentication Required</h3>
        <p class="text-gray-500 mb-4">Please connect your wallet to edit submissions.</p>
        <button
          onclick={() => push('/')}
          class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  {:else if error && !submission}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if submission}
    <div class="max-w-2xl">
      {#if submission.staff_reply}
        <div class="mb-6 bg-blue-50 border border-blue-200 p-4 rounded">
          <h3 class="font-semibold text-blue-900 mb-2">Staff Feedback:</h3>
          <div class="markdown-content text-blue-800">{@html parseMarkdown(submission.staff_reply)}</div>
        </div>
      {/if}
      
      <form onsubmit={handleSubmit}>
        {#if error}
          <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        {/if}
        
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            Contribution Type <span class="text-red-500">*</span>
          </label>
          <!-- Show all types (including non-submittable) so user can see their current
               submission's type, even if it was changed to non-submittable after submission -->
          <ContributionSelection
            bind:selectedCategory
            bind:selectedContributionType
            bind:selectedMission
            defaultContributionType={defaultContributionTypeId}
            defaultMission={missionIdFromUrl || submission?.mission}
            onlySubmittable={false}
            stewardMode={false}
            onSelectionChange={handleSelectionChange}
          />
        </div>
        
        <div class="mb-6">
          <label for="contribution_date" class="block text-sm font-medium text-gray-700 mb-2">
            Contribution Date <span class="text-red-500">*</span>
          </label>
          <input
            type="date"
            id="contribution_date"
            bind:value={formData.contribution_date}
            max={new Date().toISOString().split('T')[0]}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            required
          />
        </div>
        
        <div class="mb-6">
          <label for="title" class="block text-sm font-medium text-gray-700 mb-2">
            Title <span class="text-gray-400 font-normal">(optional)</span>
          </label>
          <input
            type="text"
            id="title"
            bind:value={formData.title}
            maxlength="200"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Give your contribution a title..."
          />
        </div>

        <div class="mb-6">
          <label for="notes" class="block text-sm font-medium text-gray-700 mb-2">
            Notes / Description
          </label>
          <textarea
            id="notes"
            bind:value={formData.notes}
            rows="6"
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Update your contribution description based on the staff feedback..."
          ></textarea>
        </div>

        <div class="mb-6">
          <div class="flex justify-between items-center mb-2">
            <label class="block text-sm font-medium text-gray-700">
              Evidence & Supporting Information
            </label>
            <button
              type="button"
              onclick={addEvidenceSlot}
              class="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
            >
              + Add Evidence
            </button>
          </div>

          {#if evidenceSlots.length === 0}
            <div class="bg-gray-50 p-4 rounded text-center text-gray-500">
              No evidence added yet. Click "Add Evidence" to include supporting information.
            </div>
          {:else}
            <div class="space-y-4">
              {#each evidenceSlots as slot, index}
                <div class="border border-gray-200 rounded-lg p-4 bg-white">
                  <!-- Evidence Type Selector -->
                  {#if acceptedEvidenceTypes.length > 0}
                    <div class="mb-3">
                      <label class="block text-xs font-medium text-gray-700 mb-1">
                        Evidence Type
                      </label>
                      <select
                        value={slot.selectedType?.slug || ''}
                        onchange={(e) => handleEvidenceTypeChange(index, e.target.value)}
                        class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                      >
                        <option value="">Select type...</option>
                        {#each acceptedEvidenceTypes.filter(t => !t.is_generic) as urlType}
                          <option value={urlType.slug}>{urlType.name}</option>
                        {/each}
                        {@const genericType = acceptedEvidenceTypes.find(t => t.is_generic)}
                        {#if genericType}
                          <option value={genericType.slug}>Other</option>
                        {/if}
                      </select>
                    </div>
                  {/if}

                  <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label class="block text-xs font-medium text-gray-700 mb-1">
                        Description
                      </label>
                      <input
                        type="text"
                        bind:value={slot.description}
                        placeholder="Brief description"
                        class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </div>

                    <div>
                      <label class="block text-xs font-medium text-gray-700 mb-1">
                        URL
                      </label>
                      <input
                        type="url"
                        bind:value={slot.url}
                        onblur={() => handleUrlBlur(index)}
                        placeholder="https://example.com"
                        class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                      {#if slot.detectedType && slot.selectedType && !slot.selectedType.is_generic && slot.detectedType.slug !== slot.selectedType.slug && !slot.detectedType.is_generic}
                        <p class="text-[11px] text-amber-600 mt-1">
                          This URL looks like a {slot.detectedType.name}, not a {slot.selectedType.name}
                        </p>
                      {/if}
                    </div>
                  </div>

                  <div class="mt-2 flex justify-end">
                    <button
                      type="button"
                      onclick={() => removeEvidenceSlot(index)}
                      class="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
          
          <p class="text-xs text-gray-500 mt-2">
            Add additional URLs and descriptions to support your contribution claim. Provide links to GitHub, Twitter, blog posts, or other evidence.
          </p>

          {#if evidenceRequiredAccounts.length > 0}
            <div class="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-4 flex flex-col gap-3">
              <p class="text-sm text-amber-800">
                Your evidence requires a linked account to verify ownership. Please link below to continue.
              </p>
              <div class="flex flex-wrap gap-3">
                {#each evidenceRequiredAccounts as account}
                  {@const info = ownershipPlatformMap[account]}
                  {#if info}
                    <SocialLink
                      platform={info.platform}
                      platformLabel={info.label}
                      connection={$userStore.user?.[info.field]}
                      initiateUrl={info.initiateUrl}
                      onLinked={handleEvidenceSocialLinked}
                      compact={true}
                    />
                  {/if}
                {/each}
              </div>
            </div>
          {/if}
        </div>
        
        <div class="flex gap-4">
          <button
            type="submit"
            disabled={submitting || evidenceRequiredAccounts.length > 0}
            class="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Saving...' : 'Save'}
          </button>

          <button
            type="button"
            onclick={() => push('/my-submissions')}
            disabled={submitting}
            class="px-6 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 disabled:opacity-50"
          >
            Cancel
          </button>

          <button
            type="button"
            onclick={handleDeleteSubmission}
            disabled={submitting}
            class="px-6 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Remove Submission
          </button>
        </div>
      </form>
    </div>
  {/if}
</div>

<ConfirmDialog
  isOpen={showDeleteDialog}
  title="Remove Submission"
  message="Are you sure you want to remove this submission? It will be marked as rejected."
  confirmText="Remove"
  cancelText="Cancel"
  onConfirm={confirmDelete}
  onCancel={cancelDelete}
/>

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