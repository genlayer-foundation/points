<script>
    import SocialLink from "../SocialLink.svelte";

    let {
        participant = null,
        onSocialLinked = () => {},
        onClaimX = () => {},
        onClaimDiscord = () => {},
        isClaimingX = false,
        isClaimingDiscord = false,
    } = $props();

    let hasXConnection = $derived(!!participant?.twitter_connection);
    let hasDiscordConnection = $derived(!!participant?.discord_connection);
    let hasLinkedX = $derived(participant?.has_community_link_x || false);
    let hasLinkedDiscord = $derived(participant?.has_community_link_discord || false);
    let completedCount = $derived((hasLinkedX ? 1 : 0) + (hasLinkedDiscord ? 1 : 0));
</script>

<div
    class="bg-white rounded-[12px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] p-6 w-full"
>
    <!-- Title and Subtitle -->
    <div class="flex flex-col gap-2 mb-4">
        <h2
            class="font-['Switzer'] font-semibold text-[20px] text-black tracking-[0.4px]"
        >
            Complete your community journey
        </h2>
        <p
            class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
        >
            {#if completedCount === 2}
                All steps completed!
            {:else}
                {2 - completedCount} step{2 - completedCount !== 1 ? 's' : ''} remaining to complete your community journey.
            {/if}
        </p>
    </div>

    <!-- Journey Progress Bar -->
    <div class="w-full bg-[#eae9f3] rounded-[4px] h-[8px] mb-6 overflow-hidden">
        <div
            class="bg-[#7f52e1] h-full transition-all duration-500 rounded-[4px]"
            style="width: {(completedCount / 2) * 100}%"
        ></div>
    </div>

    <div class="space-y-2">
        <!-- Step 1: Link X (Twitter) -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasLinkedX}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#7f52e1"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#7f52e1"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    {:else}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#C4C4C4"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    {/if}
                </div>
                <div class="flex flex-col">
                    <span
                        class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px]"
                        >Link X (Twitter)</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Connect your X account to earn 20 points</span
                    >
                </div>
            </div>
            <div>
                {#if hasLinkedX}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Done
                    </div>
                {:else if hasXConnection}
                    <button
                        onclick={() => onClaimX()}
                        disabled={isClaimingX}
                        class="px-[12px] py-[6px] bg-[#7f52e1] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#6b3fd4] transition-colors whitespace-nowrap disabled:opacity-50"
                    >
                        {isClaimingX ? 'Claiming...' : 'Claim 20 pts'}
                    </button>
                {:else}
                    <SocialLink
                        platform="twitter"
                        platformLabel="X"
                        connection={participant?.twitter_connection}
                        initiateUrl="/api/auth/twitter/"
                        onLinked={onSocialLinked}
                        compact={false}
                    />
                {/if}
            </div>
        </div>

        <!-- Step 2: Link Discord -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasLinkedDiscord}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#7f52e1"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#7f52e1"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    {:else}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#C4C4C4"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                        </svg>
                    {/if}
                </div>
                <div class="flex flex-col">
                    <span
                        class="font-['Switzer'] font-medium text-[14px] text-black tracking-[0.28px]"
                        >Link Discord</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Connect your Discord account to earn 20 points</span
                    >
                </div>
            </div>
            <div>
                {#if hasLinkedDiscord}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Done
                    </div>
                {:else if hasDiscordConnection}
                    <button
                        onclick={() => onClaimDiscord()}
                        disabled={isClaimingDiscord}
                        class="px-[12px] py-[6px] bg-[#7f52e1] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#6b3fd4] transition-colors whitespace-nowrap disabled:opacity-50"
                    >
                        {isClaimingDiscord ? 'Claiming...' : 'Claim 20 pts'}
                    </button>
                {:else}
                    <SocialLink
                        platform="discord"
                        platformLabel="Discord"
                        connection={participant?.discord_connection}
                        initiateUrl="/api/auth/discord/"
                        onLinked={onSocialLinked}
                        compact={false}
                    />
                {/if}
            </div>
        </div>
    </div>
</div>
