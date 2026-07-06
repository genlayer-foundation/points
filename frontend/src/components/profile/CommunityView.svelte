<script>
    import { push } from "svelte-spa-router";
    import ProfileHighlights from "./ProfileHighlights.svelte";
    import ProfileRecentContributions from "./ProfileRecentContributions.svelte";
    import ProfilePoaps from "../poaps/ProfilePoaps.svelte";

    let {
        participant = null,
        isOwnProfile = false,
        communityStats = { totalContributions: 0, totalPoints: 0 },
        communityStatsLoading = false,
        poapCount = 0,
        poapCountLoading = false,
    } = $props();

    let showCommunityActivity = $derived(Boolean(participant?.creator));
    let showPoaps = $derived(poapCount > 0);
</script>

<div class="community-view w-full flex flex-col items-start mt-8">
    <!-- Header -->
    <div class="community-view-header flex items-center justify-between w-full mb-4 gap-3">
        <div class="flex items-center gap-[10px]">
            <div
                class="relative flex-shrink-0"
                style="width: 32px; height: 32px;"
            >
                <img
                    src="/assets/icons/hexagon-community-light.svg"
                    alt=""
                    class="w-full h-full"
                />
                <img
                    src="/assets/icons/group-3-line-purple.svg"
                    alt=""
                    class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                    style="width: 16px; height: 16px;"
                />
            </div>
            <h2
                class="text-[20px] font-semibold text-black"
                style="letter-spacing: 0.4px;"
            >
                Community
            </h2>
        </div>
        {#if showCommunityActivity}
            <span
                class="text-[12px] font-medium text-[#ac6df3] tracking-[0.24px] leading-[16px]"
            >
                Creator
            </span>
        {/if}
    </div>

    <!-- Metrics Row: 2 cards -->
    <div class="community-metrics flex flex-col md:flex-row gap-4 w-full">
        {#if showCommunityActivity}
            <!-- Community Points Card -->
            <div
                class="community-metric-card bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
            >
                {#if communityStatsLoading}
                    <div class="flex h-full items-center animate-pulse">
                        <div
                            class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                        ></div>
                        <div class="flex flex-col gap-2">
                            <div class="h-7 w-16 bg-gray-200 rounded"></div>
                            <div class="h-3 w-28 bg-gray-100 rounded"></div>
                        </div>
                    </div>
                {:else}
                    <div class="community-metric-content flex h-full items-center min-w-0">
                        <div
                            class="community-metric-icon w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                        >
                            <img
                                src="/assets/icons/hexagon-community.svg"
                                alt=""
                                class="w-full h-full"
                            />
                            <img
                                src="/assets/icons/group-white.svg"
                                alt=""
                                class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                                style="width: 24px; height: 24px;"
                            />
                        </div>
                        <div
                            class="community-metric-text flex flex-col h-full items-start justify-center whitespace-nowrap z-10 min-w-0"
                        >
                            <p
                                class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                            >
                                {communityStats.totalPoints || 0}
                            </p>
                            <p
                                class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                            >
                                Community Points
                            </p>
                        </div>
                    </div>
                {/if}
            </div>
        {/if}

        {#if showCommunityActivity}
            <!-- Community Contributions Card -->
            <div
                class="community-metric-card bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
            >
                {#if communityStatsLoading}
                    <div class="flex h-full items-center animate-pulse">
                        <div
                            class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                        ></div>
                        <div class="flex flex-col gap-2">
                            <div class="h-7 w-16 bg-gray-200 rounded"></div>
                            <div class="h-3 w-28 bg-gray-100 rounded"></div>
                        </div>
                    </div>
                {:else}
                    <div class="community-metric-content flex h-full items-center min-w-0">
                        <div
                            class="community-metric-icon w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                        >
                            <img
                                src="/assets/icons/hexagon-community.svg"
                                alt=""
                                class="w-full h-full"
                            />
                            <svg
                                class="community-contributions-icon absolute text-white"
                                viewBox="0 0 24 24"
                                fill="currentColor"
                                aria-hidden="true"
                            >
                                <path
                                    d="M21 8V20.9932C21 21.5501 20.5552 22 20.0066 22H3.9934C3.44495 22 3 21.556 3 21.0082V2.9918C3 2.44405 3.44476 2 3.9934 2H14.9968L21 8ZM19 9H14V4H5V20H19V9ZM8 12H16V14H8V12ZM8 16H16V18H8V16Z"
                                />
                            </svg>
                        </div>
                        <div
                            class="community-metric-text flex flex-col h-full items-start justify-center whitespace-nowrap z-10 min-w-0"
                        >
                            <p
                                class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                            >
                                {communityStats.totalContributions || 0}
                            </p>
                            <p
                                class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                            >
                                Community Contributions
                            </p>
                        </div>
                    </div>
                {/if}
            </div>
        {/if}

        <!-- POAPs Card -->
        <div
            class="community-metric-card bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if poapCountLoading}
                <div class="flex h-full items-center animate-pulse">
                    <div
                        class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                    ></div>
                    <div class="flex flex-col gap-2">
                        <div class="h-7 w-16 bg-gray-200 rounded"></div>
                        <div class="h-3 w-20 bg-gray-100 rounded"></div>
                    </div>
                </div>
            {:else}
                <div class="community-metric-content flex h-full items-center min-w-0">
                    <div
                        class="community-metric-icon w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <img
                            src="/assets/icons/hexagon-community.svg"
                            alt=""
                            class="w-full h-full"
                        />
                        <span class="community-poap-icon" aria-hidden="true"></span>
                    </div>
                    <div
                        class="community-metric-text flex flex-col h-full items-start justify-center whitespace-nowrap z-10 min-w-0"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {poapCount || 0}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            POAPs
                        </p>
                    </div>
                </div>
            {/if}
        </div>

    </div>

    <!-- Content Sections -->
    <div class="space-y-12 w-full mt-4">
        {#if showPoaps}
            <ProfilePoaps userId={participant?.id ?? participant?.address} />
        {/if}

        {#if showCommunityActivity}
            <div class="w-full">
                <div class="community-section-header flex items-start justify-between mb-[20px] gap-4">
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
                        class="community-submit-button flex items-center gap-[6px] bg-[#101010] text-white px-4 py-2 rounded-[24px] text-[14px] font-medium hover:bg-black transition-colors whitespace-nowrap shrink-0"
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
                    userId={participant?.id ?? participant?.address}
                    limit={3}
                    category="community"
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
                    userId={participant?.id ?? participant?.address}
                    limit={5}
                    category="community"
                    showViewAll={true}
                    viewAllPath={`/all-contributions?user=${participant?.address}&category=community`}
                    viewAllText="View All Community Contributions →"
                />
            </div>
        {/if}
    </div>
</div>

<style>
    .community-contributions-icon {
        height: 24px;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        width: 24px;
    }

    .community-poap-icon {
        background:
            radial-gradient(circle at 32% 24%, rgba(255, 255, 255, 0.9), transparent 28%),
            linear-gradient(135deg, #ffffff, #ded8ff 46%, #7f52e1);
        border: 2px solid #fff;
        border-radius: 999px;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.48);
        height: 25px;
        left: 50%;
        position: absolute;
        top: 50%;
        transform: translate(-50%, -50%);
        width: 25px;
    }

    @media (max-width: 767px) {
        .community-view {
            margin-top: 24px;
            max-width: 100%;
            overflow-x: hidden;
        }

        .community-view-header {
            align-items: flex-start;
        }

        .community-metrics {
            gap: 10px;
        }

        .community-metric-card {
            height: 80px;
            min-width: 0;
            border-radius: 12px;
            padding: 16px;
        }

        .community-metric-icon {
            height: 40px;
            width: 40px;
            margin-right: 12px;
        }

        .community-metric-icon :global(img),
        .community-metric-icon :global(svg) {
            max-height: 40px;
            max-width: 40px;
        }

        .community-contributions-icon {
            height: 20px;
            width: 20px;
        }

        .community-metric-text {
            white-space: normal;
        }

        .community-metric-text p:first-child {
            font-size: 25px;
            line-height: 27px;
            letter-spacing: 0 !important;
        }

        .community-metric-text p:last-child {
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .community-section-header {
            align-items: stretch;
            flex-direction: column;
        }

        .community-submit-button {
            justify-content: center;
            width: 100%;
            min-height: 40px;
        }
    }
</style>
