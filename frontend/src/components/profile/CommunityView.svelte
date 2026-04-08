<script>
    import { push } from "svelte-spa-router";
    import CategoryIcon from "../portal/CategoryIcon.svelte";
    import ProfileHighlights from "./ProfileHighlights.svelte";
    import ProfileRecentContributions from "./ProfileRecentContributions.svelte";
    import { showSuccess } from "../../lib/toastStore";

    let {
        participant = null,
        referralData = null,
        referralPoints = { builder_points: 0, validator_points: 0 },
        loading = false,
        isOwnProfile = false,
        communityStats = { totalContributions: 0, totalPoints: 0 },
        communityStatsLoading = false,
    } = $props();

    let totalReferrals = $derived(
        referralData?.total_referrals ||
            participant?.creator?.total_referrals ||
            0,
    );
    let builderReferralPoints = $derived(referralPoints?.builder_points || 0);
    let validatorReferralPoints = $derived(
        referralPoints?.validator_points || 0,
    );

    function copyReferralLink() {
        const referralLink = `https://portal.genlayer.foundation/?ref=${participant?.referral_code || ""}`;
        navigator.clipboard.writeText(referralLink);
        showSuccess("Referral link copied!");
    }
</script>

<div class="w-full flex flex-col items-start mt-8">
    <!-- Header -->
    <div class="flex items-center justify-between w-full mb-4">
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
        <span
            class="text-[12px] font-medium text-[#ac6df3] tracking-[0.24px] leading-[16px]"
        >
            Community Member
        </span>
    </div>

    <!-- Referral Program Banner -->
    <div
        class="bg-[#f4ecfd] w-full rounded-[9px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] p-[20px] mb-4"
    >
        <div
            class="flex flex-col md:flex-row md:items-end md:justify-between gap-4"
        >
            <div class="flex flex-col gap-[4px]">
                <p
                    class="font-['Switzer'] font-semibold text-[20px] text-black leading-[25px] tracking-[0.4px]"
                >
                    Invite and earn forever.
                </p>
                <p
                    class="font-['Switzer'] text-[14px] text-[#6b6b6b] leading-[21px] tracking-[0.28px]"
                >
                    For each builder referred who submits at least one
                    contribution, you receive 10% of the points that the builder
                    earns permanently.
                </p>
            </div>
            {#if isOwnProfile}
                <button
                    onclick={copyReferralLink}
                    class="bg-[#1a1c1d] flex gap-[8px] h-[40px] items-center justify-center px-[16px] rounded-[20px] hover:bg-black transition-colors shrink-0"
                >
                    <svg
                        class="w-4 h-4 text-white"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    >
                        <path
                            d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"
                        ></path>
                        <path
                            d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"
                        ></path>
                    </svg>
                    <span
                        class="font-['Switzer'] font-medium text-[14px] text-white leading-[21px] tracking-[0.28px] whitespace-nowrap"
                    >
                        Copy Referral Link
                    </span>
                </button>
            {/if}
        </div>
    </div>

    <!-- Metrics Row -->
    <div class="flex flex-col md:flex-row gap-4 w-full">
        <!-- Total Referrals Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if loading}
                <div class="flex h-full items-center animate-pulse">
                    <div
                        class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                    ></div>
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
                        <CategoryIcon
                            category="community"
                            mode="hexagon"
                            size={48}
                        />
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {totalReferrals}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            Total Referrals
                        </p>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Builder Referral Points Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if loading}
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
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <CategoryIcon
                            category="builder"
                            mode="hexagon"
                            size={48}
                        />
                        <div class="absolute -bottom-[2px] -right-[2px]">
                            <CategoryIcon
                                category="community"
                                mode="hexagon"
                                size={20}
                            />
                        </div>
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {builderReferralPoints}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            Builder Referral Points
                        </p>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Validator Referral Points Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            {#if loading}
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
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <CategoryIcon
                            category="validator"
                            mode="hexagon"
                            size={48}
                        />
                        <div class="absolute -bottom-[2px] -right-[2px]">
                            <CategoryIcon
                                category="community"
                                mode="hexagon"
                                size={20}
                            />
                        </div>
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {validatorReferralPoints}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            Validator Referral Points
                        </p>
                    </div>
                </div>
            {/if}
        </div>
    </div>

    <!-- Community Contributions Stats -->
    <div class="flex flex-col md:flex-row gap-4 w-full mt-4">
        <!-- Community Points Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
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
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
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
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {communityStats.totalPoints || 0}
                        </p>
                        <p
                            class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                        >
                            Total community points
                        </p>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Community Contributions Count Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
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
                <div class="flex h-full items-center">
                    <div
                        class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                    >
                        <img
                            src="/assets/icons/hexagon-community.svg"
                            alt=""
                            class="w-full h-full"
                        />
                        <svg
                            class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-6 h-6 text-white"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                        >
                            <path
                                d="M3 2.992C3 2.444 3.445 2 3.993 2h16.014A1 1 0 0 1 21 2.992v18.016a1 1 0 0 1-.993.992H3.993A.993.993 0 0 1 3 21.008V2.992zM5 4v16h14V4H5zm4.293 7.293l-2 2a1 1 0 0 0 0 1.414l2 2 1.414-1.414L9.414 14l1.293-1.293-1.414-1.414zm5.414 0l-1.414 1.414L14.586 14l-1.293 1.293 1.414 1.414 2-2a1 1 0 0 0 0-1.414l-2-2z"
                            />
                        </svg>
                    </div>
                    <div
                        class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                    >
                        <p
                            class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                        >
                            {communityStats.totalContributions || 0}
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
                userId={participant?.address}
                limit={5}
                category="community"
                showViewAll={true}
                viewAllPath={`/all-contributions?user=${participant?.address}&category=community`}
                viewAllText="View All Community Contributions →"
            />
        </div>
    </div>
</div>
