<script>
    import { onMount } from "svelte";
    import { push } from "svelte-spa-router";
    import { format } from "date-fns";
    import { contributionsAPI } from "../../lib/api.js";

    let {
        userId = null,
        category = null,
        limit = 5,
        showViewAll = true,
        viewAllPath = "/contributions",
        viewAllText = "View All Contributions →",
    } = $props();

    let contributions = $state([]);
    let loading = $state(true);
    let error = $state(null);

    const formatDate = (dateString) => {
        try {
            return format(new Date(dateString), "MMM d, yyyy");
        } catch (e) {
            return dateString;
        }
    };

    function getCategoryColors(cat) {
        const map = {
            builder: {
                pillBg: "rgba(238,133,33,0.1)", pillText: "#ee8521",
                tagBorder: "#ee8521", tagText: "#ee8521",
                tintedBg: "#FEF3E2",
            },
            validator: {
                pillBg: "rgba(56,125,232,0.1)", pillText: "#387DE8",
                tagBorder: "#387DE8", tagText: "#387DE8",
                tintedBg: "#EBF3FE",
            },
            community: {
                pillBg: "rgba(127,82,225,0.1)", pillText: "#7F52E1",
                tagBorder: "#7F52E1", tagText: "#7F52E1",
                tintedBg: "#F4ECFD",
            },
        };
        return map[cat] || map.validator;
    }

    async function fetchContributions() {
        try {
            loading = true;
            const params = {
                limit,
                ordering: "-created_at",
                group_consecutive: true,
            };

            if (userId) params.user_address = userId;
            if (category) params.category = category;

            const response =
                await contributionsAPI.getContributions(params);
            contributions = response.data.results || [];
        } catch (err) {
            error = err.message || "Failed to load contributions";
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        fetchContributions();
    });
</script>

<div>
    {#if loading}
        <div class="flex gap-2.5 overflow-x-auto pb-2">
            {#each [1, 2, 3] as _}
                <div
                    class="flex-shrink-0 w-[300px] h-[180px] rounded-[8px] bg-gray-100 animate-pulse"
                ></div>
            {/each}
        </div>
    {:else if contributions.length === 0}
        <div
            class="w-full rounded-[12px] bg-white border border-[#e5e5e5] py-6 px-4 flex flex-col items-center justify-center gap-1"
        >
            <span class="text-[14px] text-[#999]">No contributions yet.</span>
            <span class="text-[14px] text-[#999]">Submit your first to start earning points.</span>
        </div>
    {:else}
        <div
            class="flex gap-2.5 overflow-x-auto pb-2"
            style="-ms-overflow-style: none; scrollbar-width: none;"
        >
            {#each contributions as contrib}
                {@const cat =
                    contrib.contribution_type_details?.category ||
                    category ||
                    "validator"}
                {@const colors = getCategoryColors(cat)}
                {@const typeName =
                    contrib.contribution_type_name ||
                    contrib.contribution_type_details?.name ||
                    "Contribution"}
                {@const displayTitle = contrib.mission?.name || typeName}
                {@const points =
                    contrib.frozen_global_points ||
                    contrib.frozen_points ||
                    contrib.points ||
                    0}
                {@const user =
                    contrib.user_details ||
                    (contrib.users && contrib.users[0]) ||
                    null}
                {@const count = contrib.count || 1}
                {@const hasHighlight = !!contrib.highlight}
                {@const realId = contrib.grouped_contributions?.[0]?.id || contrib.id}
                <button
                    onclick={() => push(`/contribution/${realId}`)}
                    class="flex-shrink-0 w-[300px] h-[180px] rounded-[8px] p-4 flex flex-col gap-2 text-left hover:shadow-md transition-shadow cursor-pointer"
                    style="background: {hasHighlight ? colors.tintedBg : '#FFFFFF'}; {hasHighlight ? '' : 'border: 1px solid #f5f5f5;'}"
                >
                    <!-- Top row: avatar + username | points pill + highlight star -->
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            {#if user?.profile_image_url}
                                <img
                                    src={user.profile_image_url}
                                    alt=""
                                    class="w-6 h-6 rounded-full"
                                />
                            {:else}
                                <div
                                    class="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-medium text-gray-500"
                                >
                                    {(user?.name || "?")[0].toUpperCase()}
                                </div>
                            {/if}
                            <span
                                class="text-sm font-medium"
                                style="color: #bbb;"
                            >
                                {user?.name ||
                                    `${user?.address?.slice(0, 6)}...`}
                            </span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span
                                class="text-xs font-medium px-2 py-0.5 rounded-full"
                                style="background: {colors.pillBg}; color: {colors.pillText};"
                            >
                                {points} pts
                            </span>
                            {#if hasHighlight}
                                <div class="relative w-[32px] h-[32px] flex-shrink-0">
                                    <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full" />
                                    <div
                                        class="absolute inset-0 m-auto w-[16px] h-[16px]"
                                        style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
                                    ></div>
                                </div>
                            {/if}
                        </div>
                    </div>

                    <!-- Middle: title + description -->
                    <div class="flex-1 min-h-0 overflow-hidden">
                        <h3 class="text-sm font-medium text-black truncate">
                            {#if hasHighlight}
                                {contrib.highlight.title || displayTitle}
                            {:else if contrib.title}
                                {contrib.title}
                            {:else}
                                {displayTitle}{#if count > 1}
                                    <span
                                        class="text-xs font-normal"
                                        style="color: #999;"
                                        >× {count}</span
                                    >
                                {/if}
                            {/if}
                        </h3>
                        <p
                            class="text-xs mt-1 line-clamp-3"
                            style="color: #6b6b6b;"
                        >
                            {#if hasHighlight}
                                {contrib.highlight.description}
                            {:else if contrib.notes}
                                {contrib.notes}
                            {:else}
                                {typeName} contribution
                            {/if}
                        </p>
                    </div>

                    <!-- Bottom row: category tag + date -->
                    <div class="flex items-center justify-between">
                        <span
                            class="text-xs px-2 py-0.5 rounded-full"
                            style="border: 1px solid {colors.tagBorder}; color: {colors.tagText};"
                        >
                            {typeName}
                        </span>
                        <span class="text-xs" style="color: #bababa;">
                            {formatDate(contrib.contribution_date)}
                        </span>
                    </div>
                </button>
            {/each}
        </div>

        {#if showViewAll}
            <div class="mt-3 flex justify-end">
                <button
                    onclick={() => push(viewAllPath)}
                    class="text-sm text-[#999] hover:text-black transition-colors"
                >
                    {viewAllText}
                </button>
            </div>
        {/if}
    {/if}
</div>
