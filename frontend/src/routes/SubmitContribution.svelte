<script>
  import { push, querystring } from 'svelte-spa-router';
  import { authState } from '../lib/auth.js';
  import { userStore } from '../lib/userStore';
  import { onMount } from 'svelte';
  import api, { contributionsAPI } from '../lib/api.js';
  import ContributionSelection from '../lib/components/ContributionSelection.svelte';

  let loading = $state(false);
  let submitting = $state(false);
  let error = $state('');
  let authChecked = $state(false);
  let recaptchaToken = $state('');
  let recaptchaWidgetId = $state(null);

  // Get reCAPTCHA site key from environment
  const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY;

  // Mission-related state
  let missionId = $state(null);
  let mission = $state(null);
  let loadingMission = $state(false);
  let selectedMission = $state(null);

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

  async function fetchMission() {
    if (!missionId) return;

    loadingMission = true;
    try {
      const response = await contributionsAPI.getMission(missionId);
      mission = response.data;

      // Pre-select contribution type from mission
      // Note: ContributionSelection component will handle matching mission.contribution_type
      // to the loaded contribution types and set the proper selection
      selectedMission = mission.id;
    } catch (err) {
      error = 'Failed to load mission details';
    } finally {
      loadingMission = false;
    }
  }

  async function fetchContributionType(typeId) {
    if (!typeId) return;

    loading = true;
    try {
      const response = await contributionsAPI.getContributionType(typeId);
      const type = response.data;

      // Pre-select contribution type from URL
      selectedCategory = type.category || 'validator';
      selectedContributionType = type;
      formData.contribution_type = type.id;
    } catch (err) {
      error = 'Failed to load contribution type details';
    } finally {
      loading = false;
    }
  }

  onMount(async () => {
    // Parse query parameters
    const params = new URLSearchParams($querystring);
    const missionParam = params.get('mission');
    const typeParam = params.get('type');

    if (missionParam) {
      missionId = parseInt(missionParam);
      // ContributionSelection will handle mission preselection via defaultMission prop
    } else if (typeParam) {
      // Pre-select contribution type from URL parameter
      await fetchContributionType(parseInt(typeParam));
    }

    // Wait a moment for auth state to be verified
    await new Promise(resolve => setTimeout(resolve, 100));
    authChecked = true;

    // Poll for grecaptcha API and render widget when available
    const checkRecaptcha = () => {
      if (renderRecaptcha()) {
        return; // Success - widget rendered
      }
      // Retry after 100ms if grecaptcha API not ready yet
      setTimeout(checkRecaptcha, 100);
    };

    checkRecaptcha();

    // Cleanup on component unmount
    return () => {
      if (recaptchaWidgetId !== null && window.grecaptcha) {
        try {
          window.grecaptcha.reset(recaptchaWidgetId);
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
    };
  });

  function handleSelectionChange(category, contributionType) {
    // Selection changed
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

  // Explicitly render reCAPTCHA widget
  function renderRecaptcha() {
    if (typeof window === 'undefined' || !window.grecaptcha || !window.grecaptcha.render) {
      return false;
    }

    try {
      recaptchaWidgetId = window.grecaptcha.render('recaptcha-container', {
        sitekey: RECAPTCHA_SITE_KEY,
        callback: (token) => {
          recaptchaToken = token;
          // Clear any previous reCAPTCHA error
          if (error && error.includes('reCAPTCHA')) {
            error = '';
          }
        }
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    // Validate required fields
    if (!formData.contribution_type) {
      error = 'Please select a contribution type';
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

    // Validate reCAPTCHA
    if (!recaptchaToken) {
      error = 'Please complete the reCAPTCHA verification';
      return;
    }

    submitting = true;
    error = '';

    try {
      // Create the submission with reCAPTCHA token
      const submissionData = {
        contribution_type: formData.contribution_type,
        contribution_date: formData.contribution_date + 'T00:00:00Z',
        notes: formData.notes,
        recaptcha: recaptchaToken
      };

      // Include mission if selected
      if (selectedMission) {
        submissionData.mission = selectedMission;
      }

      const response = await api.post('/submissions/', submissionData);
      const submissionId = response.data.id;

      // Add evidence from slots that have content
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
      // Handle reCAPTCHA specific errors
      if (err.response?.data?.recaptcha) {
        error = Array.isArray(err.response.data.recaptcha)
          ? err.response.data.recaptcha[0]
          : err.response.data.recaptcha;
      } else {
        error = err.response?.data?.error || err.response?.data?.detail || 'Failed to submit contribution';
      }

      // Reset reCAPTCHA on error using widget ID
      if (recaptchaWidgetId !== null && window.grecaptcha) {
        try {
          window.grecaptcha.reset(recaptchaWidgetId);
          recaptchaToken = '';
        } catch (e) {
          // Error resetting reCAPTCHA silently handled
        }
      }
    } finally {
      submitting = false;
    }
  }
</script>

<div class="container mx-auto px-4 py-8">
  <h1 class="text-2xl font-bold mb-6">Submit Contribution</h1>

  {#if !authChecked || loading || loadingMission}
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
          bind:selectedMission
          defaultMission={missionId}
          defaultContributionType={formData.contribution_type}
          onlySubmittable={true}
          stewardMode={false}
          isValidator={!!$userStore.user?.validator}
          isBuilder={!!$userStore.user?.builder}
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

      <div class="mb-6">
        <div id="recaptcha-container"></div>
        {#if error && error.includes('reCAPTCHA')}
          <p class="text-red-500 text-sm mt-2">{error}</p>
        {/if}
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
