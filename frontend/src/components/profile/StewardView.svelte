<script>
    import { format } from "date-fns";
    import CategoryIcon from "../portal/CategoryIcon.svelte";

    let { participant = null } = $props();

    let stewardRole = $derived(
        participant?.working_groups?.length > 0 ? "Working Group Member" : "Admin"
    );

    let memberSinceDate = $derived(
        participant?.steward?.created_at
            || (participant?.working_groups?.length > 0
                ? participant.working_groups.reduce((earliest, wg) =>
                    !earliest || (wg.joined_at && wg.joined_at < earliest) ? wg.joined_at : earliest,
                  null)
                : null)
    );

    let memberSince = $derived(
        memberSinceDate ? format(new Date(memberSinceDate), "MMM yyyy") : "-"
    );
</script>

<div class="w-full flex flex-col items-start mt-8">
    <!-- Header -->
    <div class="flex items-center gap-[10px] mb-4">
        <div class="relative flex-shrink-0" style="width: 32px; height: 32px;">
            <img
                src="/assets/icons/hexagon-steward-light.svg"
                alt=""
                class="w-full h-full"
            />
            <img
                src="/assets/icons/seedling-line-green.svg"
                alt=""
                class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                style="width: 16px; height: 16px;"
            />
        </div>
        <h2
            class="text-[20px] font-semibold text-black"
            style="letter-spacing: 0.4px;"
        >
            Ecosystem Steward
        </h2>
    </div>

    <!-- Metrics Row -->
    <div class="flex flex-col md:flex-row gap-4 mb-6 w-full">
        <!-- Role Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            <div class="flex h-full items-center">
                <div
                    class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                >
                    <CategoryIcon category="steward" mode="hexagon" size={48} />
                </div>
                <div
                    class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                >
                    <p
                        class="font-semibold text-[24px] leading-[32px] tracking-[-0.96px] text-black"
                    >
                        {stewardRole}
                    </p>
                    <p
                        class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                    >
                        Role
                    </p>
                </div>
            </div>
        </div>

        <!-- Member Since Card -->
        <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative overflow-hidden"
        >
            <div class="flex h-full items-center">
                <div
                    class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                >
                    <img
                        src="/assets/icons/hexagon-steward.svg"
                        alt=""
                        class="w-full h-full"
                    />
                    <svg
                        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-5 h-5 brightness-0 invert"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                    >
                        <path
                            d="M17 3H21C21.5523 3 22 3.44772 22 4V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V4C2 3.44772 2.44772 3 3 3H7V1H9V3H15V1H17V3ZM4 9V19H20V9H4ZM6 11H8V13H6V11ZM11 11H13V13H11V11ZM16 11H18V13H16V11Z"
                        />
                    </svg>
                </div>
                <div
                    class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                >
                    <p
                        class="font-semibold text-[26px] leading-[32px] tracking-[-0.96px] text-black"
                    >
                        {memberSince}
                    </p>
                    <p
                        class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                    >
                        Member Since
                    </p>
                </div>
            </div>
        </div>
    </div>

    <!-- Working Groups -->
    {#if participant?.working_groups?.length > 0}
        <div class="w-full mt-4">
            <h3
                class="font-semibold text-[20px] text-black mb-[20px]"
                style="letter-spacing: 0.4px;"
            >
                Member of
            </h3>
            <div class="flex flex-col gap-3">
                {#each participant.working_groups as wg}
                    <div
                        class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center justify-between p-[16px] w-full"
                    >
                        <div class="flex items-center gap-3">
                            {#if wg.icon}
                                <div class="w-8 h-8 rounded-full bg-gray-50 flex items-center justify-center text-lg">
                                    {wg.icon}
                                </div>
                            {:else}
                                <div class="w-10 h-10 rounded-full bg-green-50 flex items-center justify-center flex-shrink-0">
                                    <CategoryIcon
                                        category={wg.name?.toLowerCase().includes('builder') ? 'builder' : wg.name?.toLowerCase().includes('validator') ? 'validator' : 'steward'}
                                        mode="hexagon"
                                        size={32}
                                    />
                                </div>
                            {/if}
                            <span class="text-[15px] font-medium text-black">{wg.name}</span>
                        </div>
                        {#if wg.participant_count != null}
                            <div class="flex items-center gap-1 text-[12px] text-[#6b6b6b]">
                                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M2 22a8 8 0 1 1 16 0H2zm8-9c-3.315 0-6-2.685-6-6s2.685-6 6-6 6 2.685 6 6-2.685 6-6 6zm7.363 1.233A7.505 7.505 0 0 0 17.5 7.5a7.48 7.48 0 0 0-.507-2.694A5.002 5.002 0 0 1 22 9.5a5 5 0 0 1-4.637 4.733zM17.5 21.5h4A7.5 7.5 0 0 0 17 15.674a8.962 8.962 0 0 1 2.5 5.826H17.5z" />
                                </svg>
                                {wg.participant_count}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
