<script lang="ts">
    import { showSuccess } from "../../lib/toastStore";
    import { leaderboardAPI } from "../../lib/api";
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let { participant = null, overallPoints = 0, referralData = null } = $props();

    let pointsToNextRank: number | null = $state(null);
    let nextRank: number | null = $state(null);
    let isTopRank = $state(false);
    let rankLabel: string = $state("");

    let bannerRef: HTMLElement;

    // Determine which entry type to use based on role eligibility
    // Priority: builder (completed) > validator-waitlist > validator > community (with referrals)
    let eligibleEntryType = $derived.by(() => {
        if (participant?.builder) return "builder";
        if (participant?.has_validator_waitlist && !participant?.validator) return "validator-waitlist";
        if (participant?.validator) return "validator";
        // Community only if they have at least one referral
        if (participant?.creator) {
            const hasReferrals = referralData?.total_referrals > 0 ||
                referralData?.referrals?.length > 0;
            if (hasReferrals) return "community";
        }
        return null;
    });

    let showBanner = $derived(eligibleEntryType !== null);

    const roleLabelMap: Record<string, string> = {
        builder: "Builder",
        validator: "Validator",
        "validator-waitlist": "Validator Waitlist",
        community: "Community",
    };

    // Fetch points-to-next-rank once leaderboard entries are available
    let rankComputed = $state(false);
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
        const referralLink = `https://points.genlayer.com/?ref=${participant?.referral_code || ""}`;
        navigator.clipboard.writeText(referralLink);
        showSuccess("Referral link copied!");
    }
</script>

{#if showBanner}
<div
    bind:this={bannerRef}
    class="relative w-full rounded-[16px] overflow-hidden p-[48px] md:p-[64px] flex flex-col items-center justify-center text-center mt-12 mb-8 border border-white/10 shadow-2xl"
>
    <!-- Complex Gradient Background -->
    <div
        class="absolute inset-0 z-0 bg-[#0f0f0f]"
        style="
        background: radial-gradient(circle at 15% 85%, rgba(132, 114, 255, 0.45) 0%, transparent 45%),
                    radial-gradient(circle at 85% 95%, rgba(245, 168, 152, 0.4) 0%, transparent 45%),
                    radial-gradient(circle at 50% 120%, rgba(105, 222, 187, 0.3) 0%, transparent 50%),
                    #0f0f0f;
    "
    ></div>

    <!-- Noise overlay for premium texture -->
    <div
        class="absolute inset-0 z-0 opacity-[0.03] mix-blend-overlay pointer-events-none"
        style="background-image: url('data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.65%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E');"
    ></div>

    <!-- Content Container -->
    <div class="relative z-10 flex flex-col items-center max-w-[800px] mx-auto">
        <!-- Top Badge -->
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

        <!-- Main Heading -->
        <h2
            class="text-[48px] md:text-[64px] font-semibold text-white leading-tight mb-6 tracking-[-1.5px]"
        >
            Keep building, {participant?.name || "Builder"}
        </h2>

        <!-- Subtitle/Copy -->
        <p
            class="text-[16px] md:text-[18px] text-[#b3b3b3] mb-10 w-full max-w-none leading-relaxed whitespace-nowrap overflow-hidden text-ellipsis"
        >
            Invite other builders to GenLayer and receive 10% of the points they
            make, forever.
        </p>

        <!-- Action Buttons -->
        <div class="flex flex-col sm:flex-row items-center gap-4">
            <!-- Referral Button -->
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

            <!-- Read Docs Button -->
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
{/if}
