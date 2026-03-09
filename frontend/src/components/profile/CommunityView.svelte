<script>
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let {
        participant = null,
        referralData = null,
        referralPoints = { builder_points: 0, validator_points: 0 },
        loading = false,
    } = $props();

    let totalReferrals = $derived(
        referralData?.total_referrals || participant?.creator?.total_referrals || 0
    );
    let builderReferralPoints = $derived(referralPoints?.builder_points || 0);
    let validatorReferralPoints = $derived(referralPoints?.validator_points || 0);
</script>

<div class="w-full flex flex-col items-start mt-8">
    <!-- Header -->
    <div class="flex items-center gap-[10px] mb-4">
        <div class="relative flex-shrink-0" style="width: 32px; height: 32px;">
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

    <!-- Metrics Row -->
    <div class="flex flex-col md:flex-row gap-4 w-full">
        <!-- Total Referrals Card -->
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
                        <CategoryIcon category="community" mode="hexagon" size={48} />
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
                        <CategoryIcon category="builder" mode="hexagon" size={48} />
                        <div class="absolute -bottom-[2px] -right-[2px]">
                            <CategoryIcon category="community" mode="hexagon" size={20} />
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
                        <CategoryIcon category="validator" mode="hexagon" size={48} />
                        <div class="absolute -bottom-[2px] -right-[2px]">
                            <CategoryIcon category="community" mode="hexagon" size={20} />
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
</div>
