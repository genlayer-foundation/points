<script>
  import { push } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { onMount } from 'svelte';
  import api from '../lib/api.js';
  
  let contributionTypes = $state([]);
  let loading = $state(true);
  let submitting = $state(false);
  let error = $state('');
  let success = $state(false);
  
  // Form data
  let formData = $state({
    contribution_type: '',
    contribution_date: new Date().toISOString().split('T')[0],
    notes: ''
  });
  
  // Evidence slots - start with no slots
  let evidenceSlots = $state([]);
  
  onMount(async () => {
    // Check authentication
    if (!$authState.isAuthenticated) {
      push('/');
      return;
    }
    
    // Load contribution types
    try {
      const response = await api.get('/contribution-types/');
      console.log('Contribution types response:', response.data);
      // Handle paginated response
      contributionTypes = response.data.results || response.data;
      console.log('Parsed contribution types:', contributionTypes);
    } catch (err) {
      error = 'Failed to load contribution types';
      console.error('Error loading contribution types:', err);
    } finally {
      loading = false;
    }
  });
  
  function addEvidenceSlot() {
    evidenceSlots = [...evidenceSlots, { id: Date.now(), description: '', url: '', file: null }];
  }
  
  function removeEvidenceSlot(index) {
    if (evidenceSlots.length > 1) {
      evidenceSlots = evidenceSlots.filter((_, i) => i !== index);
    } else {
      // Reset the last slot instead of removing it
      evidenceSlots[0] = { id: Date.now(), description: '', url: '', file: null };
    }
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
        
        
        await api.post(`/submissions/${submissionId}/add-evidence/`, evidenceFormData);
      }
      
      success = true;
      
      // Redirect to my submissions after a moment
      setTimeout(() => {
        push('/my-submissions');
      }, 2000);
      
    } catch (err) {
      error = err.response?.data?.error || err.response?.data?.detail || 'Failed to submit contribution';
      console.error('Submission error:', err);
    } finally {
      submitting = false;
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-3xl font-bold mb-8">Submit Contribution</h1>
  
  {#if loading}
    <div class="flex justify-center py-12">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  {:else if success}
    <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
      <p class="font-bold">Success!</p>
      <p>Your contribution has been submitted successfully. Redirecting to your submissions...</p>
    </div>
  {:else}
    <form onsubmit={handleSubmit} class="max-w-2xl">
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
          <option value="">Select a type...</option>
          {#if contributionTypes && contributionTypes.length > 0}
            {#each contributionTypes as type}
              <option value={type.id}>
                {type.name}
              </option>
            {/each}
          {:else}
            <option value="" disabled>No contribution types available</option>
          {/if}
        </select>
        {#if formData.contribution_type}
          {@const selectedType = contributionTypes.find(t => t.id === parseInt(formData.contribution_type))}
          {#if selectedType?.description}
            <p class="mt-1 text-sm text-gray-600">{selectedType.description}</p>
          {/if}
        {/if}
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
          rows="4"
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Describe your contribution..."
        ></textarea>
      </div>
      
      <div class="mb-6">
        <h3 class="text-lg font-medium mb-4">Evidence (Optional)</h3>
        
        {#if evidenceSlots.length > 0}
          <p class="text-sm text-gray-600 mb-4">You can add multiple pieces of evidence to support your contribution.</p>
          
          <div class="space-y-4">
            {#each evidenceSlots as slot, index}
              <div class="border border-gray-300 rounded-md p-4 {hasEvidenceInSlot(slot) ? 'bg-green-50 border-green-300' : 'bg-white'}">
                <div class="flex justify-between items-start mb-3">
                  <h4 class="font-medium text-sm">Evidence #{index + 1}</h4>
                  {#if evidenceSlots.length > 1 || hasEvidenceInSlot(slot)}
                    <button
                      type="button"
                      onclick={() => removeEvidenceSlot(index)}
                      class="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  {/if}
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label for="evidence_description_{slot.id}" class="block text-sm text-gray-700 mb-1">
                      Description
                    </label>
                    <input
                      type="text"
                      id="evidence_description_{slot.id}"
                      bind:value={slot.description}
                      class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="Brief description"
                    />
                  </div>
                  
                  <div>
                    <label for="evidence_url_{slot.id}" class="block text-sm text-gray-700 mb-1">
                      URL
                    </label>
                    <input
                      type="url"
                      id="evidence_url_{slot.id}"
                      bind:value={slot.url}
                      class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="https://example.com"
                    />
                  </div>
                  
                  <div>
                    <label for="evidence_file_{slot.id}" class="block text-sm text-gray-700 mb-1">
                      File
                    </label>
                    <input
                      type="file"
                      id="evidence_file_{slot.id}"
                      onchange={(e) => handleFileChange(e, index)}
                      class="w-full text-sm"
                    />
                    {#if slot.file}
                      <p class="text-xs text-gray-600 mt-1">{slot.file.name}</p>
                    {/if}
                  </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
        
        <button
          type="button"
          onclick={addEvidenceSlot}
          class="{evidenceSlots.length === 0 ? '' : 'mt-3'} text-primary-600 hover:text-primary-700 text-sm font-medium"
        >
          {evidenceSlots.length === 0 ? '+ Add evidence' : '+ Add another evidence'}
        </button>
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
          onclick={() => push('/my-submissions')}
          class="px-6 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
        >
          Cancel
        </button>
      </div>
    </form>
  {/if}
</div>