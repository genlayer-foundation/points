<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  
  let { params = {} } = $props();
  
  let submission = $state(null);
  let contributionTypes = $state([]);
  let loading = $state(true);
  let submitting = $state(false);
  let error = $state('');
  let success = $state(false);
  
  // Form data
  let formData = $state({
    contribution_type: '',
    contribution_date: '',
    notes: ''
  });
  
  // Evidence slots for editing
  let evidenceSlots = $state([]);
  
  onMount(async () => {
    // Check authentication
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }
    
    await loadData();
  });
  
  function addEvidenceSlot() {
    evidenceSlots = [...evidenceSlots, { id: Date.now(), description: '', url: '', file: null, existing: false }];
  }
  
  function removeEvidenceSlot(index) {
    evidenceSlots = evidenceSlots.filter((_, i) => i !== index);
  }
  
  function handleFileChange(event, index) {
    const file = event.target.files[0];
    if (file) {
      evidenceSlots[index].file = file;
    }
  }
  
  function hasEvidenceInSlot(slot) {
    return slot.description || slot.url || slot.file;
  }
  
  async function loadData() {
    try {
      // Load submission and contribution types in parallel
      const [submissionResponse, typesResponse] = await Promise.all([
        api.get(`/submissions/${params.id}/`),
        api.get('/contribution-types/')
      ]);
      
      submission = submissionResponse.data;
      contributionTypes = typesResponse.data;
      
      // Check if editing is allowed
      if (!submission.can_edit) {
        error = 'This submission cannot be edited';
        return;
      }
      
      // Populate form data
      formData = {
        contribution_type: submission.contribution_type,
        contribution_date: submission.contribution_date.split('T')[0],
        notes: submission.notes || ''
      };
      
      // Note: We don't populate existing evidence as editable slots
      // since the backend doesn't support updating existing evidence
      // Users can only add new evidence items
      
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
    }
  }
  
  async function handleSubmit(event) {
    event.preventDefault();
    
    submitting = true;
    error = '';
    
    try {
      const updateData = {
        contribution_type: formData.contribution_type,
        contribution_date: formData.contribution_date + 'T00:00:00Z',
        notes: formData.notes
      };
      
      await api.put(`/submissions/${params.id}/`, updateData);
      
      // Add new evidence items
      const filledSlots = evidenceSlots.filter(hasEvidenceInSlot);
      for (const slot of filledSlots) {
        const evidenceFormData = new FormData();
        
        if (slot.description) {
          evidenceFormData.append('description', slot.description);
        }
        if (slot.url) {
          evidenceFormData.append('url', slot.url);
        }
        if (slot.file) {
          evidenceFormData.append('file', slot.file, slot.file.name);
        }
        
        await api.post(`/submissions/${params.id}/add-evidence/`, evidenceFormData);
      }
      
      success = true;
      
      // Redirect to my submissions after a moment
      setTimeout(() => {
        push('/my-submissions');
      }, 2000);
      
    } catch (err) {
      error = err.response?.data?.error || 'Failed to update submission';
      console.error(err);
    } finally {
      submitting = false;
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold mb-6">Edit Submission</h1>
  
  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if error && !submission}
    <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if success}
    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
      <p class="font-bold">Success!</p>
      <p>Your submission has been updated and resubmitted for review. Redirecting...</p>
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
          <label for="contribution_type" class="block text-sm font-medium text-gray-700 mb-2">
            Contribution Type <span class="text-red-500">*</span>
          </label>
          <select
            id="contribution_type"
            bind:value={formData.contribution_type}
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            required
          >
            {#each contributionTypes as type}
              <option value={type.id}>
                {type.name} ({type.min_points}-{type.max_points} points)
              </option>
            {/each}
          </select>
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
        
        {#if submission.evidence_items && submission.evidence_items.length > 0}
          <div class="mb-6">
            <h3 class="text-lg font-medium mb-2">Current Evidence</h3>
            <div class="bg-gray-50 p-3 rounded">
              <ul class="space-y-3">
                {#each submission.evidence_items as evidence}
                  <li class="text-sm">
                    {#if evidence.description}
                      • {evidence.description}
                    {/if}
                    {#if evidence.url}
                      - <a href={evidence.url} target="_blank" class="text-primary-600 underline">View URL</a>
                    {/if}
                    {#if evidence.file_url}
                      - <a href={evidence.file_url} target="_blank" class="text-primary-600 underline">View File</a>
                    {/if}
                  </li>
                {/each}
              </ul>
            </div>
          </div>
        {/if}
        
        <div class="mb-6">
          <div class="flex justify-between items-center mb-2">
            <label class="block text-sm font-medium text-gray-700">
              Add New Evidence
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
              Click "Add Evidence" to include additional supporting information.
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
                        placeholder="https://example.com"
                        class="w-full px-2 py-1 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    </div>
                  </div>
                  
                  <div class="mt-3">
                    <label class="block text-xs font-medium text-gray-700 mb-1">
                      File Upload
                    </label>
                    <input
                      type="file"
                      onchange={(e) => handleFileChange(e, index)}
                      class="w-full text-sm text-gray-500 file:mr-4 file:py-1 file:px-2 file:rounded file:border-0 file:text-sm file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
                    />
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
            Add additional URLs, descriptions, and files to support your contribution claim.
          </p>
        </div>
        
        <div class="flex gap-4">
          <button
            type="submit"
            disabled={submitting}
            class="px-6 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Updating...' : 'Update & Resubmit'}
          </button>
          
          <button
            type="button"
            onclick={() => push('/my-submissions')}
            class="px-6 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  {/if}
</div>