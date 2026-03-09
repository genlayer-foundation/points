<script>
    import { push } from "svelte-spa-router";
    import AlertBanner from "../portal/AlertBanner.svelte";
    import ProfileHighlights from "./ProfileHighlights.svelte";
    import ProfileRecentContributions from "./ProfileRecentContributions.svelte";

    let {
        role = "builder",
        iconCategory = "builder",
        colorTheme = "orange",
        participant = null,
        stats = {
            points: 0,
            contributions: 0,
            rank: 0,
        },
        isOwnProfile = false,
        isWaitlist = false,
        loading = false,
    } = $props();

    // Helper to get formatted display name for the role
    let roleTitle = $derived(role.charAt(0).toUpperCase() + role.slice(1));

</script>

<div class="w-full flex flex-col items-start mt-8">
    <!-- Header -->
    <div class="flex items-center gap-[10px] mb-4">
        <div class="relative flex-shrink-0" style="width: 32px; height: 32px;">
            <img
                src={role === "builder"
                    ? "/assets/icons/hexagon-builder-light.svg"
                    : role === "validator"
                      ? "/assets/icons/hexagon-validator-light.svg"
                      : role === "community"
                        ? "/assets/icons/hexagon-community-light.svg"
                        : "/assets/icons/hexagon-light.svg"}
                alt=""
                class="w-full h-full"
            />
            <img
                src={role === "builder"
                    ? "/assets/icons/terminal-line-orange.svg"
                    : role === "validator"
                      ? "/assets/icons/folder-shield-line-blue.svg"
                      : role === "community"
                        ? "/assets/icons/group-3-line-purple.svg"
                        : "/assets/icons/dashboard-fill-black.svg"}
                alt=""
                class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                style="width: 16px; height: 16px;"
            />
        </div>
        <h2
            class="text-[20px] font-semibold text-black"
            style="letter-spacing: 0.4px;"
        >
            {roleTitle} Journey
        </h2>
    </div>

    {#if isWaitlist}
        <div class="w-full mb-4">
            <AlertBanner
                id="validator-waitlist"
                alertType="blue"
                text={isOwnProfile
                    ? "You've joined the <strong>Validator Waitlist</strong>. You're waiting to be graduated to the role of Validator. In the meantime, keep contributing to earn points and climb the ranks."
                    : "This user is on the <strong>Validator Waitlist</strong>, waiting to be graduated to the role of Validator."}
            />
        </div>
    {/if}

    <!-- Metrics Row -->
    <div class="flex flex-col md:flex-row gap-4 mb-10 w-full">
        <!-- Total Role Points Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if loading}
                <div class="flex h-full items-center animate-pulse">
                    <div class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"></div>
                    <div class="flex flex-col gap-2">
                        <div class="h-7 w-16 bg-gray-200 rounded"></div>
                        <div class="h-3 w-28 bg-gray-100 rounded"></div>
                    </div>
                </div>
            {:else}
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <img
                            src={role === "builder"
                                ? "/assets/icons/hexagon-builder.svg"
                                : role === "validator"
                                  ? "/assets/icons/hexagon-validator.svg"
                                  : role === "community"
                                    ? "/assets/icons/hexagon-community.svg"
                                    : "/assets/icons/hexagon-genlayer.svg"}
                            alt=""
                            class="w-full h-full"
                        />
                        <img
                            src={role === "builder"
                                ? "/assets/icons/terminal-fill-white.svg"
                                : role === "validator"
                                  ? "/assets/icons/shield-white.svg"
                                  : role === "community"
                                    ? "/assets/icons/group-white.svg"
                                    : "/assets/icons/gl-symbol-white.svg"}
                            alt=""
                            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                            style="width: 24px; height: 24px;"
                        />
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {stats.points || 0}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            Total {role.toLowerCase()} points
                        </p>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Total Contributions Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if loading}
                <div class="flex h-full items-center animate-pulse">
                    <div class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"></div>
                    <div class="flex flex-col gap-2">
                        <div class="h-7 w-16 bg-gray-200 rounded"></div>
                        <div class="h-3 w-28 bg-gray-100 rounded"></div>
                    </div>
                </div>
            {:else}
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <img
                            src={role === "builder"
                                ? "/assets/icons/hexagon-builder.svg"
                                : role === "validator"
                                  ? "/assets/icons/hexagon-validator.svg"
                                  : role === "community"
                                    ? "/assets/icons/hexagon-community.svg"
                                    : "/assets/icons/hexagon-genlayer.svg"}
                            alt=""
                            class="w-full h-full"
                        />
                        {#if role === "validator"}
                            <svg
                                class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                                style="width: 26px; height: 26px;"
                                viewBox="0 0 32 32"
                                fill="none"
                                stroke="white"
                                stroke-width="2"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <path d="M19 2H7c-.552 0-1 .448-1 1v24c0 .552.448 1 1 1h10" />
                                <path d="M26 9V9l-7-7" />
                                <path d="M19 2v6c0 .552.448 1 1 1h6" />
                                <path d="M17 13v10.5l5 3 5-3V13H17z" stroke-width="2.5" />
                            </svg>
                        {:else}
                            <svg
                                class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 text-white"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                            >
                                <path
                                    d="M3 2.992C3 2.444 3.445 2 3.993 2h16.014A1 1 0 0 1 21 2.992v18.016a1 1 0 0 1-.993.992H3.993A.993.993 0 0 1 3 21.008V2.992zM5 4v16h14V4H5zm4.293 7.293l-2 2a1 1 0 0 0 0 1.414l2 2 1.414-1.414L9.414 14l1.293-1.293-1.414-1.414zm5.414 0l-1.414 1.414L14.586 14l-1.293 1.293 1.414 1.414 2-2a1 1 0 0 0 0-1.414l-2-2z"
                                />
                            </svg>
                        {/if}
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {stats.contributions || 0}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            Total Contributions
                        </p>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Rank Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if loading}
                <div class="flex h-full items-center animate-pulse">
                    <div class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"></div>
                    <div class="flex flex-col gap-2">
                        <div class="h-7 w-16 bg-gray-200 rounded"></div>
                        <div class="h-3 w-24 bg-gray-100 rounded"></div>
                    </div>
                </div>
            {:else}
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <img
                            src={role === "builder"
                                ? "/assets/icons/hexagon-builder.svg"
                                : role === "validator"
                                  ? "/assets/icons/hexagon-validator.svg"
                                  : role === "community"
                                    ? "/assets/icons/hexagon-community.svg"
                                    : "/assets/icons/hexagon-genlayer.svg"}
                            alt=""
                            class="w-full h-full"
                        />
                        <svg
                            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-5 h-5 text-white"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                        >
                            <path
                                d="M2 13h6v8H2v-8zM9 3h6v18H9V3zm7 5h6v13h-6V8z"
                            />
                        </svg>
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            #{stats.rank || "-"}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            {roleTitle} Rank
                        </p>
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <!-- Content Sections -->
    <div class="space-y-12 w-full mt-4">
        <div class="w-full">
            <div class="flex items-start justify-between mb-[20px]">
                <div>
                    <h3
                        class="font-semibold text-[20px] text-black"
                        style="letter-spacing: 0.4px;"
                    >
                        Highlights
                    </h3>
                    <p class="text-[14px] text-[#999] mt-1">
                        Get highlighted: submit impactful or pioneering work to get highlighted
                    </p>
                </div>
                <button
                    onclick={() => push("/submit-contribution")}
                    class="flex items-center gap-[6px] bg-[#101010] text-white px-4 py-2 rounded-[24px] text-[14px] font-medium hover:bg-black transition-colors whitespace-nowrap shrink-0"
                >
                    Submit contribution
                    <img
                        src="/assets/icons/arrow-right-line.svg"
                        alt=""
                        class="w-4 h-4 brightness-0 invert"
                    />
                </button>
            </div>
            <ProfileHighlights
                userId={participant?.address}
                limit={3}
                category={iconCategory}
                {isOwnProfile}
            />
        </div>

        <div class="w-full">
            <h3
                class="font-semibold text-[20px] text-black mb-[20px]"
                style="letter-spacing: 0.4px;"
            >
                Recent Contributions
            </h3>
            <ProfileRecentContributions
                userId={participant?.address}
                limit={5}
                category={iconCategory}
                showViewAll={true}
                viewAllPath={`/all-contributions?user=${participant?.address}&category=${iconCategory}`}
                viewAllText={`View All ${roleTitle} Contributions →`}
            />
        </div>
    </div>
</div>

