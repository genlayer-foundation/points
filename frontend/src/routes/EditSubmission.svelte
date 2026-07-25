<script>
  import { push } from "svelte-spa-router";
  import api from "../lib/api.js";
  import { authState } from "../lib/auth.js";
  import SubmitContributionForm from "../components/portal/submit-contribution/SubmitContribution.svelte";

  let { params = {} } = $props();

  let submission = $state(null);
  let loading = $state(true);
  let error = $state("");
  let loadedSubmissionId = $state(null);
  let requestVersion = 0;

  async function loadSubmission(id) {
    const currentRequest = ++requestVersion;
    loading = true;
    error = "";
    submission = null;

    try {
      const response = await api.get(`/submissions/${id}/`);
      if (currentRequest !== requestVersion) return;

      const loadedSubmission = response.data;
      if (!loadedSubmission?.can_edit) {
        error = "This submission can no longer be edited.";
        return;
      }
      submission = loadedSubmission;
    } catch (err) {
      if (currentRequest !== requestVersion) return;
      if (err.response?.status === 404) {
        error = "Submission not found.";
      } else if (err.response?.status === 403) {
        error = "You do not have permission to edit this submission.";
      } else {
        error = "We couldn't load this submission. Please try again.";
      }
    } finally {
      if (currentRequest === requestVersion) loading = false;
    }
  }

  $effect(() => {
    const id = params.id;
    if (!$authState.isAuthenticated || !id) {
      requestVersion += 1;
      loadedSubmissionId = null;
      submission = null;
      loading = false;
      return;
    }
    if (String(loadedSubmissionId) === String(id)) return;
    loadedSubmissionId = id;
    loadSubmission(id);
  });
</script>

<div class="edit-submission-route w-full px-4 py-[60px]">
  {#if loading}
    <div class="mx-auto flex min-h-[360px] max-w-[620px] items-center justify-center">
      <div class="flex flex-col items-center gap-3 text-[#6b6b6b]">
        <span class="h-9 w-9 animate-spin rounded-full border-[3px] border-black/10 border-t-black"></span>
        <p class="font-['Switzer'] text-[13px]">Loading submission...</p>
      </div>
    </div>
  {:else if !$authState.isAuthenticated}
    <div class="mx-auto max-w-[550px]">
      <div class="rounded-[16px] bg-white p-8 text-center shadow-[0_0_0_1px_rgba(0,0,0,0.05),0_8px_30px_rgba(0,0,0,0.04)]">
        <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-[14px] bg-[#f5f5f5] text-[#6b6b6b]">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2h-1V9a4 4 0 00-8 0v2H6a2 2 0 00-2 2v6a2 2 0 002 2zm3-10V9a3 3 0 00-6 0v2h6z" />
          </svg>
        </span>
        <h1 class="mt-4 text-balance font-heading text-[22px] font-semibold text-black">
          Authentication required
        </h1>
        <p class="mx-auto mt-2 max-w-[340px] text-pretty font-['Switzer'] text-[14px] leading-5 text-[#6b6b6b]">
          Connect the wallet that submitted this contribution to continue editing.
        </p>
        <button
          type="button"
          onclick={() => push("/")}
          class="mt-5 inline-flex min-h-10 items-center justify-center rounded-full bg-[#1a1c1d] px-5 font-['Switzer'] text-[14px] font-medium text-white transition-[background-color,scale] duration-150 ease-out hover:bg-black active:scale-[0.96]"
        >
          Return to overview
        </button>
      </div>
    </div>
  {:else if error}
    <div class="mx-auto max-w-[550px]">
      <div class="rounded-[16px] bg-white p-8 text-center shadow-[0_0_0_1px_rgba(0,0,0,0.05),0_8px_30px_rgba(0,0,0,0.04)]">
        <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-[14px] bg-red-50 text-red-600">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v3.75m9-1.875a9 9 0 11-18 0 9 9 0 0118 0zM12 16.5h.008v.008H12V16.5z" />
          </svg>
        </span>
        <h1 class="mt-4 text-balance font-heading text-[22px] font-semibold text-black">
          Submission unavailable
        </h1>
        <p class="mx-auto mt-2 max-w-[380px] text-pretty font-['Switzer'] text-[14px] leading-5 text-[#6b6b6b]">
          {error}
        </p>
        <div class="mt-5 flex flex-col justify-center gap-2 sm:flex-row">
          {#if error.includes("couldn't load")}
            <button
              type="button"
              onclick={() => loadSubmission(params.id)}
              class="inline-flex min-h-10 items-center justify-center rounded-full bg-[#1a1c1d] px-5 font-['Switzer'] text-[14px] font-medium text-white transition-[background-color,scale] duration-150 ease-out hover:bg-black active:scale-[0.96]"
            >
              Try again
            </button>
          {/if}
          <button
            type="button"
            onclick={() => push("/my-submissions")}
            class="inline-flex min-h-10 items-center justify-center rounded-full bg-[#f5f5f5] px-5 font-['Switzer'] text-[14px] font-medium text-[#1a1c1d] transition-[background-color,scale] duration-150 ease-out hover:bg-[#eaeaea] active:scale-[0.96]"
          >
            Back to my submissions
          </button>
        </div>
      </div>
    </div>
  {:else if submission}
    <SubmitContributionForm {submission} />
  {/if}
</div>

<style>
  @media (max-width: 767px) {
    .edit-submission-route {
      max-width: 100%;
      overflow-x: clip;
      padding: 20px 12px 28px;
    }
  }
</style>
