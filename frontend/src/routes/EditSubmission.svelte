<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  import ConfirmDialog from '../components/ConfirmDialog.svelte';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';

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
  let defaultContributionTypeId = $state(null);

  // Form data
  let formData = $state({
    contribution_type: '',
    contribution_date: '',
    notes: ''
  });

  // Evidence slots for editing
  let evidenceSlots = $state([]);

  // Flag to track if form has been initialized
  let formInitialized = $state(false);

  // Update form data when submission changes (only on initial load)
  $effect(() => {
    if (submission && !loading && !formInitialized) {
      formData = {
        contribution_type: submission.contribution_type,
        contribution_date: submission.contribution_date ? submission.contribution_date.split('T')[0] : '',
        notes: submission.notes || ''
      };

      formInitialized = true;
      console.log('Form data initialized from submission:', formData);
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

  function handleSelectionChange(category, contributionType) {
    console.log('Selection changed:', { category, contributionType });
  }

  function addEvidenceSlot() {
    // New evidence doesn't have an id - backend will create it
    evidenceSlots = [...evidenceSlots, { description: '', url: '' }];
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

      console.log('Loaded submission:', submission);

      // Check if editing is allowed
      if (!submission.can_edit) {
        error = 'This submission cannot be edited';
        return;
      }

      // Set the default contribution type for the selector
      defaultContributionTypeId = submission.contribution_type;

      // Form data will be populated by the $effect

      // Load existing evidence into editable slots (with id for existing items)
      if (submission.evidence_items && submission.evidence_items.length > 0) {
        evidenceSlots = submission.evidence_items.map(item => ({
          id: item.id,  // Include id for existing evidence
          description: item.description || '',
          url: item.url || ''
        }));
      }

    } catch (err) {
      if (err.response?.status === 404) {
        error = 'Submission not found';
      } else if (err.response?.status === 403) {
        error = 'You do not have permission to view this submission';
      } else {
        error = 'Failed to load submission';
      }
      console.error(err);
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

    // Validate evidence slots - if any field is filled, both must be filled
    for (let i = 0; i < evidenceSlots.length; i++) {
      const slot = evidenceSlots[i];
      const hasDescription = slot.description && slot.description.trim().length > 0;
      const hasUrl = slot.url && slot.url.trim().length > 0;

      if (hasDescription && !hasUrl) {
        error = `Evidence ${i + 1}: Please provide a URL along with the description`;
        return;
      }
      if (hasUrl && !hasDescription) {
        error = `Evidence ${i + 1}: Please provide a description along with the URL`;
        return;
      }
    }

    // Validate that user has provided either notes or evidence
    const filledSlots = evidenceSlots.filter(slot => {
      const hasDescription = slot.description && slot.description.trim().length > 0;
      const hasUrl = slot.url && slot.url.trim().length > 0;
      return hasDescription && hasUrl;
    });
    const hasNotes = formData.notes && formData.notes.trim().length > 0;
    const hasEvidence = filledSlots.length > 0;

    if (!hasNotes && !hasEvidence) {
      error = 'Please provide either a description or evidence to support your contribution';
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
        notes: formData.notes || '',
        evidence_items: evidence_items  // Send all evidence in one request
      };

      console.log('Submitting update:', updateData);

      await api.put(`/submissions/${params.id}/`, updateData);

      // Store success message in sessionStorage to show on My Submissions page
      sessionStorage.setItem('submissionUpdateSuccess', 'Your submission has been saved successfully.');

      // Redirect immediately to my submissions
      push('/my-submissions');

    } catch (err) {
      error = err.response?.data?.error || err.response?.data?.detail || 'Failed to update submission';
      console.error('Update error:', err.response?.data || err);
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
      console.error(err);
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
          <p class="text-blue-800">{submission.staff_reply}</p>
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
          <ContributionSelection
            bind:selectedCategory
            bind:selectedContributionType
            defaultContributionType={defaultContributionTypeId}
            onlySubmittable={true}
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
        </div>
        
        <div class="flex gap-4">
          <button
            type="submit"
            disabled={submitting}
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