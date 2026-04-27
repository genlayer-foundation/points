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

  // Required evidence types: at least one filled evidence slot must have a
  // detected URL type in this list when the contribution type declares it.
  let requiredEvidenceTypes = $derived(
    selectedContributionType?.required_evidence_url_types?.length
      ? selectedContributionType.required_evidence_url_types
      : []
  );

  let requiredEvidenceLabel = $derived.by(() => {
    if (!requiredEvidenceTypes.length) return '';
    const names = requiredEvidenceTypes.map((t) => t.name);
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]} or ${names[1]}`;
    return `${names.slice(0, -1).join(', ')}, or ${names[names.length - 1]}`;
  });

  let requiredEvidenceSatisfied = $derived.by(() => {
    if (!requiredEvidenceTypes.length) return true;
    return evidenceSlots.some((slot) => {
      if (!slot.url?.trim()) return false;
      const t = slot.selectedType;
      if (!t) return false;
      return requiredEvidenceTypes.some((rt) => rt.id === t.id);
    });
  });

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

  // Check if selected type requires social accounts the user hasn't linked
  const socialAccountLabels = {
    twitter: "X (Twitter)",
    discord: "Discord",
    github: "GitHub",
  };
  const socialConnectionFields = {
    twitter: "twitter_connection",
    discord: "discord_connection",
    github: "github_connection",
  };
  let missingSocialAccounts = $derived.by(() => {
    if (!selectedContributionType?.required_social_accounts?.length) return [];
    const user = $userStore.user;
    if (!user) return selectedContributionType.required_social_accounts.map((a) => socialAccountLabels[a] || a);
    return selectedContributionType.required_social_accounts
      .filter((account) => {
        const field = socialConnectionFields[account];
        return field && !user[field];
      })
      .map((a) => socialAccountLabels[a] || a);
  });

  // True when ALL non-generic accepted evidence types require an unlinked social account
  let allEvidenceTypesBlocked = $derived.by(() => {
    if (!selectedContributionType || acceptedEvidenceTypes.length === 0) return false;
    const user = $userStore.user;
    if (!user) return false;
    const slugToAccount = {
      'x-post': 'twitter',
      'github-repo': 'github',
      'github-file': 'github',
    };
    const nonGenericTypes = acceptedEvidenceTypes.filter(t => !t.is_generic);
    if (nonGenericTypes.length === 0) return false;
    return nonGenericTypes.every(t => {
      const account = slugToAccount[t.slug];
      if (!account) return false;
      const info = ownershipPlatformMap[account];
      return info && !user[info.field];
    });
  });

  // Collect the raw account keys that are blocking
  let blockingSocialAccounts = $derived.by(() => {
    const accounts = new Set();
    if (selectedContributionType?.required_social_accounts?.length) {
      const user = $userStore.user;
      for (const account of selectedContributionType.required_social_accounts) {
        const field = socialConnectionFields[account];
        if (field && (!user || !user[field])) {
          accounts.add(account);
        }
      }
    }
    if (allEvidenceTypesBlocked) {
      const slugToAccount = {
        'x-post': 'twitter',
        'github-repo': 'github',
        'github-file': 'github',
      };
      const nonGenericTypes = acceptedEvidenceTypes.filter(t => !t.is_generic);
      const user = $userStore.user;
      for (const t of nonGenericTypes) {
        const account = slugToAccount[t.slug];
        if (account) {
          const info = ownershipPlatformMap[account];
          if (info && user && !user[info.field]) {
            accounts.add(account);
          }
        }
      }
    }
    return Array.from(accounts);
  });

  // Master gate: should the form details be shown?
  let canShowFormDetails = $derived(
    selectedContributionType &&
    missingSocialAccounts.length === 0 &&
    !allEvidenceTypesBlocked
  );

  // True if any evidence slot has a URL that doesn't match its selected type
  let hasEvidencePatternMismatch = $derived.by(() => {
    return evidenceSlots.some(slot =>
      slot.url && slot.selectedType && !slot.selectedType.is_generic && !urlMatchesType(slot.url, slot.selectedType)
    );
  });

  // URL placeholder hints per evidence type slug
  const urlPlaceholders = {
    'x-post': 'https://x.com/username/status/123...',
    'github-repo': 'https://github.com/username/repository',
    'github-file': 'https://github.com/username/repo/blob/main/file.py',
    'github-pr': 'https://github.com/org/repo/pull/123',
    'github-issue': 'https://github.com/org/repo/issues/123',
    'studio-contract': 'https://studio.genlayer.com/...',
  };

  function getUrlPlaceholder(slot) {
    return urlPlaceholders[slot.selectedType?.slug] || 'https://...';
  }

  function handleEvidenceTypeChange(index, slug) {
    const urlType = acceptedEvidenceTypes.find(t => t.slug === slug) || null;
    evidenceSlots[index].selectedType = urlType;
    if (urlType) {
      evidenceSlots[index].description = urlType.is_generic ? 'Other' : urlType.name;
    }
  }

  // Check if a URL matches a specific evidence type's patterns
  function urlMatchesType(url, urlType) {
    if (!url || !urlType || urlType.is_generic) return true;
    for (const pattern of urlType.url_patterns || []) {
      try {
        if (new RegExp(pattern, 'i').test(url)) return true;
      } catch (e) { continue; }
    }
    return false;
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
      // Auto-correct: if URL matches a specific type, always upgrade to it
      // But if detected is generic, don't override a specific manual selection
      if (detected && !detected.is_generic) {
        evidenceSlots[index].selectedType = detected;
        evidenceSlots[index].description = detected.name;
      } else if (!evidenceSlots[index].selectedType) {
        evidenceSlots[index].selectedType = detected;
        evidenceSlots[index].description = detected?.is_generic ? 'Other' : (detected?.name || '');
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

    // Client-side: validate that URL matches the selected evidence type's patterns
    for (let i = 0; i < filledSlots.length; i++) {
      const slot = filledSlots[i];
      if (slot.selectedType && !slot.selectedType.is_generic) {
        if (!urlMatchesType(slot.url, slot.selectedType)) {
          error = `Evidence ${i + 1}: The URL provided doesn't match the expected format for ${slot.selectedType.name}.`;
          return;
        }
      }
    }

    // Enforce the required-URL-type rule before hitting the server
    if (requiredEvidenceTypes.length > 0 && !requiredEvidenceSatisfied) {
      error = `At least one evidence URL must be one of: ${requiredEvidenceLabel}.`;
      return;
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

        <!-- Social account linking gate -->
        {#if selectedContributionType && !canShowFormDetails}
          <div class="mb-6 bg-white border border-gray-200 rounded-lg p-6 flex flex-col gap-4 items-center text-center">
            <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
              <svg class="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
              </svg>
            </div>
            <div>
              <h3 class="font-semibold text-gray-900 mb-1">Connect Your Account</h3>
              <p class="text-sm text-gray-500">
                This contribution type requires account verification. Please connect your account to continue.
              </p>
            </div>
            <div class="flex flex-col gap-3 w-full max-w-[280px]">
              {#each blockingSocialAccounts as account}
                {@const info = ownershipPlatformMap[account]}
                {#if info}
                  <SocialLink
                    platform={info.platform}
                    platformLabel={info.label}
                    connection={$userStore.user?.[info.field]}
                    initiateUrl={info.initiateUrl}
                    onLinked={handleEvidenceSocialLinked}
                    compact={false}
                  />
                {/if}
              {/each}
            </div>
          </div>
        {/if}

        {#if canShowFormDetails}
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

          {#if requiredEvidenceTypes.length > 0}
            <div
              class="mb-3 p-3 rounded-md border {requiredEvidenceSatisfied
                ? 'border-green-300 bg-green-50'
                : 'border-amber-300 bg-amber-50'} flex items-start gap-2"
            >
              {#if requiredEvidenceSatisfied}
                <svg class="w-4 h-4 mt-0.5 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
              {:else}
                <svg class="w-4 h-4 mt-0.5 text-amber-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l6.516 11.59c.75 1.336-.213 2.98-1.742 2.98H3.48c-1.53 0-2.493-1.644-1.743-2.98L8.257 3.1zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              {/if}
              <div class="text-sm">
                <span class="font-semibold">Required evidence:</span>
                at least one URL must be one of
                <span class="font-medium">{requiredEvidenceLabel}</span>.
                {#if requiredEvidenceSatisfied}
                  <span class="text-green-700">Requirement satisfied.</span>
                {:else}
                  <span class="text-amber-700">Not yet satisfied.</span>
                {/if}
              </div>
            </div>
          {/if}

          {#if evidenceSlots.length === 0}
            <div class="bg-gray-50 p-4 rounded text-center text-gray-500">
              No evidence added yet. Click "Add Evidence" to include supporting information.
            </div>
          {:else}
            <div class="space-y-4">
              {#each evidenceSlots as slot, index}
                <div class="border border-gray-200 rounded-lg p-4 bg-white relative">
                  <!-- URL field (primary input) -->
                  <div class="pr-[60px] mb-3">
                    <label class="block text-xs font-medium text-gray-700 mb-1">
                      URL
                    </label>
                    <input
                      type="url"
                      bind:value={slot.url}
                      onblur={() => handleUrlBlur(index)}
                      placeholder={getUrlPlaceholder(slot)}
                      class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                    />
                  </div>

                  <!-- Detected type indicator + override -->
                  {#if acceptedEvidenceTypes.length > 0}
                    <div class="flex items-center gap-2 pr-[60px]">
                      {#if slot.selectedType}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          <svg class="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                          </svg>
                          {slot.selectedType.is_generic ? 'Other' : slot.selectedType.name}
                        </span>
                      {:else}
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-50 text-gray-400">
                          Paste a URL to auto-detect type
                        </span>
                      {/if}
                      {#if acceptedEvidenceTypes.length > 1}
                        <select
                          value={slot.selectedType?.slug || ''}
                          onchange={(e) => handleEvidenceTypeChange(index, e.target.value)}
                          class="text-xs text-gray-500 bg-transparent border-none underline decoration-dotted underline-offset-2 cursor-pointer focus:outline-none appearance-none"
                        >
                          <option value="" disabled>Change type</option>
                          {#each acceptedEvidenceTypes as urlType}
                            {#if urlType.is_generic}
                              <option value={urlType.slug}>Other</option>
                            {:else}
                              <option value={urlType.slug}>{urlType.name}</option>
                            {/if}
                          {/each}
                        </select>
                      {/if}
                    </div>
                    {#if slot.url && slot.selectedType && !slot.selectedType.is_generic && !urlMatchesType(slot.url, slot.selectedType)}
                      <p class="text-xs text-red-500 mt-1 pl-0.5">
                        This URL doesn't match the expected format for {slot.selectedType.name}.
                      </p>
                    {/if}
                  {/if}

                  <div class="absolute top-4 right-4">
                    <button
                      type="button"
                      onclick={() => removeEvidenceSlot(index)}
                      class="text-red-500 hover:text-red-700 text-sm"
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
            <div class="mt-3 bg-gray-50 border border-gray-200 rounded-lg p-4 flex flex-col gap-3">
              <p class="text-sm text-gray-500">
                Your selected evidence type requires account verification to confirm ownership.
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
                      compact={false}
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
            disabled={submitting || evidenceRequiredAccounts.length > 0 || hasEvidencePatternMismatch}
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
        {/if}
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