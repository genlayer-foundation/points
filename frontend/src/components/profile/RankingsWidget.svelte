<script lang="ts">
    import { push } from "svelte-spa-router";
    import { leaderboardAPI } from "../../lib/api";
    import Avatar from "../Avatar.svelte";
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let {
        participant = null,
        isOwnProfile = false,
        topRole = null,
        builderStats = null,
        validatorStats = null,
        communityStats = null,
        referralPoints = { builder_points: 0, validator_points: 0 },
    } = $props();

    let communityRank: number | null = $state(null);
    let communityRankLoaded = $state(false);
    const DEFAULT_TAB_ORDER = ["Builders", "Validators", "Community"];

    // Role checks
    let isBuilder = $derived(!!participant?.builder);
    let isValidator = $derived(
        !!participant?.validator || !!participant?.has_validator_waitlist,
    );
    let isCreator = $derived(!!participant?.creator);
    let isValidatorWaitlist = $derived(
        participant?.has_validator_waitlist && !participant?.validator,
    );

    function getTabForRoleKey(roleKey: string) {
        if (roleKey === "builder") return "Builders";
        if (roleKey === "validator") return "Validators";
        if (roleKey === "community") return "Community";
        return null;
    }

    let topRoleTabs = $derived.by(() => {
        const tabs: string[] = [];
        const badges = topRole?.badges || [];

        for (const badge of badges) {
            const tab = getTabForRoleKey(badge?.key || badge?.category);
            if (tab && !tabs.includes(tab)) tabs.push(tab);
        }

        const categoryTab = getTabForRoleKey(topRole?.category);
        if (categoryTab && !tabs.includes(categoryTab)) {
            tabs.push(categoryTab);
        }

        return tabs;
    });

    // Only show tabs for roles the user actually has, ordered by top role first.
    let availableTabs = $derived.by(() => {
        const tabs: string[] = [];
        if (isBuilder) tabs.push("Builders");
        if (isValidator) tabs.push("Validators");
        if (isCreator) tabs.push("Community");

        const preferred = topRoleTabs.filter((tab) => tabs.includes(tab));
        const remaining = DEFAULT_TAB_ORDER.filter(
            (tab) => tabs.includes(tab) && !preferred.includes(tab),
        );

        return [...preferred, ...remaining];
    });

    let hasAnyRankableRole = $derived(isBuilder || isValidator || isCreator);

    let activeTab: string | null = $state(null);
    let activeTabAddress: string | null = $state(null);
    let userSelectedTab = $state(false);

    // Set initial tab when available tabs change
    $effect(() => {
        const tabs = availableTabs;
        const addr = participant?.address || null;
        if (addr !== activeTabAddress) {
            activeTabAddress = addr;
            userSelectedTab = false;
            activeTab = tabs[0] || null;
            return;
        }

        if (tabs.length > 0 && (!activeTab || !tabs.includes(activeTab))) {
            activeTab = tabs[0];
        } else if (tabs.length > 0 && !userSelectedTab && activeTab !== tabs[0]) {
            activeTab = tabs[0];
        }
    });

    let loading = $state(true);
    let error: string | null = $state(null);
    let activeList: any[] = $state([]);
    let communityContextCache = new Map<string, any>();
    let communityContextPromises = new Map<string, Promise<any>>();

    function getEntryRank(entry: any, fallback: number) {
        return entry?.rank || entry?._displayRank || fallback;
    }

    function withDisplayRank(entry: any, fallback: number) {
        return {
            ...entry,
            _displayRank: getEntryRank(entry, fallback),
        };
    }

    async function fetchCommunityProfileContext(address: string) {
        if (communityContextCache.has(address)) {
            return communityContextCache.get(address);
        }
        if (communityContextPromises.has(address)) {
            return communityContextPromises.get(address);
        }

        const requestAddress = address;
        const promise = (leaderboardAPI as any)
            .getLeaderboard({
                type: "community",
                user_address: requestAddress,
                profile_context: true,
            })
            .then((res: any) => {
                const data = res.data || {};
                communityContextCache.set(requestAddress, data);
                return data;
            })
            .finally(() => {
                communityContextPromises.delete(requestAddress);
            });

        communityContextPromises.set(requestAddress, promise);
        return promise;
    }

    function buildCommunityProfileList(data: any) {
        const topEntry = data?.top_entry;
        const contextRows = data?.context_results || [];
        const rows: any[] = [];

        if (topEntry) {
            rows.push(withDisplayRank(topEntry, 1));
        }

        const contextWithoutTop = contextRows.filter((row: any) => {
            const rowRank = getEntryRank(row, 0);
            return rowRank !== 1;
        });

        if (topEntry && contextWithoutTop.length > 0) {
            const firstContextRank = getEntryRank(contextWithoutTop[0], 0);
            if (firstContextRank > 2) {
                rows.push({ isEllipsis: true });
            }
        }

        for (const row of contextWithoutTop) {
            rows.push(withDisplayRank(row, getEntryRank(row, rows.length + 1)));
        }

        return rows;
    }

    async function loadTabLeaderboard(tab: string) {
        loading = true;
        error = null;
        activeList = [];

        try {
            let apiType;
            if (tab === "Builders") apiType = "builder";
            else if (tab === "Validators") {
                apiType = isValidatorWaitlist
                    ? "validator-waitlist"
                    : "validator";
            } else if (tab === "Community") apiType = "community";
            else apiType = "builder";

            if (apiType === "community" && participant?.address) {
                const requestedAddress = participant.address;
                const communityContext = await fetchCommunityProfileContext(
                    requestedAddress,
                );
                if (participant?.address !== requestedAddress) return;
                communityRank = communityContext?.user_rank || null;
                communityRankLoaded = true;
                activeList = buildCommunityProfileList(communityContext);
                return;
            }

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
                    if (apiType === "community") {
                        userRank = userEntryRes.data?.user_rank || null;
                    }

                    const userEntries = Array.isArray(userEntryRes.data)
                        ? userEntryRes.data
                        : userEntryRes.data?.results || [];
                    if (!userRank && userEntries.length > 0) {
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

    let loadedLeaderboardKey: string | null = $state(null);
    let loadedCommunityRankForAddress: string | null = $state(null);

    $effect(() => {
        const addr = participant?.address;
        if (!addr || !hasAnyRankableRole || !activeTab) return;

        const key = `${addr}:${activeTab}`;
        if (key !== loadedLeaderboardKey) {
            loadedLeaderboardKey = key;
            loadTabLeaderboard(activeTab);
        }
    });

    $effect(() => {
        const addr = participant?.address;
        if (!addr || !isCreator || addr === loadedCommunityRankForAddress)
            return;

        loadedCommunityRankForAddress = addr;
        communityRank = null;
        communityRankLoaded = false;
        fetchCommunityProfileContext(addr)
            .then((data: any) => {
                if (participant?.address !== addr) return;
                communityRank = data?.user_rank || null;
            })
            .catch(() => {})
            .finally(() => {
                if (participant?.address !== addr) return;
                communityRankLoaded = true;
            });
    });

    function switchTab(t: string) {
        if (t !== activeTab) {
            userSelectedTab = true;
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

    let userCommunityPoints = $derived(communityStats?.totalPoints || 0);

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
    <div class="rankings-widget mt-8">
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
            {#if availableTabs.length > 0}
            <!-- Left: Leaderboard (50%) -->
            <div class="w-full lg:w-1/2 flex flex-col pt-2 min-h-[300px] min-w-0">
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
                    class="ranking-list-card bg-[#fcfcfc] border border-[#f0f0f0] rounded-[16px] overflow-hidden p-[16px]"
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
                                        class="ranking-row flex items-center justify-between rounded-[10px] px-3 py-[10px] transition-colors min-w-0
                                        {isCurrentUser(row)
                                            ? 'bg-[#f0f0f0]'
                                            : 'bg-white hover:bg-[#f8f8f8]'}"
                                    >
                                        <div
                                            class="flex items-center gap-[10px] min-w-0"
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
                                                class="text-[14px] font-medium text-black truncate min-w-0"
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
                                                    row.community_points ||
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
            {/if}

            <!-- Right: Context Stats (50% when leaderboard is shown, otherwise full width) -->
            <div
                class="ranking-context-column w-full {availableTabs.length > 0
                    ? 'lg:w-1/2'
                    : ''} flex flex-col gap-3 pt-[36px]"
            >
                <!-- Builder Stat -->
                {#if isBuilder}
                    <div
                        class="ranking-context-card flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm"
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
                        class="ranking-context-card flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm hover:bg-[#fafafa] transition-colors text-left w-full"
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
                        class="ranking-context-card flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm"
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
                        class="ranking-context-card flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm hover:bg-[#fafafa] transition-colors text-left w-full"
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

                <!-- Community Points Stat -->
                {#if isCreator}
                    <div
                        class="ranking-context-card flex items-center justify-between bg-[#fcfcfc] rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm"
                    >
                        {#if !communityRankLoaded && userCommunityPoints > 0}
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
                                        >Community Points</span
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
                        class="ranking-context-card flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm hover:bg-[#fafafa] transition-colors text-left w-full"
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
                                    >Link socials and submit community contributions</span
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

<style>
    @media (max-width: 767px) {
        .rankings-widget {
            max-width: 100%;
            overflow-x: hidden;
        }

        .ranking-list-card {
            border-radius: 12px;
            padding: 10px;
        }

        .ranking-row {
            gap: 10px;
            padding: 10px;
        }

        .ranking-context-column {
            padding-top: 12px;
        }

        .ranking-context-card {
            min-width: 0;
            height: auto;
            min-height: 82px;
            padding: 16px;
        }

        .ranking-context-card > div:first-child {
            min-width: 0;
        }

        .ranking-context-card span {
            overflow-wrap: anywhere;
        }
    }
</style>
