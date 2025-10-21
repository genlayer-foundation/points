<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';
  
  let loading = $state(false);
  let submitting = $state(false);
  let error = $state('');
  let authChecked = $state(false);
  
  // Selection state
  let selectedCategory = $state('validator');
  let selectedContributionType = $state(null);
  
  // Form data
  let formData = $state({
    contribution_type: '',
    contribution_date: new Date().toISOString().split('T')[0],
    notes: ''
  });
  
  // Evidence slots - start with no slots
  let evidenceSlots = $state([]);
  
  // React to auth state changes
  $effect(() => {
    if ($authState.isAuthenticated) {
      authChecked = true;
    } else {
      authChecked = true;
    }
  });
  
  // Update form data when contribution type is selected
  $effect(() => {
    if (selectedContributionType) {
      formData.contribution_type = selectedContributionType.id;
      // Clear error when a contribution type is selected
      if (error === 'Please select a contribution type') {
        error = '';
      }
    } else {
      formData.contribution_type = '';
    }
  });
  
  onMount(async () => {
    // Wait a moment for auth state to be verified
    await new Promise(resolve => setTimeout(resolve, 100));
    authChecked = true;
  });
  
  function handleSelectionChange(category, contributionType) {
    console.log('Selection changed:', { category, contributionType });
  }
  
  function addEvidenceSlot() {
    evidenceSlots = [...evidenceSlots, { id: Date.now(), description: '', url: '' }];
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
  
  function hasEvidenceInSlot(slot) {
    return slot.description || slot.url;
  }
  
  async function handleSubmit(event) {
    event.preventDefault();
    
    if (!formData.contribution_type) {
      error = 'Please select a contribution type';
      return;
    }
    
    submitting = true;
    error = '';
    
    try {
      // Create the submission
      const submissionData = {
        contribution_type: formData.contribution_type,
        contribution_date: formData.contribution_date + 'T00:00:00Z',
        notes: formData.notes
      };
      
      const response = await api.post('/submissions/', submissionData);
      const submissionId = response.data.id;
      
      // Add evidence from slots that have content
      const filledSlots = evidenceSlots.filter(hasEvidenceInSlot);
      
      for (const slot of filledSlots) {
        const evidenceData = {};

        if (slot.description) {
          evidenceData.description = slot.description;
        }
        if (slot.url) {
          // Normalize URL before sending to backend
          evidenceData.url = normalizeUrl(slot.url);
        }


        await api.post(`/submissions/${submissionId}/add-evidence/`, evidenceData);
      }
      
      // Store success message in sessionStorage to show on My Submissions page
      sessionStorage.setItem('submissionUpdateSuccess', 'Your contribution has been submitted successfully and is pending review.');
      
      // Redirect immediately to my submissions
      push('/my-submissions');
      
    } catch (err) {
      error = err.response?.data?.error || err.response?.data?.detail || 'Failed to submit contribution';
      console.error('Submission error:', err);
    } finally {
      submitting = false;
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold mb-6">Submit Contribution</h1>
  
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
        <p class="text-gray-500 mb-4">Please connect your wallet to submit contributions.</p>
        <button
          onclick={() => document.querySelector('.auth-button')?.click()}
          class="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700"
        >
          Connect Wallet
        </button>
      </div>
    </div>
  {:else}
    <form onsubmit={handleSubmit} class="max-w-2xl">
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
          placeholder="Describe your contribution..."
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
          Add URLs and descriptions to support your contribution claim. Provide links to GitHub, Twitter, blog posts, or other evidence.
        </p>
      </div>
      
      <div class="flex gap-4">
        <button
          type="submit"
          disabled={submitting}
          class="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? 'Submitting...' : 'Submit Contribution'}
        </button>
        
        <button
          type="button"
          onclick={() => push('/')}
          class="px-6 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
        >
          Cancel
        </button>
      </div>
    </form>
  {/if}
</div>