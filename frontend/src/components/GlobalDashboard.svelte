<script>
  import { onMount } from "svelte";
  import { push } from "svelte-spa-router";
  import { format } from "date-fns";
  import TopLeaderboard from "./TopLeaderboard.svelte";
  import CategoryIcon from "./portal/CategoryIcon.svelte";
  import { leaderboardAPI, validatorsAPI } from "../lib/api";
  import { showError } from "../lib/toastStore";

  // State management
  let networkStats = $state({ asimov: { total: 0 }, bradbury: { total: 0 } });
  let networks = $state([]);
  let asimovLeaderboard = $state([]);
  let bradburyLeaderboard = $state([]);
  let waitlistLeaderboard = $state([]);
  let loading = $state(true);

  async function fetchGlobalData() {
    try {
      loading = true;

      // Fetch all necessary data in one parallel batch
      const [
        asimovLeaderboardRes,
        bradburyLeaderboardRes,
        waitlistLeaderboardRes,
        networksRes,
      ] = await Promise.all([
        leaderboardAPI.getLeaderboardByType("validator", "asc", {
          network: "asimov",
        }),
        leaderboardAPI.getLeaderboardByType("validator", "asc", {
          network: "bradbury",
        }),
        leaderboardAPI.getWaitlistTop(5),
        validatorsAPI.getNetworks().catch(() => ({ data: [] })),
      ]);

      // Process leaderboards — full list for count, top 5 for display
      const asimovFull = Array.isArray(asimovLeaderboardRes.data)
        ? asimovLeaderboardRes.data
        : [];
      const bradburyFull = Array.isArray(bradburyLeaderboardRes.data)
        ? bradburyLeaderboardRes.data
        : [];
      asimovLeaderboard = asimovFull.slice(0, 5).map((entry, i) => ({ ...entry, rank: i + 1 }));
      bradburyLeaderboard = bradburyFull.slice(0, 5).map((entry, i) => ({ ...entry, rank: i + 1 }));
      waitlistLeaderboard = Array.isArray(waitlistLeaderboardRes.data)
        ? waitlistLeaderboardRes.data
        : [];

      // Process networks for Explorers
      let fetchedNetworks = networksRes.data || [];
      const asimov = fetchedNetworks.find((n) => n.key === "asimov") || {
        key: "asimov",
        name: "Asimov",
      };
      const bradbury = fetchedNetworks.find((n) => n.key === "bradbury") || {
        key: "bradbury",
        name: "Bradbury",
      };

      if (!asimov.explorer_url)
        asimov.explorer_url = "https://explorer.testnet-chain.genlayer.com/";
      if (!bradbury.explorer_url)
        bradbury.explorer_url = "https://explorer.testnet-chain.genlayer.com/";
      networks = [asimov, bradbury];

      // Validator count per network from leaderboard entries (active on-chain validators)
      networkStats = {
        asimov: { total: asimovFull.length },
        bradbury: { total: bradburyFull.length },
      };

      loading = false;
    } catch (error) {
      console.error("Dashboard fetch error:", error);
      showError("Failed to load dashboard data. Please refresh the page.");
      loading = false;
    }
  }

  onMount(() => {
    fetchGlobalData();
  });
</script>

<div class="space-y-6 sm:space-y-8">
  <!-- Title Section -->
  <div class="flex flex-col gap-1">
    <h1
      class="text-[24px] font-semibold text-gray-900 font-display"
      style="letter-spacing: -0.5px;"
    >
      Testnets
    </h1>
    <p class="text-[14px] text-[#6b6b6b]" style="letter-spacing: 0.28px;">
      Monitor GenLayer's live testnets and validator metrics.
    </p>
  </div>

  {#if loading}
    <!-- Skeleton loading state -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {#each [1, 2] as _}
        <div class="bg-white rounded-[8px] border border-[#f0f0f0] flex flex-col overflow-hidden animate-pulse">
          <!-- Header skeleton -->
          <div class="px-6 py-5 border-b border-[#f0f0f0] flex items-center gap-3">
            <div class="w-8 h-8 rounded bg-gray-200"></div>
            <div class="flex flex-col gap-1.5">
              <div class="h-5 w-24 bg-gray-200 rounded"></div>
              <div class="h-3 w-16 bg-gray-100 rounded"></div>
            </div>
          </div>

          <div class="p-6 space-y-8">
            <!-- Stat box skeleton -->
            <div class="p-5 rounded-[8px] bg-gray-50 border border-[#f0f0f0] flex flex-col gap-1 w-full">
              <div class="h-3 w-28 bg-gray-200 rounded"></div>
              <div class="flex items-baseline gap-2 mt-2">
                <div class="h-8 w-16 bg-gray-200 rounded"></div>
                <div class="h-3 w-16 bg-gray-100 rounded"></div>
              </div>
            </div>

            <!-- Leaderboard skeleton -->
            <div>
              <div class="flex items-center justify-between mb-3">
                <div class="h-4 w-40 bg-gray-200 rounded"></div>
                <div class="h-3 w-24 bg-gray-100 rounded"></div>
              </div>
              <div class="space-y-2">
                {#each [1, 2, 3, 4, 5] as _row}
                  <div class="flex items-center gap-3 rounded-[8px] bg-gray-50 px-3 py-2.5">
                    <div class="w-5 h-4 bg-gray-200 rounded"></div>
                    <div class="w-8 h-8 rounded-full bg-gray-200"></div>
                    <div class="flex-1 h-4 bg-gray-200 rounded"></div>
                    <div class="h-4 w-12 bg-gray-100 rounded"></div>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Waitlist section skeleton -->
    <div class="bg-white rounded-[8px] border border-[#f0f0f0] flex flex-col overflow-hidden animate-pulse">
      <div class="px-6 py-5 border-b border-[#f0f0f0] flex items-center gap-3">
        <div class="w-8 h-8 rounded bg-gray-200"></div>
        <div class="h-5 w-32 bg-gray-200 rounded"></div>
      </div>
      <div class="p-6">
        <div class="flex items-center justify-between mb-4">
          <div class="h-4 w-44 bg-gray-200 rounded"></div>
        </div>
        <div class="space-y-2">
          {#each [1, 2, 3, 4, 5] as _row}
            <div class="flex items-center gap-3 rounded-[8px] bg-gray-50 px-3 py-2.5">
              <div class="w-5 h-4 bg-gray-200 rounded"></div>
              <div class="w-8 h-8 rounded-full bg-gray-200"></div>
              <div class="flex-1 h-4 bg-gray-200 rounded"></div>
              <div class="h-4 w-12 bg-gray-100 rounded"></div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {:else}
    <!-- TESTNET GRIDS -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- ASIMOV METRICS CARD -->
      <div
        class="bg-white rounded-[8px] border border-[#f0f0f0] flex flex-col overflow-hidden"
      >
        <!-- Header -->
        <div
          class="px-6 py-5 border-b border-[#f0f0f0] flex items-center justify-between"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-8 h-8 rounded bg-[#eff6ff] text-[#2563eb] flex items-center justify-center"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
                ></path>
              </svg>
            </div>
            <div class="flex flex-col">
              <span
                class="text-[18px] font-medium text-gray-900 font-display leading-none"
                style="letter-spacing: -0.4px;">Asimov</span
              >
              <a
                href={networks.find((n) => n.key === "asimov")?.explorer_url ||
                  "https://explorer.testnet-chain.genlayer.com/"}
                target="_blank"
                rel="noopener noreferrer"
                class="text-[12px] text-gray-500 hover:text-[#2563eb] transition-colors mt-1 hover:underline flex items-center gap-1"
              >
                Explorer
                <svg
                  class="w-3 h-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  /></svg
                >
              </a>
            </div>
          </div>
        </div>

        <div class="p-6 space-y-8 flex-grow">
          <!-- Total Validators Stat -->
          <div
            class="p-5 rounded-[8px] bg-gray-50 border border-[#f0f0f0] flex flex-col gap-1 w-full"
          >
            <span class="text-[12px] text-gray-500 font-medium"
              >Asimov Network</span
            >
            <div class="flex items-baseline gap-2 mt-1">
              <span
                class="text-[32px] font-display font-medium leading-[25px] text-[#2563eb]"
                style="letter-spacing: -0.96px;"
                >{networkStats.asimov.total}</span
              >
              <span class="text-[13px] text-gray-500">Active Validators</span>
            </div>
          </div>

          <!-- Top Leaderboard -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-[14px] font-medium text-gray-900">
                Top Asimov Validators
              </h3>
              <button
                onclick={() => push("/validators/leaderboard")}
                class="text-[12px] text-gray-500 hover:text-[#2563eb] transition-colors"
                >Leaderboard →</button
              >
            </div>

            {#if asimovLeaderboard.length === 0}
              <div
                class="bg-gray-50 rounded-[8px] p-8 text-center border border-[#f0f0f0] border-dashed"
              >
                <div
                  class="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3"
                >
                  <svg
                    class="w-6 h-6 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                    ></path>
                  </svg>
                </div>
                <h4 class="text-[14px] font-medium text-gray-900 mb-1">
                  No validators yet
                </h4>
                <p class="text-[13px] text-gray-500">
                  Asimov testnet currently has no active validators.
                </p>
              </div>
            {:else}
              <TopLeaderboard
                showHeader={false}
                category="validator"
                limit={5}
                entries={asimovLeaderboard}
                {loading}
              />
            {/if}
          </div>
        </div>
      </div>

      <!-- BRADBURY METRICS CARD -->
      <div
        class="bg-white rounded-[8px] border border-[#f0f0f0] flex flex-col overflow-hidden"
      >
        <!-- Header -->
        <div
          class="px-6 py-5 border-b border-[#f0f0f0] flex items-center justify-between"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-8 h-8 rounded bg-[#f0f9ff] text-[#0284c7] flex items-center justify-center"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
                ></path>
              </svg>
            </div>
            <div class="flex flex-col">
              <span
                class="text-[18px] font-medium text-gray-900 font-display leading-none"
                style="letter-spacing: -0.4px;">Bradbury</span
              >
              <a
                href={networks.find((n) => n.key === "bradbury")
                  ?.explorer_url || "https://explorer.testnet-chain.genlayer.com/"}
                target="_blank"
                rel="noopener noreferrer"
                class="text-[12px] text-gray-500 hover:text-[#0284c7] transition-colors mt-1 hover:underline flex items-center gap-1"
              >
                Explorer
                <svg
                  class="w-3 h-3"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  ><path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  /></svg
                >
              </a>
            </div>
          </div>
        </div>

        <div class="p-6 space-y-8 flex-grow">
          <!-- Total Validators Stat -->
          <div
            class="p-5 rounded-[8px] bg-gray-50 border border-[#f0f0f0] flex flex-col gap-1 w-full"
          >
            <span class="text-[12px] text-gray-500 font-medium"
              >Bradbury Network</span
            >
            <div class="flex items-baseline gap-2 mt-1">
              <span
                class="text-[32px] font-display font-medium leading-[25px] text-[#0284c7]"
                style="letter-spacing: -0.96px;"
                >{networkStats.bradbury.total}</span
              >
              <span class="text-[13px] text-gray-500">Active Validators</span>
            </div>
          </div>

          <!-- Top Leaderboard -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-[14px] font-medium text-gray-900">
                Top Bradbury Validators
              </h3>
              <button
                onclick={() => push("/validators/leaderboard")}
                class="text-[12px] text-gray-500 hover:text-[#0284c7] transition-colors"
                >Leaderboard →</button
              >
            </div>

            {#if bradburyLeaderboard.length === 0}
              <div
                class="bg-gray-50 rounded-[8px] p-8 text-center border border-[#f0f0f0] border-dashed"
              >
                <div
                  class="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3"
                >
                  <svg
                    class="w-6 h-6 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    ></path>
                  </svg>
                </div>
                <h4 class="text-[14px] font-medium text-gray-900 mb-1">
                  Coming Soon
                </h4>
                <p class="text-[13px] text-gray-500">
                  Bradbury testnet has no validators actively running yet. Check
                  back soon for the leaderboard!
                </p>
              </div>
            {:else}
              <TopLeaderboard
                showHeader={false}
                category="validator"
                limit={5}
                entries={bradburyLeaderboard}
                {loading}
              />
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- COMMON WAITLIST SECTION -->
    {#if waitlistLeaderboard.length > 0}
      <div
        class="bg-white rounded-[8px] border border-[#f0f0f0] flex flex-col overflow-hidden"
      >
        <!-- Header -->
        <div
          class="px-6 py-5 border-b border-[#f0f0f0] flex items-center justify-between"
        >
          <div class="flex items-center gap-3">
            <div
              class="w-8 h-8 rounded bg-[#eff6ff] text-[#2563eb] flex items-center justify-center"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                ></path>
              </svg>
            </div>
            <span
              class="text-[18px] font-medium text-gray-900 font-display"
              style="letter-spacing: -0.4px;">Race To Testnets</span
            >
          </div>
        </div>
        <div class="p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-[14px] font-medium text-gray-900">
              Top Waitlisted Validators
            </h3>
          </div>
          <TopLeaderboard
            showHeader={false}
            category="validator-waitlist"
            limit={5}
            entries={waitlistLeaderboard}
            {loading}
          />
        </div>
      </div>
    {/if}
  {/if}
</div>
