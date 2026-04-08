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
        if (cat === "builder") {
            return {
                pillBg: "rgba(238,141,36,0.1)",
                pillText: "#ee8d24",
                tagBorder: "#ee8d24",
                tagText: "#ee8d24",
            };
        }
        return {
            pillBg: "rgba(79,118,246,0.1)",
            pillText: "#4f76f6",
            tagBorder: "#4f76f6",
            tagText: "#4f76f6",
        };
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
                    style="border: 1px solid #f5f5f5;"
                >
                    <!-- Top row: avatar + username | points pill -->
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
                        <span
                            class="text-xs font-medium px-2 py-0.5 rounded-full"
                            style="background: {colors.pillBg}; color: {colors.pillText};"
                        >
                            {points} pts
                        </span>
                    </div>

                    <!-- Middle: title + description -->
                    <div class="flex-1 min-h-0 overflow-hidden">
                        <div class="flex items-center gap-[6px]">
                            {#if hasHighlight}
                                <div class="relative w-[20px] h-[20px] flex-shrink-0">
                                    <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full" />
                                    <div
                                        class="absolute inset-0 m-auto w-[10px] h-[10px]"
                                        style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
                                    ></div>
                                </div>
                            {/if}
                            <h3 class="text-sm font-medium text-black truncate">
                                {#if hasHighlight}
                                    {contrib.highlight.title}
                                {:else if contrib.title}
                                    {contrib.title}
                                {:else}
                                    {typeName}{#if count > 1}
                                        <span
                                            class="text-xs font-normal"
                                            style="color: #999;"
                                            >× {count}</span
                                        >
                                    {/if}
                                {/if}
                            </h3>
                        </div>
                        <p
                            class="text-xs mt-1 line-clamp-3"
                            style="color: #6b6b6b;"
                        >
                            {#if hasHighlight}
                                {contrib.highlight.description}
                            {:else if contrib.title && contrib.notes}
                                {contrib.notes}
                            {:else if contrib.title}
                                {typeName} contribution
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
