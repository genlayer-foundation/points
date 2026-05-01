<script>
    import { push } from "svelte-spa-router";
    import Avatar from "../Avatar.svelte";
    import CategoryIcon from "../portal/CategoryIcon.svelte";
    import { showSuccess } from "../../lib/toastStore";

    let {
        participant = null,
        referralData = null,
        referralPoints = { builder_points: 0, validator_points: 0 },
        loading = false,
        isOwnProfile = false,
    } = $props();

    let totalReferrals = $derived(referralData?.total_referrals ?? 0);
    let builderReferralPoints = $derived(referralPoints?.builder_points ?? 0);
    let validatorReferralPoints = $derived(referralPoints?.validator_points ?? 0);
    let totalReferralPoints = $derived(builderReferralPoints + validatorReferralPoints);

    let topReferrals = $derived(
        (referralData?.referrals ?? [])
            .slice()
            .sort((a, b) => {
                if (b.total_points !== a.total_points)
                    return b.total_points - a.total_points;
                return new Date(b.created_at) - new Date(a.created_at);
            })
            .slice(0, 5),
    );

    let hasReferrals = $derived(totalReferrals > 0);

    function copyReferralLink() {
        const referralLink = `https://portal.genlayer.foundation/?ref=${participant?.referral_code || ""}`;
        navigator.clipboard.writeText(referralLink);
        showSuccess("Referral link copied!");
    }

    function shortAddress(addr) {
        if (!addr) return "";
        return addr.slice(0, 6) + "..." + addr.slice(-4);
    }

    function referrerEarned(referral) {
        const builder = Math.round((referral.builder_contribution_points || 0) * 0.1);
        const validator = Math.round((referral.validator_contribution_points || 0) * 0.1);
        return builder + validator;
    }

    function referralUserObj(referral) {
        return {
            name: referral.name,
            address: referral.address,
            profile_image_url: referral.profile_image_url,
            builder: referral.is_builder,
            validator: referral.is_validator,
        };
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
                    src="/assets/icons/hexagon-genlayer.svg"
                    alt=""
                    class="w-full h-full"
                />
                <img
                    src="/assets/icons/link-m.svg"
                    alt=""
                    class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 brightness-0 invert"
                    style="width: 16px; height: 16px;"
                />
            </div>
            <h2
                class="text-[20px] font-semibold text-black"
                style="letter-spacing: 0.4px;"
            >
                Referrals
            </h2>
        </div>
        <button
            onclick={() => push("/referral-program")}
            class="flex items-center gap-[4px] text-[12px] font-medium text-black tracking-[0.24px] leading-[16px] hover:opacity-70 transition-opacity"
        >
            Referral Program
            <img
                src="/assets/icons/arrow-right-up-line.svg"
                alt=""
                class="w-4 h-4"
            />
        </button>
    </div>

    <!-- Invite & Earn Banner (own profile only) -->
    {#if isOwnProfile}
        <div
            class="bg-[#1a1c1d] w-full rounded-[9px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] p-[20px] mb-4"
        >
            <div
                class="flex flex-col md:flex-row md:items-end md:justify-between gap-4"
            >
                <div class="flex flex-col gap-[4px]">
                    <p
                        class="font-['Switzer'] font-semibold text-[20px] text-white leading-[25px] tracking-[0.4px]"
                    >
                        Invite and earn, forever.
                    </p>
                    <p
                        class="font-['Switzer'] text-[14px] text-[#b0b0b0] leading-[21px] tracking-[0.28px]"
                    >
                        For each builder or validator you refer who submits at
                        least one contribution, you receive 10% of the points
                        they earn permanently.
                    </p>
                </div>
                <button
                    onclick={copyReferralLink}
                    class="bg-white flex gap-[8px] h-[40px] items-center justify-center px-[16px] rounded-[20px] hover:bg-[#f0f0f0] transition-colors shrink-0"
                >
                    <img
                        src="/assets/icons/link-m.svg"
                        alt=""
                        class="w-4 h-4"
                    />
                    <span
                        class="font-['Switzer'] font-medium text-[14px] text-[#1a1c1d] leading-[21px] tracking-[0.28px] whitespace-nowrap"
                    >
                        Copy Referral Link
                    </span>
                </button>
            </div>
        </div>
    {/if}

    {#if hasReferrals || loading}
        <!-- Stat cards: Total Referrals + Total Referral Points -->
        <div class="flex flex-col md:flex-row gap-4 w-full">
            <!-- Total Referrals Card -->
            <div
                class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative"
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
                            <img
                                src="/assets/icons/hexagon-genlayer.svg"
                                alt=""
                                class="w-full h-full"
                            />
                            <img
                                src="/assets/icons/link-m.svg"
                                alt=""
                                class="absolute w-5 h-5 brightness-0 invert"
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

            <!-- Total Referral Points Card -->
            <div
                class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative"
            >
                {#if loading}
                    <div class="flex h-full items-center animate-pulse">
                        <div
                            class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                        ></div>
                        <div class="flex flex-col gap-2">
                            <div class="h-7 w-20 bg-gray-200 rounded"></div>
                            <div class="h-3 w-32 bg-gray-100 rounded"></div>
                        </div>
                    </div>
                {:else}
                    <div class="flex h-full items-center">
                        <div
                            class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                        >
                            <img
                                src="/assets/icons/hexagon-genlayer.svg"
                                alt=""
                                class="w-full h-full"
                            />
                            <img
                                src="/assets/icons/group-white.svg"
                                alt=""
                                class="absolute"
                                style="width: 24px; height: 24px;"
                            />
                        </div>
                        <div
                            class="flex flex-col h-full items-start justify-center z-10"
                        >
                            <div class="flex items-center gap-2">
                                <p
                                    class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                                >
                                    {totalReferralPoints}
                                </p>
                                <div class="relative group">
                                    <svg
                                        class="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                        ></path>
                                    </svg>
                                    <div
                                        class="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 w-[240px] text-center"
                                    >
                                        10% of your referrals' eligible builder
                                        and validator contributions.
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-3 mt-1">
                                <span
                                    class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b]"
                                >
                                    Total Referral Points
                                </span>
                                {#if builderReferralPoints > 0 || validatorReferralPoints > 0}
                                    <div class="flex items-center gap-2">
                                        <div class="flex items-center gap-[3px]">
                                            <CategoryIcon
                                                category="builder"
                                                mode="hexagon"
                                                size={14}
                                            />
                                            <span
                                                class="text-[11px] font-medium text-[#999] leading-[14px]"
                                                >{builderReferralPoints}</span
                                            >
                                        </div>
                                        <div class="flex items-center gap-[3px]">
                                            <CategoryIcon
                                                category="validator"
                                                mode="hexagon"
                                                size={14}
                                            />
                                            <span
                                                class="text-[11px] font-medium text-[#999] leading-[14px]"
                                                >{validatorReferralPoints}</span
                                            >
                                        </div>
                                    </div>
                                {/if}
                            </div>
                        </div>
                    </div>
                {/if}
            </div>
        </div>

        <!-- Top Referrals List -->
        {#if hasReferrals}
            <div class="w-full mt-6">
                <div class="flex items-end justify-between mb-3">
                    <div>
                        <h3
                            class="font-semibold text-[16px] text-black"
                            style="letter-spacing: 0.32px;"
                        >
                            Top Referrals
                        </h3>
                        <p class="text-[13px] text-[#999] mt-1">
                            Your highest earning referrals
                        </p>
                    </div>
                    {#if isOwnProfile}
                        <button
                            onclick={() => push("/referrals")}
                            class="flex items-center gap-[4px] text-[14px] text-[#6b6b6b] hover:text-black transition-colors"
                            style="letter-spacing: 0.28px;"
                        >
                            View all referrals
                            <img
                                src="/assets/icons/arrow-right-line.svg"
                                alt=""
                                class="w-4 h-4"
                            />
                        </button>
                    {/if}
                </div>

                <div
                    class="bg-[#fcfcfc] border border-[#f0f0f0] rounded-[16px] p-[16px]"
                >
                    <div class="flex flex-col gap-[6px]">
                        {#each topReferrals as referral}
                            <button
                                onclick={() =>
                                    push(`/participant/${referral.address}`)}
                                class="flex items-center justify-between rounded-[10px] bg-white hover:bg-[#f8f8f8] px-3 py-[10px] transition-colors w-full"
                            >
                                <div class="flex items-center gap-[10px] min-w-0">
                                    <Avatar
                                        user={referralUserObj(referral)}
                                        size="sm"
                                        clickable={false}
                                    />
                                    <div class="flex flex-col items-start min-w-0">
                                        <span
                                            class="text-[14px] font-medium text-black truncate max-w-[200px]"
                                            style="letter-spacing: 0.2px;"
                                        >
                                            {referral.name || "Anonymous"}
                                        </span>
                                        <span
                                            class="text-[12px] text-[#999] leading-[14px]"
                                        >
                                            {shortAddress(referral.address)}
                                        </span>
                                    </div>
                                </div>
                                <div class="flex items-center gap-[6px]">
                                    {#if referral.is_builder}
                                        <CategoryIcon
                                            category="builder"
                                            mode="hexagon"
                                            size={20}
                                        />
                                    {/if}
                                    {#if referral.is_validator}
                                        <CategoryIcon
                                            category="validator"
                                            mode="hexagon"
                                            size={20}
                                        />
                                    {/if}
                                    <div
                                        class="flex items-center gap-[3px] text-[13px] font-medium text-[#7f52e1] ml-2"
                                    >
                                        <span>+{referrerEarned(referral)}</span>
                                        <span class="text-[#999] font-normal"
                                            >GP</span
                                        >
                                    </div>
                                </div>
                            </button>
                        {/each}
                    </div>
                </div>
            </div>
        {/if}
    {/if}
</div>
