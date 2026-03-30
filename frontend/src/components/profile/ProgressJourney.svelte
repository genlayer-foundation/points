<script>
    import { authState } from "../../lib/auth";
    import { onMount } from "svelte";
    import { showWarning, showError } from "../../lib/toastStore";
    import { FAUCET_URL } from "../../lib/config";
    import GitHubLink from "../GitHubLink.svelte";

    let {
        testnetBalance = null,
        hasBuilderWelcome = false,
        hasDeployedContract = false,
        githubUsername = "",
        hasStarredRepo = false,
        repoToStar = "genlayerlabs/genlayer-project-boilerplate",
        onClaimBuilderBadge = null,
        isClaimingBuilderBadge = false,
        onRefreshBalance = null,
        isRefreshingBalance = false,
        onOpenStudio = null,
        onGitHubLinked = null,
        onCheckRepoStar = null,
        isCheckingRepoStar = false,
        onCompleteJourney = null,
        isCompletingJourney = false,
    } = $props();

    // Network states
    let hasAsimovNetwork = $state(false);
    let hasStudioNetwork = $state(false);
    let isCheckingNetworks = $state(false);
    let isAddingAsimov = $state(false);
    let isAddingStudio = $state(false);

    let walletAddress = $derived($authState.address);

    function getStorageKey(network) {
        if (!walletAddress) return null;
        return `genlayer_${network}_network_added_${walletAddress.toLowerCase()}`;
    }

    function loadNetworkState() {
        if (typeof window === "undefined" || !walletAddress) return;
        const asimovKey = getStorageKey("asimov");
        const studioKey = getStorageKey("studio");
        hasAsimovNetwork = asimovKey
            ? localStorage.getItem(asimovKey) === "true"
            : false;
        hasStudioNetwork = studioKey
            ? localStorage.getItem(studioKey) === "true"
            : false;
    }

    $effect(() => {
        loadNetworkState();
    });

    const ASIMOV_NETWORK = {
        chainId: "0x107D",
        chainName: "GenLayer Testnet Chain",
        nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
        rpcUrls: ["https://rpc.testnet-chain.genlayer.com"],
        blockExplorerUrls: [
            "https://explorer.testnet-chain.genlayer.com",
        ],
    };

    const STUDIO_NETWORK = {
        chainId: "0xF22F",
        chainName: "GenLayer Studio",
        nativeCurrency: { name: "GEN", symbol: "GEN", decimals: 18 },
        rpcUrls: ["https://studio.genlayer.com/api"],
        blockExplorerUrls: [],
    };

    async function checkNetworks() {
        const provider = $authState.provider || window.ethereum;
        if (!provider || !walletAddress) return;
        isCheckingNetworks = true;
        try {
            const currentChainId = await provider.request({
                method: "eth_chainId",
            });
            if (
                currentChainId === ASIMOV_NETWORK.chainId &&
                !hasAsimovNetwork
            ) {
                hasAsimovNetwork = true;
                const key = getStorageKey("asimov");
                if (key) localStorage.setItem(key, "true");
            }
            if (
                currentChainId === STUDIO_NETWORK.chainId &&
                !hasStudioNetwork
            ) {
                hasStudioNetwork = true;
                const key = getStorageKey("studio");
                if (key) localStorage.setItem(key, "true");
            }
        } catch (error) {
        } finally {
            isCheckingNetworks = false;
        }
    }

    async function addNetwork(network, isStudio = false) {
        const provider = $authState.provider || window.ethereum;
        if (!provider) {
            showWarning("Please connect your wallet first");
            return;
        }

        if (isStudio) isAddingStudio = true;
        else isAddingAsimov = true;

        try {
            await provider.request({
                method: "wallet_addEthereumChain",
                params: [network],
            });
            if (isStudio) {
                hasStudioNetwork = true;
                const key = getStorageKey("studio");
                if (key) localStorage.setItem(key, "true");
            } else {
                hasAsimovNetwork = true;
                const key = getStorageKey("asimov");
                if (key) localStorage.setItem(key, "true");
            }
        } catch (error) {
            if (error.code !== 4001) {
                showError("Failed to add network. Please try manually.");
            }
        } finally {
            if (isStudio) isAddingStudio = false;
            else isAddingAsimov = false;
        }
    }

    let completedCount = $derived(
        (walletAddress ? 1 : 0) +
            (hasBuilderWelcome ? 1 : 0) +
            (githubUsername ? 1 : 0) +
            (hasStarredRepo ? 1 : 0) +
            (hasAsimovNetwork ? 1 : 0) +
            (testnetBalance && testnetBalance > 0 ? 1 : 0) +
            (hasStudioNetwork ? 1 : 0) +
            (hasDeployedContract ? 1 : 0),
    );

    let hasTestnetBalance = $derived(testnetBalance && testnetBalance > 0);
    let allCoreRequirementsMet = $derived(
        hasBuilderWelcome &&
            !!githubUsername &&
            hasStarredRepo &&
            hasTestnetBalance &&
            hasDeployedContract,
    );
</script>

<div
    class="bg-white rounded-[12px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.02)] p-6 w-full"
>
    <!-- Title and Subtitle -->
    <div class="flex flex-col gap-2 mb-4">
        <h2
            class="font-['Switzer'] font-semibold text-[20px] text-black tracking-[0.4px]"
        >
            Complete your builder journey
        </h2>
        <p
            class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
        >
            {8 - completedCount} steps remaining to complete your builder journey.
        </p>
    </div>

    <!-- Journey Progress Bar -->
    <div class="w-full bg-[#eae9f3] rounded-[4px] h-[8px] mb-6 overflow-hidden">
        <div
            class="bg-[#ee8521] h-full transition-all duration-500 rounded-[4px]"
            style="width: {(completedCount / 8) * 100}%"
        ></div>
    </div>

    <div class="space-y-2">
        <!-- Requirement 1: Connect Wallet -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if walletAddress}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Connect your wallet</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Link your Web3 wallet</span
                    >
                </div>
            </div>
            <div>
                {#if walletAddress}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Connected
                    </div>
                {:else}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Connected
                    </div>
                {/if}
            </div>
        </div>

        <!-- Requirement 2: Earn your first points -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasBuilderWelcome}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Earn your first points</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Claim your Builder Welcome Contribution</span
                    >
                </div>
            </div>
            <div>
                {#if hasBuilderWelcome}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Done
                    </div>
                {:else}
                    <button
                        onclick={() =>
                            onClaimBuilderBadge ? onClaimBuilderBadge() : null}
                        disabled={isClaimingBuilderBadge ||
                            !onClaimBuilderBadge ||
                            !walletAddress}
                        class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap disabled:opacity-50"
                    >
                        {isClaimingBuilderBadge
                            ? "Claiming..."
                            : "Claim Points"}
                    </button>
                {/if}
            </div>
        </div>

        <!-- Requirement 3: Link GitHub -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if githubUsername}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Connect your GitHub</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Link your GitHub account</span
                    >
                </div>
            </div>
            <div>
                {#if githubUsername}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Connected
                    </div>
                {:else}
                    <GitHubLink
                        onLinked={onGitHubLinked}
                        buttonClass="flex items-center gap-[6px] px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap"
                        buttonText="Connect GitHub"
                    />
                {/if}
            </div>
        </div>

        <!-- Requirement 4: Star Boilerplate Repo -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasStarredRepo}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Star the Boilerplate repo</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Star the boilerplate repo on GitHub</span
                    >
                </div>
            </div>
            <div>
                {#if hasStarredRepo}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Starred
                    </div>
                {:else if githubUsername}
                    <div class="flex items-center gap-3">
                        {#if onCheckRepoStar}
                            <button
                                onclick={onCheckRepoStar}
                                disabled={isCheckingRepoStar}
                                class="flex items-center justify-center p-1.5 rounded-full hover:bg-gray-100 transition-colors group disabled:opacity-50"
                                title="Verify Star"
                                aria-label="Verify Star"
                            >
                                <svg
                                    class="w-4 h-4 text-[#6b6b6b] opacity-50 group-hover:opacity-100 {isCheckingRepoStar
                                        ? 'animate-spin [animation-direction:reverse]'
                                        : ''}"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2.5"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                >
                                    <path
                                        d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"
                                    />
                                    <path d="M3 3v5h5" />
                                </svg>
                            </button>
                        {/if}
                        <a
                            href="https://github.com/{repoToStar}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap block"
                        >
                            Star Repo
                        </a>
                    </div>
                {:else}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px] cursor-not-allowed"
                    >
                        Star Repo
                    </div>
                {/if}
            </div>
        </div>

        <!-- Requirement 5: Add GenLayer Testnet Chain -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasAsimovNetwork}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Add GenLayer Testnet Chain</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Add the testnet to your wallet</span
                    >
                </div>
            </div>
            <div>
                {#if hasAsimovNetwork}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Added
                    </div>
                {:else if walletAddress}
                    <div class="flex items-center gap-3">
                        <button
                            onclick={checkNetworks}
                            disabled={isCheckingNetworks}
                            class="flex items-center justify-center p-1.5 rounded-full hover:bg-gray-100 transition-colors group disabled:opacity-50"
                            title="Verify Network"
                            aria-label="Verify Network"
                        >
                            <svg
                                class="w-4 h-4 text-[#6b6b6b] opacity-50 group-hover:opacity-100 {isCheckingNetworks
                                    ? 'animate-spin [animation-direction:reverse]'
                                    : ''}"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2.5"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <path
                                    d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"
                                />
                                <path d="M3 3v5h5" />
                            </svg>
                        </button>
                        <button
                            onclick={() => addNetwork(ASIMOV_NETWORK, false)}
                            disabled={isAddingAsimov}
                            class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap disabled:opacity-50"
                        >
                            {isAddingAsimov ? "Adding..." : "Add Network"}
                        </button>
                    </div>
                {:else}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px] cursor-not-allowed"
                    >
                        Add Network
                    </div>
                {/if}
            </div>
        </div>

        <!-- Requirement 6: Top-up testnet GEN -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasTestnetBalance}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Top-up with Testnet GEN</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Get testnet tokens for deployment</span
                    >
                </div>
            </div>
            <div>
                {#if hasTestnetBalance}
                    <a
                        href={FAUCET_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        class="px-[12px] py-[6px] border border-[#e0e0e0] bg-white rounded-[6px] text-[14px] font-['Switzer'] font-medium text-black tracking-[0.28px] hover:bg-gray-50 transition-colors whitespace-nowrap block"
                        >Get More</a
                    >
                {:else}
                    <div class="flex items-center gap-3">
                        {#if onRefreshBalance && hasAsimovNetwork}
                            <button
                                onclick={onRefreshBalance}
                                disabled={isRefreshingBalance}
                                class="flex items-center justify-center p-1.5 rounded-full hover:bg-gray-100 transition-colors group disabled:opacity-50"
                                title="Verify Balance"
                                aria-label="Verify Balance"
                            >
                                <svg
                                    class="w-4 h-4 text-[#6b6b6b] opacity-50 group-hover:opacity-100 {isRefreshingBalance
                                        ? 'animate-spin [animation-direction:reverse]'
                                        : ''}"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="2.5"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                >
                                    <path
                                        d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"
                                    />
                                    <path d="M3 3v5h5" />
                                </svg>
                            </button>
                        {/if}
                        <a
                            href={FAUCET_URL}
                            target="_blank"
                            rel="noopener noreferrer"
                            class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap block"
                            >Get Tokens</a
                        >
                    </div>
                {/if}
            </div>
        </div>

        <!-- Requirement 7: At the Studio Network -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasStudioNetwork}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Add Studio Network</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Connect to studio.genlayer.com</span
                    >
                </div>
            </div>
            <div>
                {#if hasStudioNetwork}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Added
                    </div>
                {:else if walletAddress}
                    <div class="flex items-center gap-3">
                        <button
                            onclick={checkNetworks}
                            disabled={isCheckingNetworks}
                            class="flex items-center justify-center p-1.5 rounded-full hover:bg-gray-100 transition-colors group disabled:opacity-50"
                            title="Verify Network"
                            aria-label="Verify Network"
                        >
                            <svg
                                class="w-4 h-4 text-[#6b6b6b] opacity-50 group-hover:opacity-100 {isCheckingNetworks
                                    ? 'animate-spin [animation-direction:reverse]'
                                    : ''}"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                stroke-width="2.5"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            >
                                <path
                                    d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"
                                />
                                <path d="M3 3v5h5" />
                            </svg>
                        </button>
                        <button
                            onclick={() => addNetwork(STUDIO_NETWORK, true)}
                            disabled={isAddingStudio}
                            class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap disabled:opacity-50"
                        >
                            {isAddingStudio ? "Adding..." : "Add Network"}
                        </button>
                    </div>
                {:else}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px] cursor-not-allowed"
                    >
                        Add Network
                    </div>
                {/if}
            </div>
        </div>

        <!-- Requirement 8: Deploy First Contract -->
        <div class="flex items-center justify-between py-1">
            <div class="flex items-center gap-3 w-full md:w-auto">
                <div
                    class="flex-shrink-0 w-5 h-5 flex items-center justify-center"
                >
                    {#if hasDeployedContract}
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M10 18.3333C14.6025 18.3333 18.3333 14.6025 18.3333 10C18.3333 5.3975 14.6025 1.66667 10 1.66667C5.3975 1.66667 1.66667 5.3975 1.66667 10C1.66667 14.6025 5.3975 18.3333 10 18.3333Z"
                                stroke="#EE8521"
                                stroke-width="1.25"
                                stroke-linecap="round"
                                stroke-linejoin="round"
                            />
                            <path
                                d="M6.25 10L8.75 12.5L13.75 7.5"
                                stroke="#EE8521"
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
                        >Deploy your first contract</span
                    >
                    <span
                        class="font-['Switzer'] font-medium text-[12px] text-[#6b6b6b] tracking-[0.24px]"
                        >Deploy an intelligent contract</span
                    >
                </div>
            </div>
            <div>
                {#if hasDeployedContract}
                    <div
                        class="px-[12px] py-[6px] bg-[#f2f2f2] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-[#ababab] tracking-[0.28px]"
                    >
                        Deployed
                    </div>
                {:else if onOpenStudio}
                    <button
                        onclick={onOpenStudio}
                        class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap disabled:opacity-50"
                    >
                        Open Studio
                    </button>
                {:else}
                    <a
                        href="https://studio.genlayer.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="px-[12px] py-[6px] bg-[#ee8521] rounded-[6px] text-[14px] font-['Switzer'] font-medium text-white tracking-[0.28px] hover:bg-[#d6771e] transition-colors whitespace-nowrap block disabled:opacity-50"
                    >
                        Open Studio
                    </a>
                {/if}
            </div>
        </div>
    </div>

    <!-- Complete Journey Final Action -->
    <div class="mt-8">
        <button
            onclick={onCompleteJourney}
            disabled={!allCoreRequirementsMet || isCompletingJourney}
            class="w-full h-[40px] flex items-center justify-center rounded-[24px] text-[14px] font-['Switzer'] font-medium tracking-[0.28px] transition-colors {allCoreRequirementsMet
                ? 'bg-[#ee8521] text-white hover:bg-[#d6771e]'
                : 'bg-[#f2f2f2] text-[#ababab] cursor-not-allowed'}"
        >
            {isCompletingJourney ? "Completing..." : "Complete Builder Journey"}
        </button>
    </div>
</div>
