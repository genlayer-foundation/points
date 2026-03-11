<script lang="ts">
    import { push } from "svelte-spa-router";
    import { showSuccess } from "../../lib/toastStore";
    import { leaderboardAPI } from "../../lib/api";
    import { userStore } from "../../lib/userStore.js";
    import { authState } from "../../lib/auth.js";
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let { variant = "dark", participant = null, referralData = null } = $props();

    // For light variant without participant, derive auth state from stores
    let storeValue = $state({ user: null });
    let authValue = $state({ isAuthenticated: false });

    userStore.subscribe((value) => {
        storeValue = value;
    });

    authState.subscribe((value) => {
        authValue = value;
    });

    // Determine if user is logged in (either via participant prop or store)
    let isLoggedIn = $derived(
        !!participant || (authValue.isAuthenticated && !!storeValue.user),
    );
    let displayName = $derived(
        participant?.name ||
            storeValue.user?.name ||
            storeValue.user?.address?.slice(0, 8) ||
            "Builder",
    );
    let referralCode = $derived(
        participant?.referral_code || storeValue.user?.referral_code || "",
    );

    // Rank computation state
    let pointsToNextRank: number | null = $state(null);
    let nextRank: number | null = $state(null);
    let isTopRank = $state(false);
    let rankLabel: string = $state("");
    let rankComputed = $state(false);

    // Determine which entry type to use based on role eligibility
    // Priority: builder (completed) > validator-waitlist > validator > community (with referrals)
    let eligibleEntryType = $derived.by(() => {
        const p = participant;
        if (!p) return null;
        if (p.builder) return "builder";
        if (p.has_validator_waitlist && !p.validator) return "validator-waitlist";
        if (p.validator) return "validator";
        // Community only if they have at least one referral
        if (p.creator) {
            const hasReferrals =
                referralData?.total_referrals > 0 ||
                referralData?.referrals?.length > 0;
            if (hasReferrals) return "community";
        }
        return null;
    });

    const roleLabelMap: Record<string, string> = {
        builder: "Builder",
        validator: "Validator",
        "validator-waitlist": "Validator Waitlist",
        community: "Community",
    };

    // Fetch points-to-next-rank once leaderboard entries are available
    $effect(() => {
        if (
            participant?.address &&
            participant?.leaderboard_entries?.length > 0 &&
            eligibleEntryType &&
            !rankComputed
        ) {
            computePointsToNextRank();
        }
    });

    async function computePointsToNextRank() {
        if (rankComputed) return;
        try {
            const entries = participant.leaderboard_entries || [];
            const targetEntry = entries.find(
                (e) => e.type === eligibleEntryType && e.rank && e.rank > 0,
            );

            if (!targetEntry) {
                rankComputed = true;
                return;
            }

            const userRank = targetEntry.rank;
            rankLabel = roleLabelMap[eligibleEntryType] || "Overall";

            if (userRank <= 1) {
                isTopRank = true;
                rankComputed = true;
                return;
            }

            // Fetch the user one rank above in the same leaderboard
            const res = await leaderboardAPI.getLeaderboard({
                type: eligibleEntryType,
                offset: userRank - 2,
                limit: 1,
            });
            const results = res.data?.results || res.data || [];
            if (results.length > 0) {
                const userAbove = results[0];
                const abovePoints = userAbove.total_points || 0;
                const userPoints = targetEntry.total_points || 0;
                pointsToNextRank = Math.max(0, abovePoints - userPoints);
                nextRank = userRank - 1;
            }
        } catch (err) {
            // Silently fail - banner will show without rank info
        } finally {
            rankComputed = true;
        }
    }

    function copyReferralLink() {
        const referralLink = `https://points.genlayer.com/?ref=${referralCode}`;
        navigator.clipboard.writeText(referralLink);
        showSuccess("Referral link copied!");
    }

    // Show rank pill only when logged in and we have rank data (or are computing it)
    let showRankPill = $derived(isLoggedIn && participant && eligibleEntryType !== null);
</script>

{#if variant === "dark"}
    <!-- Dark variant (Profile page) -->
    <div
        class="relative w-full overflow-hidden px-[20px] py-[120px] md:py-[160px] flex flex-col items-center justify-center text-center bg-[#131214]"
    >
        <!-- Iridescent gradient background -->
        <div
            class="absolute inset-0 pointer-events-none"
            style="
                -webkit-mask-image: radial-gradient(ellipse 130% 90% at 50% 100%, black 20%, transparent 70%);
                mask-image: radial-gradient(ellipse 130% 90% at 50% 100%, black 20%, transparent 70%);
            "
        >
            <img
                src="/assets/illustrations/cta-gradient.webp"
                alt=""
                class="absolute inset-0 w-full h-full object-cover"
            />
        </div>

        <!-- Content Container -->
        <div class="relative z-10 flex flex-col items-center max-w-[800px] mx-auto">
            <!-- Rank Pill -->
            {#if showRankPill}
                <div
                    class="inline-flex items-center gap-[6px] bg-[#1a1a1a]/80 backdrop-blur-md border border-white/10 rounded-full px-4 py-2 mb-8 shadow-lg"
                >
                    {#if !rankComputed}
                        <div class="animate-pulse flex items-center gap-2">
                            <div class="w-5 h-5 rounded-full bg-white/20"></div>
                            <div class="h-3 w-40 bg-white/20 rounded"></div>
                        </div>
                    {:else}
                        <CategoryIcon category="genlayer" mode="hexagon" size={20} />
                        <span
                            class="text-[#dcdcdc] text-[13px] font-medium tracking-[0.2px]"
                        >
                            {#if isTopRank}
                                You're #1!
                            {:else if pointsToNextRank !== null}
                                {pointsToNextRank} Points to {rankLabel} Rank #{nextRank}
                            {:else}
                                Keep earning points to climb the ranks
                            {/if}
                        </span>
                    {/if}
                </div>
            {/if}

            <!-- Main Heading -->
            <h2
                class="text-[48px] md:text-[64px] font-semibold text-white leading-tight mb-6 tracking-[-1.5px]"
            >
                {#if isLoggedIn}
                    Keep building, {displayName}
                {:else}
                    Start contributing today
                {/if}
            </h2>

            <!-- Subtitle -->
            <p
                class="text-[16px] md:text-[18px] text-[#b3b3b3] mb-10 w-full max-w-none leading-relaxed whitespace-nowrap overflow-hidden text-ellipsis"
            >
                {#if isLoggedIn}
                    Invite other builders to GenLayer and receive 10% of the points they
                    make, forever.
                {:else}
                    Join professional validators and builders in creating the trust infrastructure for the AI age.
                {/if}
            </p>

            <!-- Action Buttons -->
            <div class="flex flex-col sm:flex-row items-center gap-4">
                {#if isLoggedIn}
                    <button
                        onclick={copyReferralLink}
                        class="flex items-center gap-[8px] bg-[#935cf1] hover:bg-[#824ce0] text-white px-6 py-[14px] rounded-full text-[15px] font-medium transition-all shadow-[0_0_20px_rgba(147,92,241,0.3)] hover:shadow-[0_0_25px_rgba(147,92,241,0.5)] transform hover:-translate-y-[1px]"
                    >
                        <svg
                            width="16"
                            height="16"
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
                        Referral link
                    </button>
                {:else}
                    <button
                        onclick={() => push('/builders/welcome')}
                        class="flex items-center gap-[8px] bg-[#935cf1] hover:bg-[#824ce0] text-white px-6 py-[14px] rounded-full text-[15px] font-medium transition-all shadow-[0_0_20px_rgba(147,92,241,0.3)] hover:shadow-[0_0_25px_rgba(147,92,241,0.5)] transform hover:-translate-y-[1px]"
                    >
                        Get started
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                        >
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                            <polyline points="12 5 19 12 12 19"></polyline>
                        </svg>
                    </button>
                {/if}

                <button
                    onclick={() =>
                        window.open("https://docs.genlayer.com", "_blank")}
                    class="flex items-center gap-[8px] bg-transparent border border-white/20 hover:border-white/40 hover:bg-white/5 text-white px-6 py-[14px] rounded-full text-[15px] font-medium transition-all"
                >
                    Read the Docs
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                    >
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                    </svg>
                </button>
            </div>
        </div>
    </div>
{:else}
    <!-- Light variant (Landing page) -->
    <div class="relative overflow-hidden rounded-[8px]">
        <div class="px-[20px] pt-[160px] pb-[80px] flex items-center justify-center">
            <div class="flex flex-col gap-[24px] items-center text-center">
                <!-- Rank pill -->
                {#if showRankPill}
                    <div
                        class="inline-flex items-center gap-[6px] rounded-full px-4 py-2"
                        style="background: rgba(255,255,255,0.1);"
                    >
                        {#if !rankComputed}
                            <div class="animate-pulse flex items-center gap-2">
                                <div class="w-5 h-5 rounded-full bg-black/10"></div>
                                <div class="h-3 w-40 bg-black/10 rounded"></div>
                            </div>
                        {:else}
                            <div class="relative w-[24px] h-[24px]">
                                <img src="/assets/illustrations/gl-polygon.svg" alt="" class="absolute inset-[1.45%_6.7%] w-[86.6%] h-[97.1%]" />
                                <img src="/assets/illustrations/gl-symbol-white.svg" alt="" class="absolute inset-[22.66%_24.69%_29.53%_24.69%] w-[50.62%] h-[47.81%]" />
                            </div>
                            <span
                                class="text-[12px] font-medium text-black leading-[15px]"
                                style="letter-spacing: 0.24px;"
                            >
                                {#if isTopRank}
                                    You're #1!
                                {:else if pointsToNextRank !== null}
                                    {pointsToNextRank} Points to {rankLabel} Rank #{nextRank}
                                {:else}
                                    Keep earning points to climb the ranks
                                {/if}
                            </span>
                        {/if}
                    </div>
                {/if}

                <h2
                    class="text-[40px] md:text-[64px] font-medium font-display leading-[64px] text-black"
                    style="letter-spacing: -1.28px;"
                >
                    {#if isLoggedIn}
                        Keep building, {displayName}
                    {:else}
                        Start contributing today
                    {/if}
                </h2>
                <p
                    class="text-[17px] text-black leading-[28px]"
                    style="letter-spacing: 0.34px;"
                >
                    {#if isLoggedIn}
                        Invite other builders to GenLayer and receive 10% of the
                        points they make, forever.
                    {:else}
                        Join professional validators and builders in creating the
                        trust infrastructure for the AI age.
                    {/if}
                </p>

                <div class="flex gap-[8px] items-start">
                    {#if isLoggedIn}
                        <button
                            onclick={copyReferralLink}
                            class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] transition-colors hover:opacity-90"
                            style="background-color: #9e4bf6;"
                        >
                            <img
                                src="/assets/icons/link-m.svg"
                                alt=""
                                class="w-4 h-4"
                            />
                            <span
                                class="text-[14px] font-medium text-white leading-[21px]"
                                style="letter-spacing: 0.28px;"
                            >
                                Referral link
                            </span>
                        </button>
                    {:else}
                        <button
                            onclick={() => push("/builders/welcome")}
                            class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] transition-colors hover:opacity-90"
                            style="background-color: #9e4bf6;"
                        >
                            <span
                                class="text-[14px] font-medium text-white leading-[21px]"
                                style="letter-spacing: 0.28px;"
                            >
                                Get started
                            </span>
                            <img
                                src="/assets/icons/arrow-right-line-white.svg"
                                alt=""
                                class="w-4 h-4"
                            />
                        </button>
                    {/if}
                    <a
                        href="https://docs.genlayer.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="flex gap-[8px] items-center justify-center h-[40px] px-[16px] rounded-[20px] border border-black transition-colors hover:bg-black/5"
                    >
                        <span
                            class="text-[14px] font-medium text-black leading-[21px]"
                            style="letter-spacing: 0.28px;"
                        >
                            Read the Docs
                        </span>
                        <img
                            src="/assets/icons/arrow-right-line.svg"
                            alt=""
                            class="w-4 h-4"
                        />
                    </a>
                </div>
            </div>
        </div>
    </div>
{/if}
