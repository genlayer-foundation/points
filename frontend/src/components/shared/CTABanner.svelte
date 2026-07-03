<script lang="ts">
    import { push } from "svelte-spa-router";
    import { showError, showSuccess } from "../../lib/toastStore";
    import { leaderboardAPI } from "../../lib/api";
    import { userStore } from "../../lib/userStore.js";
    import { authState } from "../../lib/auth.js";
    import { buildReferralLink, referralCodeFromSources } from "../../lib/referrals.js";
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let { variant = "dark", participant = null, referralData = null, topRole = null } = $props();

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
        referralCodeFromSources(participant, storeValue.user),
    );

    // Rank computation state
    let pointsToNextRank: number | null = $state(null);
    let nextRank: number | null = $state(null);
    let isTopRank = $state(false);
    let rankLabel: string = $state("");
    let rankComputed = $state(false);
    let rankComputationKey: string | null = $state(null);

    function getRankableEntryType(roleKey: string | null, p: any) {
        if (!roleKey || !p) return null;
        if (roleKey === "builder") return p.builder ? "builder" : null;
        if (roleKey === "validator") {
            if (p.has_validator_waitlist && !p.validator) return "validator-waitlist";
            if (p.validator) return "validator";
        }
        if (roleKey === "community") return p.creator ? "community" : null;
        return null;
    }

    // Determine which entry type to use from the same top-role logic used by the profile header.
    let eligibleEntryType = $derived.by(() => {
        const p = participant;
        if (!p) return null;

        const badges = topRole?.badges || [];
        for (const badge of badges) {
            const entryType = getRankableEntryType(badge?.key || badge?.category, p);
            if (entryType) return entryType;
        }

        const categoryEntryType = getRankableEntryType(topRole?.category, p);
        if (categoryEntryType) return categoryEntryType;

        if (p.builder) return "builder";
        if (p.has_validator_waitlist && !p.validator) return "validator-waitlist";
        if (p.validator) return "validator";
        if (p.creator) return "community";
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
        const key = `${participant?.address || ""}:${eligibleEntryType || ""}`;
        const hasLeaderboardEntries = (participant?.leaderboard_entries?.length || 0) > 0;
        if (!participant?.address || !eligibleEntryType || key === rankComputationKey) {
            return;
        }
        if (eligibleEntryType !== "community" && !hasLeaderboardEntries) {
            return;
        }

        rankComputationKey = key;
        pointsToNextRank = null;
        nextRank = null;
        isTopRank = false;
        rankLabel = "";
        rankComputed = false;
        computePointsToNextRank(key);
    });

    async function computePointsToNextRank(key: string) {
        try {
            const entries = participant.leaderboard_entries || [];
            let userRank: number | null = null;
            let userPoints = 0;
            rankLabel = roleLabelMap[eligibleEntryType] || "Overall";

            if (eligibleEntryType === "community") {
                const userRankRes = await leaderboardAPI.getLeaderboard({
                    type: "community",
                    user_address: participant.address,
                    limit: 1,
                });
                userRank = userRankRes.data?.user_rank || null;
                userPoints = userRankRes.data?.user_total_points || 0;
            } else {
                const targetEntry = entries.find(
                    (e) => e.type === eligibleEntryType && e.rank && e.rank > 0,
                );

                if (!targetEntry) {
                    return;
                }

                userRank = targetEntry.rank;
                userPoints = targetEntry.total_points || 0;
            }

            if (!userRank) {
                return;
            }

            if (userRank <= 1) {
                isTopRank = true;
                return;
            }

            // Fetch all users above the current user (capped at 100) so we can
            // skip anyone tied with the user and find the closest rank with
            // strictly more points.
            const fetchLimit = Math.min(userRank - 1, 100);
            const res = await leaderboardAPI.getLeaderboard({
                type: eligibleEntryType,
                offset: Math.max(0, userRank - 1 - fetchLimit),
                limit: fetchLimit,
            });
            const results = Array.isArray(res.data) ? res.data : res.data?.results || [];
            // Walk from the rank closest to the user upward until we find a
            // user with strictly more points.
            let targetUser = null;
            for (let i = results.length - 1; i >= 0; i--) {
                const r = results[i];
                if ((r.total_points || 0) > userPoints) {
                    targetUser = r;
                    break;
                }
            }
            if (targetUser) {
                pointsToNextRank = Math.max(
                    0,
                    (targetUser.total_points || 0) - userPoints,
                );
                nextRank = targetUser.rank;
            }
        } catch (err) {
            // Silently fail - banner will show without rank info
        } finally {
            if (rankComputationKey === key) {
                rankComputed = true;
            }
        }
    }

    function copyReferralLink() {
        const referralLink = buildReferralLink(referralCode);
        if (!referralLink) {
            showError("Referral code is still loading. Try again in a moment.");
            return;
        }

        navigator.clipboard.writeText(referralLink);
        showSuccess("Referral link copied!");
    }

    // Show rank pill only when logged in and we have rank data (or are computing it)
    let showRankPill = $derived(isLoggedIn && participant && eligibleEntryType !== null);
</script>

{#if variant === "dark"}
    <!-- Dark variant (Profile page) -->
    <div
        class="cta-banner-dark relative w-full overflow-hidden px-[20px] py-[120px] md:py-[160px] flex flex-col items-center justify-center text-center bg-[#131214]"
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
        <div class="cta-content relative z-10 flex flex-col items-center max-w-[800px] mx-auto">
            <!-- Rank Pill -->
            {#if showRankPill}
                <div
                    class="cta-rank-pill inline-flex items-center gap-[6px] bg-[#1a1a1a]/80 backdrop-blur-md border border-white/10 rounded-full px-4 py-2 mb-8 shadow-lg"
                >
                    {#if !rankComputed}
                        <div class="animate-pulse flex items-center gap-2">
                            <div class="w-5 h-5 rounded-full bg-white/20"></div>
                            <div class="h-3 w-40 bg-white/20 rounded"></div>
                        </div>
                    {:else}
                        <CategoryIcon category="genlayer" mode="hexagon" size={20} />
                        <span
                            class="cta-rank-text text-[#dcdcdc] text-[13px] font-medium tracking-[0.2px]"
                        >
                            {#if isTopRank}
                                You lead the {rankLabel} ranks!
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
                class="cta-title text-[48px] md:text-[64px] font-semibold text-white leading-tight mb-6 tracking-[-1.5px]"
            >
                {#if isLoggedIn}
                    Keep building, {displayName}
                {:else}
                    Start contributing today
                {/if}
            </h2>

            <!-- Subtitle -->
            <p
                class="cta-subtitle text-[16px] md:text-[18px] text-[#b3b3b3] mb-10 w-full max-w-none leading-relaxed whitespace-nowrap overflow-hidden text-ellipsis"
            >
                {#if isLoggedIn}
                    Invite other builders to GenLayer and receive 10% of the points they
                    make, forever.
                {:else}
                    Join professional validators and builders in creating the trust infrastructure for the AI age.
                {/if}
            </p>

            <!-- Action Buttons -->
            <div class="cta-actions flex flex-col sm:flex-row items-center gap-4">
                {#if isLoggedIn}
                    <button
                        onclick={copyReferralLink}
                        disabled={!referralCode}
                        class="cta-action-button flex items-center gap-[8px] bg-[#935cf1] hover:bg-[#824ce0] text-white px-6 py-[14px] rounded-full text-[15px] font-medium transition-all shadow-[0_0_20px_rgba(147,92,241,0.3)] hover:shadow-[0_0_25px_rgba(147,92,241,0.5)] transform hover:-translate-y-[1px]"
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
                        class="cta-action-button flex items-center gap-[8px] bg-[#935cf1] hover:bg-[#824ce0] text-white px-6 py-[14px] rounded-full text-[15px] font-medium transition-all shadow-[0_0_20px_rgba(147,92,241,0.3)] hover:shadow-[0_0_25px_rgba(147,92,241,0.5)] transform hover:-translate-y-[1px]"
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
                    class="cta-action-button flex items-center gap-[8px] bg-transparent border border-white/20 hover:border-white/40 hover:bg-white/5 text-white px-6 py-[14px] rounded-full text-[15px] font-medium transition-all"
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
                                    You lead the {rankLabel} ranks!
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
                            disabled={!referralCode}
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

<style>
    @media (max-width: 767px) {
        .cta-banner-dark {
            border-radius: 10px;
            padding: 64px 20px 72px;
        }

        .cta-content {
            width: 100%;
            max-width: 100%;
            min-width: 0;
        }

        .cta-rank-pill {
            max-width: 100%;
            justify-content: center;
            border-radius: 999px;
            padding: 8px 12px;
        }

        .cta-rank-text {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            letter-spacing: 0 !important;
        }

        .cta-title {
            max-width: 100%;
            font-size: clamp(30px, 9vw, 38px);
            line-height: 1.08;
            letter-spacing: 0 !important;
            overflow-wrap: anywhere;
            margin-bottom: 16px;
        }

        .cta-subtitle {
            max-width: 100%;
            font-size: 15px;
            line-height: 22px;
            margin-bottom: 28px;
            white-space: normal;
            overflow: visible;
            text-overflow: clip;
            text-wrap: pretty;
        }

        .cta-actions {
            width: 100%;
            align-items: stretch;
        }

        .cta-action-button {
            width: 100%;
            min-height: 46px;
            justify-content: center;
            transform: none;
        }
    }
</style>
