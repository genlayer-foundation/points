<script>
  import { push, querystring } from "svelte-spa-router";
  import { authState } from "../lib/auth.js";
  import api from "../lib/api.js";
  import { onMount } from "svelte";
  import { setConnectWalletIntent } from "../lib/analytics.js";
  import SubmitContributionForm from "../components/portal/submit-contribution/SubmitContribution.svelte";

  let authChecked = $state(false);
  /** @type {number | null} */
  let missionId = $state(null);
  /** @type {number | null} */
  let initialTypeId = $state(null);
  /** @type {string | null} */
  let resubmitId = $state(null);
  /** @type {Record<string, any> | null} */
  let resubmitSource = $state(null);
  let resubmitLoading = $state(false);
  let resubmitError = $state("");
  let resubmitCanRetry = $state(false);
  let loadedResubmitKey = $state("");
  let resubmitResultKey = $state("");
  let resubmitLoadSequence = 0;
  let activeResubmitKey = $derived(
    `${$authState.address || "authenticated"}:${resubmitId || ""}`,
  );

  /**
   * @param {string} id
   * @param {string} loadKey
   */
  async function loadResubmitSource(id, loadKey = activeResubmitKey) {
    const loadSequence = ++resubmitLoadSequence;
    resubmitLoading = true;
    resubmitError = "";
    resubmitCanRetry = false;
    resubmitSource = null;
    resubmitResultKey = "";
    try {
      const response = await api.get(
        `/submissions/${encodeURIComponent(id)}/`,
      );
      if (loadSequence !== resubmitLoadSequence) return;
      if (response.data?.state !== "rejected") {
        resubmitError = "Only a submission that is still rejected can be used to start a corrected submission.";
        resubmitResultKey = loadKey;
        return;
      }
      resubmitSource = response.data;
      resubmitResultKey = loadKey;
    } catch (caught) {
      if (loadSequence !== resubmitLoadSequence) return;
      const error = /** @type {any} */ (caught);
      if (error.response?.status === 404) {
        resubmitError = "Rejected submission not found for this account.";
      } else {
        resubmitError = "We couldn't load the rejected submission. Please try again.";
        resubmitCanRetry = true;
      }
      resubmitResultKey = loadKey;
    } finally {
      if (loadSequence === resubmitLoadSequence) {
        resubmitLoading = false;
      }
    }
  }

  onMount(async () => {
    // Parse query parameters
    const params = new URLSearchParams($querystring);
    const resubmitParam = params.get("resubmit");
    const missionParam = params.get("mission");
    const typeParam = params.get("type");

    // A rejected resubmission is a complete clone context and therefore wins
    // over ordinary mission/type preselection parameters.
    if (resubmitParam) {
      resubmitId = resubmitParam;
      missionId = null;
      initialTypeId = null;
    } else if (missionParam) {
      missionId = parseInt(missionParam);
    } else if (typeParam) {
      initialTypeId = parseInt(typeParam);
    }

    // Wait a moment for auth state to be verified
    await new Promise((resolve) => setTimeout(resolve, 100));
    authChecked = true;
  });

  // A user may open a resubmit link while signed out and authenticate without
  // remounting this route. Load again when the active wallet changes so clone
  // data can never leak across accounts or silently fall back to a blank form.
  $effect(() => {
    const key = activeResubmitKey;
    if (
      !authChecked ||
      !$authState.isAuthenticated ||
      !resubmitId ||
      loadedResubmitKey === key
    ) {
      return;
    }
    loadedResubmitKey = key;
    void loadResubmitSource(resubmitId, key);
  });
</script>

<div class="submit-contribution-route w-full px-4 py-[60px]">
  {#if !authChecked || resubmitLoading || (resubmitId && $authState.isAuthenticated && resubmitResultKey !== activeResubmitKey)}
    <div class="flex justify-center py-12">
      <div
        class="animate-spin rounded-full h-10 w-10 border-b-2 border-black"
      ></div>
    </div>
  {:else if !$authState.isAuthenticated}
    <div class="max-w-[550px] mx-auto">
      <div
        class="auth-required-card bg-white border border-[#f5f5f5] rounded-[16px] p-[32px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] text-center"
      >
        <svg
          class="mx-auto h-12 w-12 text-gray-300 mb-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
          />
        </svg>
        <h3 class="text-lg font-semibold text-black mb-2 font-['Switzer']">
          Authentication Required
        </h3>
        <p class="text-[14px] text-[#6b6b6b] mb-5 font-['Switzer']">
          Please connect your wallet to submit contributions.
        </p>
        <button
          onclick={() => {
            setConnectWalletIntent({
              surface: "form",
              cta_id: "submit_contribution_auth_prompt",
            });
            document.querySelector(".auth-button")?.click();
          }}
          class="bg-[#9e4bf6] text-white px-[20px] h-[40px] rounded-[20px] font-['Switzer'] font-medium text-[14px] hover:bg-[#8b3ced] transition-colors"
        >
          Connect Wallet
        </button>
      </div>
    </div>
  {:else if resubmitError}
    <div class="mx-auto max-w-[550px]">
      <div class="rounded-[16px] bg-white p-8 text-center shadow-[0_0_0_1px_rgba(0,0,0,0.05),0_8px_30px_rgba(0,0,0,0.04)]">
        <span class="mx-auto flex h-12 w-12 items-center justify-center rounded-[14px] bg-red-50 text-red-600">
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 9v3.75m9-1.875a9 9 0 11-18 0 9 9 0 0118 0zM12 16.5h.008v.008H12V16.5z" />
          </svg>
        </span>
        <h1 class="mt-4 font-heading text-[22px] font-semibold text-black">Unable to start resubmission</h1>
        <p class="mx-auto mt-2 max-w-[390px] text-pretty font-['Switzer'] text-[14px] leading-5 text-[#6b6b6b]">{resubmitError}</p>
        <div class="mt-5 flex flex-col justify-center gap-2 sm:flex-row">
          {#if resubmitCanRetry}
            <button
              type="button"
              onclick={() => {
                if (resubmitId) void loadResubmitSource(resubmitId);
              }}
              class="inline-flex min-h-10 items-center justify-center rounded-full bg-[#1a1c1d] px-5 font-['Switzer'] text-[14px] font-medium text-white hover:bg-black"
            >
              Try again
            </button>
          {/if}
          <button
            type="button"
            onclick={() => push("/my-submissions")}
            class="inline-flex min-h-10 items-center justify-center rounded-full bg-[#f5f5f5] px-5 font-['Switzer'] text-[14px] font-medium text-[#1a1c1d] hover:bg-[#eaeaea]"
          >
            Back to my submissions
          </button>
        </div>
      </div>
    </div>
  {:else}
    <SubmitContributionForm {missionId} {initialTypeId} {resubmitSource} />
  {/if}
</div>

<style>
  @media (max-width: 767px) {
    .submit-contribution-route {
      max-width: 100%;
      /* clip, not hidden: overflow-x hidden computes overflow-y to auto,
         making this wrapper a scroll container that cuts the type dropdown
         at the route's bottom edge (see frontend/CLAUDE.md, Common Issues) */
      overflow-x: clip;
      padding: 20px 12px 28px;
    }

    .auth-required-card {
      border-radius: 12px;
      padding: 24px 18px;
    }
  }
</style>
