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
  let authChecked = $state(false);
  
  // Form data
  let formData = $state({
    contribution_type: '',
    contribution_date: '',
    notes: ''
  });
  
  async function loadData() {
    if (!$authState.isAuthenticated) {
      loading = false;
      authChecked = true;
      return;
    }
    
    loading = true;
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
    
    submitting = true;
    error = '';
    
    try {
      const updateData = {
        contribution_type: formData.contribution_type,
        contribution_date: formData.contribution_date + 'T00:00:00Z',
        notes: formData.notes
      };
      
      await api.put(`/submissions/${params.id}/`, updateData);
      
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
            <p class="text-sm text-gray-600 mt-2">
              Note: You cannot modify evidence in this form. Please include any additional information in the notes field.
            </p>
          </div>
        {/if}
        
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