<script lang="ts">
    import { push } from "svelte-spa-router";
    import { leaderboardAPI } from "../../lib/api";
    import Avatar from "../Avatar.svelte";
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let {
        participant = null,
        isOwnProfile = false,
        builderStats = null,
        validatorStats = null,
        overallPoints = 0,
        referralPoints = { builder_points: 0, validator_points: 0 },
    } = $props();

    let communityRank: number | null = $state(null);

    // Role checks
    let isBuilder = $derived(!!participant?.builder);
    let isValidator = $derived(
        !!participant?.validator || !!participant?.has_validator_waitlist,
    );
    let isCreator = $derived(!!participant?.creator);
    let isValidatorWaitlist = $derived(
        participant?.has_validator_waitlist && !participant?.validator,
    );

    // Only show tabs for roles the user actually has
    let availableTabs = $derived.by(() => {
        const tabs = [];
        if (isBuilder) tabs.push("Builders");
        if (isValidator) tabs.push("Validators");
        if (isCreator) tabs.push("Community");
        return tabs;
    });

    let hasAnyRankableRole = $derived(isBuilder || isValidator || isCreator);

    let activeTab: string | null = $state(null);

    // Set initial tab when available tabs change
    $effect(() => {
        const tabs = availableTabs;
        if (tabs.length > 0 && (!activeTab || !tabs.includes(activeTab))) {
            activeTab = tabs[0];
        }
    });

    let loading = $state(true);
    let error: string | null = $state(null);
    let activeList: any[] = $state([]);

    async function loadTabLeaderboard(tab: string) {
        loading = true;
        error = null;
        activeList = [];

        try {
            if (tab === "Community") {
                await loadCommunityTab();
                return;
            }

            let apiType;
            if (tab === "Builders") apiType = "builder";
            else if (tab === "Validators") {
                apiType = isValidatorWaitlist
                    ? "validator-waitlist"
                    : "validator";
            } else apiType = "builder";

            const topRes = await leaderboardAPI.getLeaderboard({
                type: apiType,
                limit: 4,
            });
            const top4 = topRes.data?.results || topRes.data || [];

            const userInTop4 = top4.some(
                (u: any) =>
                    (
                        u.user_address ||
                        u.user_details?.address ||
                        u.address
                    )?.toLowerCase() === participant.address?.toLowerCase(),
            );

            if (userInTop4 || !participant) {
                activeList = top4.map((u: any, i: number) => ({
                    ...u,
                    _displayRank: i + 1,
                }));
            } else {
                let userRank = null;
                try {
                    const userEntryRes = await leaderboardAPI.getLeaderboard({
                        type: apiType,
                        user_address: participant.address,
                    });
                    const userEntries =
                        userEntryRes.data?.results || userEntryRes.data || [];
                    if (userEntries.length > 0) {
                        userRank = userEntries[0].rank;
                    }
                } catch {}

                if (!userRank) {
                    activeList = top4.map((u: any, i: number) => ({
                        ...u,
                        _displayRank: i + 1,
                    }));
                } else {
                    const targetIndex = userRank - 1;
                    const offset = Math.max(0, targetIndex - 1);
                    const limit = 3;

                    const contextRes = await leaderboardAPI.getLeaderboard({
                        type: apiType,
                        offset: offset,
                        limit: limit,
                    });
                    const contextUsers =
                        contextRes.data?.results || contextRes.data || [];

                    let constructedList = [];
                    if (top4.length > 0) {
                        constructedList.push({ ...top4[0], _displayRank: 1 });
                    }
                    constructedList.push({ isEllipsis: true });

                    contextUsers.forEach((u: any, i: number) => {
                        constructedList.push({
                            ...u,
                            _displayRank: offset + i + 1,
                        });
                    });

                    activeList = constructedList;
                }
            }
        } catch (err) {
            console.error(err);
            error = "Failed to load leaderboard context";
        } finally {
            loading = false;
        }
    }

    async function loadCommunityTab() {
        try {
            const topRes = await (leaderboardAPI as any).getCommunity({
                limit: 4,
                user_address: participant?.address,
            });

            const results = topRes.data?.results || [];
            const userRankFromApi = topRes.data?.user_rank;

            if (userRankFromApi) {
                communityRank = userRankFromApi;
            }

            const top4 = results.map((u: any) => ({
                user_address: u.address,
                user_name: u.name,
                name: u.name,
                address: u.address,
                profile_image_url: u.profile_image_url,
                total_points: u.total_points || u.total_referral_points || 0,
                points: u.total_points || u.total_referral_points || 0,
                _displayRank: u.rank,
            }));

            const userInTop4 = top4.some(
                (u: any) =>
                    u.address?.toLowerCase() ===
                    participant?.address?.toLowerCase(),
            );

            if (userInTop4 || !participant || !userRankFromApi) {
                activeList = top4;
            } else {
                const offset = Math.max(0, userRankFromApi - 2);
                const contextRes = await (leaderboardAPI as any).getCommunity({
                    limit: 3,
                    offset: offset,
                });
                const contextUsers = (contextRes.data?.results || []).map(
                    (u: any) => ({
                        user_address: u.address,
                        user_name: u.name,
                        name: u.name,
                        address: u.address,
                        profile_image_url: u.profile_image_url,
                        total_points:
                            u.total_points || u.total_referral_points || 0,
                        points: u.total_points || u.total_referral_points || 0,
                        _displayRank: u.rank,
                    }),
                );

                let constructedList = [];
                if (top4.length > 0) {
                    constructedList.push(top4[0]);
                }
                constructedList.push({ isEllipsis: true });
                constructedList.push(...contextUsers);
                activeList = constructedList;
            }
        } catch (err) {
            console.error(err);
            error = "Failed to load community leaderboard";
        } finally {
            loading = false;
        }
    }

    let initializedForAddress = $state(null);

    $effect(() => {
        const addr = participant?.address;
        if (!addr || addr === initializedForAddress || !hasAnyRankableRole)
            return;
        initializedForAddress = addr;

        if (activeTab) {
            loadTabLeaderboard(activeTab);
        }

        // Fetch community rank only if user is a creator
        if (isCreator) {
            (leaderboardAPI as any)
                .getCommunity({
                    limit: 1,
                    user_address: addr,
                })
                .then((res: any) => {
                    if (res.data?.user_rank) {
                        communityRank = res.data.user_rank;
                    }
                })
                .catch(() => {});
        }
    });

    function switchTab(t: string) {
        if (t !== activeTab) {
            activeTab = t;
            loadTabLeaderboard(t);
        }
    }

    function getUserObj(entry: any) {
        const ud = entry.user_details || {};
        return {
            name: entry.user_name || ud.name || entry.name,
            address: entry.user_address || ud.address || entry.address,
            profile_image_url: entry.profile_image_url || ud.profile_image_url,
            builder: entry.builder ?? false,
            validator: entry.validator ?? false,
            steward: entry.steward ?? false,
            has_validator_waitlist: entry.has_validator_waitlist ?? false,
            has_builder_welcome: entry.has_builder_welcome ?? false,
        };
    }

    function getDisplayName(entry: any) {
        const name = entry.user_name || entry.user_details?.name || entry.name;
        const addr =
            entry.user_address || entry.user_details?.address || entry.address;
        if (name) return name.length > 14 ? name.slice(0, 14) + "..." : name;
        if (addr) return addr.slice(0, 6) + "..." + addr.slice(-4);
        return "Unknown";
    }

    function formatPoints(pts: any) {
        if (pts == null) return "-";
        if (pts >= 1000) return (pts / 1000).toFixed(1) + "K";
        return pts.toString();
    }

    function isCurrentUser(row: any) {
        const addr =
            row.user_address || row.user_details?.address || row.address;
        return (
            addr &&
            participant?.address &&
            addr.toLowerCase() === participant.address.toLowerCase()
        );
    }

    let userCommunityPoints = $derived(
        (referralPoints?.builder_points || 0) +
            (referralPoints?.validator_points || 0),
    );

    let rightPanelStats = $derived({
        builder: participant?.leaderboard_entries?.find(
            (e: any) => e.type === "builder",
        ),
        validator: participant?.leaderboard_entries?.find((e: any) =>
            isValidatorWaitlist
                ? e.type === "validator-waitlist"
                : e.type === "validator",
        ),
    });

    function scrollToJourneys() {
        const el = document.querySelector(".journey-actions-section");
        if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }
</script>

{#if hasAnyRankableRole}
    <div class="mt-8">
        <div class="flex items-center justify-between mb-4">
            <h2
                class="text-[20px] font-semibold text-black"
                style="letter-spacing: 0.4px;"
            >
                Ranking
            </h2>
            <button
                onclick={() => push("/leaderboard")}
                class="flex items-center gap-[4px] text-[14px] text-[#6b6b6b] hover:text-black transition-colors"
                style="letter-spacing: 0.28px;"
            >
                View all
                <img
                    src="/assets/icons/arrow-right-line.svg"
                    alt=""
                    class="w-4 h-4"
                />
            </button>
        </div>

        <!-- Main Content Layout -->
        <div class="flex flex-col lg:flex-row gap-6">
            <!-- Left: Leaderboard (50%) -->
            <div class="w-full lg:w-1/2 flex flex-col pt-2 min-h-[300px]">
                <!-- Tabs Header -->
                <div class="flex gap-6 border-b border-[#f0f0f0] mb-4">
                    {#each availableTabs as tab}
                        <button
                            class="pb-2 px-1 text-[14px] font-medium transition-colors relative {activeTab ===
                            tab
                                ? 'text-black'
                                : 'text-[#6b6b6b] hover:text-black'}"
                            onclick={() => switchTab(tab)}
                        >
                            {tab}
                            {#if activeTab === tab}
                                <div
                                    class="absolute bottom-0 left-0 right-0 h-[2px] bg-black rounded-t-full"
                                ></div>
                            {/if}
                        </button>
                    {/each}
                </div>

                <!-- Tab Content (Leaderboard List) -->
                <div
                    class="bg-[#fcfcfc] border border-[#f0f0f0] rounded-[16px] overflow-hidden p-[16px]"
                >
                    {#if loading}
                        <div class="animate-pulse flex flex-col gap-[6px]">
                            {#each [1, 2, 3, 4] as _}
                                <div
                                    class="flex items-center gap-[10px] rounded-[10px] bg-white px-3 py-[10px]"
                                >
                                    <div
                                        class="w-5 h-4 bg-gray-200 rounded"
                                    ></div>
                                    <div
                                        class="w-8 h-8 rounded-full bg-gray-200"
                                    ></div>
                                    <div
                                        class="flex-1 h-4 bg-gray-200 rounded"
                                    ></div>
                                </div>
                            {/each}
                        </div>
                    {:else if error}
                        <div class="text-sm text-gray-500 py-4 text-center">
                            {error}
                        </div>
                    {:else if activeTab === "Community" && userCommunityPoints === 0}
                        <div
                            class="flex flex-col items-center justify-center py-8 px-4 text-center"
                        >
                            <CategoryIcon
                                category="community"
                                mode="hexagon"
                                size={40}
                            />
                            <p class="text-[14px] font-medium text-black mt-3">
                                No ranking yet
                            </p>
                            <p class="text-[13px] text-[#6b6b6b] mt-1">
                                Refer at least one user to appear in the
                                community ranking
                            </p>
                        </div>
                    {:else if activeList.length === 0}
                        <div class="text-sm text-gray-500 py-4 text-center">
                            No ranked users found.
                        </div>
                    {:else}
                        <div class="flex flex-col gap-[6px]">
                            {#each activeList as row}
                                {#if row.isEllipsis}
                                    <div
                                        class="flex items-center justify-center py-1"
                                    >
                                        <div
                                            class="flex flex-col items-center gap-[3px]"
                                        >
                                            <div
                                                class="w-[4px] h-[4px] rounded-full bg-[#c0c0c0]"
                                            ></div>
                                            <div
                                                class="w-[4px] h-[4px] rounded-full bg-[#c0c0c0]"
                                            ></div>
                                            <div
                                                class="w-[4px] h-[4px] rounded-full bg-[#c0c0c0]"
                                            ></div>
                                        </div>
                                    </div>
                                {:else}
                                    <button
                                        onclick={() => {
                                            const addr =
                                                row.user_address ||
                                                row.user_details?.address ||
                                                row.address;
                                            if (addr)
                                                push(`/participant/${addr}`);
                                        }}
                                        class="flex items-center justify-between rounded-[10px] px-3 py-[10px] transition-colors
                                        {isCurrentUser(row)
                                            ? 'bg-[#f0f0f0]'
                                            : 'bg-white hover:bg-[#f8f8f8]'}"
                                    >
                                        <div
                                            class="flex items-center gap-[10px]"
                                        >
                                            <span
                                                class="text-[13px] font-medium text-[#999] min-w-[20px] text-center"
                                            >
                                                {row._displayRank}
                                            </span>
                                            <Avatar
                                                user={getUserObj(row)}
                                                size="sm"
                                                clickable={false}
                                            />
                                            <span
                                                class="text-[14px] font-medium text-black"
                                                style="letter-spacing: 0.2px;"
                                            >
                                                {getDisplayName(row)}
                                            </span>
                                        </div>
                                        <div
                                            class="flex items-center gap-[3px] text-[13px] font-medium
                                            {activeTab === 'Builders'
                                                ? 'text-[#ee8521]'
                                                : activeTab === 'Validators'
                                                  ? 'text-[#387de8]'
                                                  : 'text-[#7f52e1]'}"
                                        >
                                            <svg
                                                class="w-3 h-3"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="currentColor"
                                                stroke-width="2.5"
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                            >
                                                <path d="M5 15l7-7 7 7" />
                                            </svg>
                                            <span>
                                                {formatPoints(
                                                    row.points ||
                                                        row.total_points ||
                                                        0,
                                                )}
                                            </span>
                                        </div>
                                    </button>
                                {/if}
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>

            <!-- Right: Context Stats (50%) -->
            <div class="w-full lg:w-1/2 flex flex-col gap-3 pt-[36px]">
                <!-- Builder Stat -->
                {#if isBuilder}
                    <div
                        class="flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm"
                    >
                        {#if !participant?.leaderboard_entries}
                            <div class="flex items-center gap-4 animate-pulse">
                                <div
                                    class="w-[48px] h-[48px] rounded-full bg-gray-200"
                                ></div>
                                <div class="flex flex-col gap-2">
                                    <div
                                        class="h-6 w-14 bg-gray-200 rounded"
                                    ></div>
                                    <div
                                        class="h-3 w-24 bg-gray-100 rounded"
                                    ></div>
                                </div>
                            </div>
                            <div
                                class="h-3 w-16 bg-gray-100 rounded self-start mt-1 animate-pulse"
                            ></div>
                        {:else}
                            <div class="flex items-center gap-4">
                                <CategoryIcon
                                    category="builder"
                                    mode="hexagon"
                                    size={48}
                                />
                                <div class="flex flex-col">
                                    <span
                                        class="text-[24px] font-semibold text-black leading-tight"
                                        >{builderStats?.totalPoints || 0}</span
                                    >
                                    <span class="text-[12px] text-[#6b6b6b]"
                                        >Builder Points</span
                                    >
                                </div>
                            </div>
                            <div
                                class="text-[12px] font-medium text-[#6b6b6b] self-start mt-1"
                            >
                                Rank #{rightPanelStats.builder?.rank || "-"}
                            </div>
                        {/if}
                    </div>
                {:else if isOwnProfile}
                    <button
                        onclick={scrollToJourneys}
                        class="flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm hover:bg-[#fafafa] transition-colors text-left w-full"
                    >
                        <div class="flex items-center gap-4">
                            <CategoryIcon
                                category="builder"
                                mode="hexagon"
                                size={48}
                            />
                            <div class="flex flex-col">
                                <span class="text-[14px] font-medium text-black"
                                    >Start as a Builder</span
                                >
                                <span class="text-[12px] text-[#6b6b6b]"
                                    >Complete the builder journey to get ranked</span
                                >
                            </div>
                        </div>
                        <img
                            src="/assets/icons/arrow-right-line.svg"
                            alt=""
                            class="w-4 h-4 opacity-40"
                        />
                    </button>
                {/if}

                <!-- Validator Stat -->
                {#if isValidator}
                    <div
                        class="flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm"
                    >
                        {#if !participant?.leaderboard_entries}
                            <div class="flex items-center gap-4 animate-pulse">
                                <div
                                    class="w-[48px] h-[48px] rounded-full bg-gray-200"
                                ></div>
                                <div class="flex flex-col gap-2">
                                    <div
                                        class="h-6 w-14 bg-gray-200 rounded"
                                    ></div>
                                    <div
                                        class="h-3 w-24 bg-gray-100 rounded"
                                    ></div>
                                </div>
                            </div>
                            <div
                                class="h-3 w-16 bg-gray-100 rounded self-start mt-1 animate-pulse"
                            ></div>
                        {:else}
                            <div class="flex items-center gap-4">
                                <CategoryIcon
                                    category="validator"
                                    mode="hexagon"
                                    size={48}
                                />
                                <div class="flex flex-col">
                                    <span
                                        class="text-[24px] font-semibold text-black leading-tight"
                                        >{validatorStats?.totalPoints ||
                                            0}</span
                                    >
                                    <span class="text-[12px] text-[#6b6b6b]"
                                        >{isValidatorWaitlist
                                            ? "Waitlist Points"
                                            : "Validator Points"}</span
                                    >
                                </div>
                            </div>
                            <div
                                class="text-[12px] font-medium text-[#6b6b6b] self-start mt-1"
                            >
                                {isValidatorWaitlist ? "Waitlist" : ""} Rank #{rightPanelStats
                                    .validator?.rank || "-"}
                            </div>
                        {/if}
                    </div>
                {:else if isOwnProfile}
                    <button
                        onclick={scrollToJourneys}
                        class="flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm hover:bg-[#fafafa] transition-colors text-left w-full"
                    >
                        <div class="flex items-center gap-4">
                            <CategoryIcon
                                category="validator"
                                mode="hexagon"
                                size={48}
                            />
                            <div class="flex flex-col">
                                <span class="text-[14px] font-medium text-black"
                                    >Become a Validator</span
                                >
                                <span class="text-[12px] text-[#6b6b6b]"
                                    >Join the waitlist to start earning points</span
                                >
                            </div>
                        </div>
                        <img
                            src="/assets/icons/arrow-right-line.svg"
                            alt=""
                            class="w-4 h-4 opacity-40"
                        />
                    </button>
                {/if}

                <!-- Community XP Stat -->
                {#if isCreator}
                    <div
                        class="flex items-center justify-between bg-[#fcfcfc] rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm"
                    >
                        {#if !participant?.leaderboard_entries}
                            <div class="flex items-center gap-4 animate-pulse">
                                <div
                                    class="w-[48px] h-[48px] rounded-full bg-gray-200"
                                ></div>
                                <div class="flex flex-col gap-2">
                                    <div
                                        class="h-6 w-14 bg-gray-200 rounded"
                                    ></div>
                                    <div
                                        class="h-3 w-24 bg-gray-100 rounded"
                                    ></div>
                                </div>
                            </div>
                            <div
                                class="h-3 w-16 bg-gray-100 rounded self-start mt-1 animate-pulse"
                            ></div>
                        {:else}
                            <div class="flex items-center gap-4">
                                <CategoryIcon
                                    category="community"
                                    mode="hexagon"
                                    size={48}
                                />
                                <div class="flex flex-col">
                                    <span
                                        class="text-[24px] font-semibold text-black leading-tight"
                                        >{userCommunityPoints}</span
                                    >
                                    <span class="text-[12px] text-[#6b6b6b]"
                                        >Community XP</span
                                    >
                                </div>
                            </div>
                            <div
                                class="text-[12px] font-medium text-[#6b6b6b] self-start mt-1"
                            >
                                Rank #{communityRank || "-"}
                            </div>
                        {/if}
                    </div>
                {:else if isOwnProfile}
                    <button
                        onclick={scrollToJourneys}
                        class="flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm hover:bg-[#fafafa] transition-colors text-left w-full"
                    >
                        <div class="flex items-center gap-4">
                            <CategoryIcon
                                category="community"
                                mode="hexagon"
                                size={48}
                            />
                            <div class="flex flex-col">
                                <span class="text-[14px] font-medium text-black"
                                    >Join the community</span
                                >
                                <span class="text-[12px] text-[#6b6b6b]"
                                    >Become a referrer to earn community XP</span
                                >
                            </div>
                        </div>
                        <img
                            src="/assets/icons/arrow-right-line.svg"
                            alt=""
                            class="w-4 h-4 opacity-40"
                        />
                    </button>
                {/if}
            </div>
        </div>
    </div>
{/if}
