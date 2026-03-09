<script>
  import { push } from "svelte-spa-router";
  import CategoryIcon from "../portal/CategoryIcon.svelte";

  let { participant = null, onJoinCommunity = () => {}, onApplyBuilder = () => {} } = $props();

  let isApplyingBuilder = $state(false);

  async function handleApplyBuilder() {
    isApplyingBuilder = true;
    try {
      await onApplyBuilder();
    } finally {
      isApplyingBuilder = false;
    }
  }

  // Builder Journey States
  let builderState = $derived(
    participant?.builder
      ? "completed"
      : participant?.has_builder_welcome
        ? "ongoing"
        : "not_started",
  );

  // Validator Journey States
  let validatorState = $derived(
    participant?.validator
      ? "completed"
      : participant?.has_validator_waitlist
        ? "ongoing"
        : "not_started",
  );

  // Community States
  let communityState = $derived(
    participant?.creator ? "completed" : "not_started",
  );

  function scrollToBuilderJourney() {
    const el = document.querySelector(".w-full.mb-10 .progress-journey, .w-full.mb-10");
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }
</script>

<div class="mt-8">
  <div class="flex items-center justify-between mb-4">
      <h2
        class="text-[20px] font-semibold text-black"
        style="letter-spacing: 0.4px;"
      >
        Your Journeys
      </h2>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <!-- Builder Journey Card -->
    <div
      class="bg-[#ffffff] border border-[#f0f0f0] rounded-[16px] p-6 flex flex-col justify-between h-[220px]"
    >
      <div>
        <div class="flex items-start justify-between mb-3">
          <h3 class="text-[18px] font-semibold text-black leading-tight" style="font-family: 'F37 Lineca', 'Geist', sans-serif;">
            Start as a Builder
          </h3>
          <CategoryIcon category="builder" mode="hexagon" size={40} />
        </div>
        <p class="text-[14px] text-[#6b6b6b] leading-snug">
          Deploy intelligent contracts and contribute repos to earn builder
          points.
        </p>
      </div>

      <div class="flex gap-2 w-full mt-4">
        {#if builderState === "completed"}
          <button
            disabled
            class="flex-1 bg-[#ee8521]/10 text-[#ee8521] py-2 rounded-[24px] text-[14px] font-medium cursor-default"
          >
            <svg class="inline w-4 h-4 mr-1 -mt-0.5" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/></svg>
            Completed
          </button>
        {:else if builderState === "ongoing"}
          <button
            onclick={scrollToBuilderJourney}
            class="flex-1 bg-[#ee8521] text-white py-2 rounded-[24px] text-[14px] font-medium hover:bg-[#d9751a] transition-colors"
          >
            Finish the journey <img
              src="/assets/icons/arrow-right-line.svg"
              class="inline w-4 h-4 ml-1 brightness-0 invert"
              alt=""
            />
          </button>
        {:else}
          <button
            onclick={handleApplyBuilder}
            disabled={isApplyingBuilder}
            class="flex-1 bg-[#101010] text-white py-2 rounded-[24px] text-[14px] font-medium hover:bg-black transition-colors disabled:opacity-70"
          >
            {#if isApplyingBuilder}
              Applying...
            {:else}
              Apply for the role <img
                src="/assets/icons/arrow-right-line.svg"
                class="inline w-4 h-4 ml-1 brightness-0 invert"
                alt=""
              />
            {/if}
          </button>
        {/if}

        <button
          class="flex-1 py-2 bg-white border border-[#e0e0e0] rounded-[24px] text-[14px] font-medium text-black hover:bg-gray-50 transition-colors whitespace-nowrap"
        >
          Learn more
        </button>
      </div>
    </div>

    <!-- Validator Journey Card -->
    <div
      class="bg-[#ffffff] border border-[#f0f0f0] rounded-[16px] p-6 flex flex-col justify-between h-[220px]"
    >
      <div>
        <div class="flex items-start justify-between mb-3">
          <h3 class="text-[18px] font-semibold text-black leading-tight" style="font-family: 'F37 Lineca', 'Geist', sans-serif;">
            Become a Validator
          </h3>
          <CategoryIcon category="validator" mode="hexagon" size={40} />
        </div>
        <p class="text-[14px] text-[#6b6b6b] leading-snug">
          Operate a node to secure the network and participate in consensus to
          earn rewards.
        </p>
      </div>

      <div class="flex gap-2 w-full mt-4">
        {#if validatorState === "completed"}
          <button
            disabled
            class="flex-1 bg-[#387de8]/10 text-[#387de8] py-2 rounded-[24px] text-[14px] font-medium cursor-default"
          >
            <svg class="inline w-4 h-4 mr-1 -mt-0.5" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/></svg>
            Completed
          </button>
        {:else if validatorState === "ongoing"}
          <button
            disabled
            class="flex-1 bg-[#387de8]/10 text-[#387de8] py-2 rounded-[24px] text-[14px] font-medium cursor-default"
          >
            <svg class="inline w-4 h-4 mr-1 -mt-0.5" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/></svg>
            Awaiting graduation
          </button>
        {:else}
          <button
            onclick={() => push("/validators/waitlist/join")}
            class="flex-1 bg-[#101010] text-white py-2 rounded-[24px] text-[14px] font-medium hover:bg-black transition-colors"
          >
            Join the waitlist <img
              src="/assets/icons/arrow-right-line.svg"
              class="inline w-4 h-4 ml-1 brightness-0 invert"
              alt=""
            />
          </button>
        {/if}

        <button
          class="flex-1 py-2 bg-white border border-[#e0e0e0] rounded-[24px] text-[14px] font-medium text-black hover:bg-gray-50 transition-colors whitespace-nowrap"
        >
          Learn more
        </button>
      </div>
    </div>

    <!-- Community Journey Card -->
    <div
      class="bg-[#ffffff] border border-[#f0f0f0] rounded-[16px] p-6 flex flex-col justify-between h-[220px]"
    >
      <div>
        <div class="flex items-start justify-between mb-3">
          <h3 class="text-[18px] font-semibold text-black leading-tight" style="font-family: 'F37 Lineca', 'Geist', sans-serif;">
            Join the community
          </h3>
          <CategoryIcon category="community" mode="hexagon" size={40} />
        </div>
        <p class="text-[14px] text-[#6b6b6b] leading-snug">
          Invite others to GenLayer and earn 10% of the points they make,
          forever.
        </p>
      </div>

      <div class="flex gap-2 w-full mt-4">
        {#if communityState === "completed"}
          <button
            disabled
            class="flex-1 bg-[#7f52e1]/10 text-[#7f52e1] py-2 rounded-[24px] text-[14px] font-medium cursor-default"
          >
            <svg class="inline w-4 h-4 mr-1 -mt-0.5" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/></svg>
            Completed
          </button>
        {:else}
          <button
            onclick={onJoinCommunity}
            class="flex-1 bg-[#101010] text-white py-2 rounded-[24px] text-[14px] font-medium hover:bg-black transition-colors"
          >
            Become a referrer <img
              src="/assets/icons/arrow-right-line.svg"
              class="inline w-4 h-4 ml-1 brightness-0 invert"
              alt=""
            />
          </button>
        {/if}

        <button
          class="flex-1 py-2 bg-white border border-[#e0e0e0] rounded-[24px] text-[14px] font-medium text-black hover:bg-gray-50 transition-colors whitespace-nowrap"
        >
          Learn more
        </button>
      </div>
    </div>
  </div>
</div>
