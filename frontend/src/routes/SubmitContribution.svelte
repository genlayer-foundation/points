<script>
  import { querystring } from "svelte-spa-router";
  import { authState } from "../lib/auth.js";
  import { onMount } from "svelte";
  import SubmitContributionForm from "../components/portal/submit-contribution/SubmitContribution.svelte";

  let authChecked = $state(false);
  let missionId = $state(null);
  let initialTypeId = $state(null);

  onMount(async () => {
    // Parse query parameters
    const params = new URLSearchParams($querystring);
    const missionParam = params.get("mission");
    const typeParam = params.get("type");

    if (missionParam) {
      missionId = parseInt(missionParam);
    }
    if (typeParam) {
      initialTypeId = parseInt(typeParam);
    }

    // Wait a moment for auth state to be verified
    await new Promise((resolve) => setTimeout(resolve, 100));
    authChecked = true;
  });
</script>

<div class="w-full px-4 py-[60px]">
  {#if !authChecked}
    <div class="flex justify-center py-12">
      <div
        class="animate-spin rounded-full h-10 w-10 border-b-2 border-black"
      ></div>
    </div>
  {:else if !$authState.isAuthenticated}
    <div class="max-w-[550px] mx-auto">
      <div
        class="bg-white border border-[#f5f5f5] rounded-[16px] p-[32px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] text-center"
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
          onclick={() => document.querySelector(".auth-button")?.click()}
          class="bg-[#9e4bf6] text-white px-[20px] h-[40px] rounded-[20px] font-['Switzer'] font-medium text-[14px] hover:bg-[#8b3ced] transition-colors"
        >
          Connect Wallet
        </button>
      </div>
    </div>
  {:else}
    <SubmitContributionForm {missionId} {initialTypeId} />
  {/if}
</div>
