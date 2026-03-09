<script lang="ts">
  import { push, querystring } from "svelte-spa-router";
  import { format } from "date-fns";
  import RecentContributions from "../components/RecentContributions.svelte";
  import HighlightedContributions from "../components/HighlightedContributions.svelte";
  import Avatar from "../components/Avatar.svelte";
  import Badge from "../components/Badge.svelte";
  import ContributionCard from "../components/ContributionCard.svelte";
  import ContributionBreakdown from "../components/ContributionBreakdown.svelte";
  import Icons from "../components/Icons.svelte";
  import Tooltip from "../components/Tooltip.svelte";
  import {
    usersAPI,
    statsAPI,
    leaderboardAPI,
    journeyAPI,
    creatorAPI,
    getCurrentUser,
    githubAPI,
    validatorsAPI,
  } from "../lib/api";
  import { authState } from "../lib/auth";
  import { getValidatorBalance } from "../lib/blockchain";
  import { showSuccess, showWarning, showError } from "../lib/toastStore";
  import { parseMarkdown } from "../lib/markdownLoader.js";

  import ProfileHeader from "../components/profile/ProfileHeader.svelte";
  import RankingsWidget from "../components/profile/RankingsWidget.svelte";
  import JourneyActions from "../components/profile/JourneyActions.svelte";
  import ProgressJourney from "../components/profile/ProgressJourney.svelte";
  import RoleView from "../components/profile/RoleView.svelte";
  import StewardView from "../components/profile/StewardView.svelte";
  import CommunityView from "../components/profile/CommunityView.svelte";
  import ReferralBanner from "../components/profile/ReferralBanner.svelte";
  import CategoryIcon from "../components/portal/CategoryIcon.svelte";

  // Import route params from svelte-spa-router
  import { params } from "svelte-spa-router";

  // State management
  let participant: any = $state(null);
  let contributionStats: any = $state({
    totalContributions: 0,
    totalPoints: 0,
    averagePoints: 0,
    contributionTypes: [],
  });
  let validatorStats: any = $state({
    totalContributions: 0,
    totalPoints: 0,
    averagePoints: 0,
    contributionTypes: [],
  });
  let builderStats: any = $state({
    totalContributions: 0,
    totalPoints: 0,
    averagePoints: 0,
    contributionTypes: [],
  });
  let isValidatorOnly = $state(false);

  let loading = $state(true);
  let error = $state(null);
  let statsError = $state(null);
  let balance = $state(null);
  let testnetBalance = $state(null);
  let loadingBalance = $state(false);
  let hasDeployedContract = $state(false);
  let isRefreshingBalance = $state(false);
  let isClaimingBuilderBadge = $state(false);
  let hasStarredRepo = $state(false);
  let repoToStar = $state("genlayerlabs/genlayer-project-boilerplate");
  let isCheckingRepoStar = $state(false);
  let isCompletingJourney = $state(false);
  let referralData = $state(null);
  let loadingReferrals = $state(false);
  let hasShownStatsErrorToast = $state(false);
  let validatorWallets = $state([]);
  let loadingValidatorWallets = $state(false);
  let referralPoints = $state({ builder_points: 0, validator_points: 0 });
  let contributionStatsLoaded = $state(false);
  let builderStatsLoaded = $state(false);
  let validatorStatsLoaded = $state(false);

  // Check if this is the current user's profile
  let isOwnProfile = $derived(
    $authState.isAuthenticated &&
      participant?.address &&
      $authState.address?.toLowerCase() === participant.address.toLowerCase(),
  );

  // Check if user is in transition (waitlist/welcome)
  let isInTransition = $derived(
    participant?.has_validator_waitlist || participant?.has_builder_welcome,
  );

  // Check if user has any role cards to display
  let hasAnyRole = $derived(
    participant &&
      (participant.steward ||
        participant.validator ||
        participant.builder ||
        participant.creator ||
        participant.has_validator_waitlist ||
        participant.has_builder_welcome),
  );

  let isCreatorOnly = $derived(
    participant?.creator &&
      !participant.steward &&
      !participant.validator &&
      !participant.builder &&
      !participant.has_validator_waitlist &&
      !participant.has_builder_welcome,
  );

  let overallPoints = $derived(
    (builderStats?.totalPoints || 0) +
      (validatorStats?.totalPoints || 0) +
      (referralPoints?.builder_points || 0) +
      (referralPoints?.validator_points || 0),
  );

  $effect(() => {
    const currentParams = $params;

    // Check for success message from profile update
    const savedMessage = sessionStorage.getItem("profileUpdateSuccess");
    if (savedMessage) {
      showSuccess(savedMessage);
      sessionStorage.removeItem("profileUpdateSuccess");
    }

    const builderSuccess = sessionStorage.getItem("builderJourneySuccess");
    if (builderSuccess === "true") {
      showSuccess("Congratulations! 🎉 You are now a GenLayer Builder!");
      sessionStorage.removeItem("builderJourneySuccess");
    }

    if (currentParams && currentParams.address) {
      fetchParticipantData(currentParams.address);
    } else {
      error = "No valid wallet address provided";
      loading = false;
    }
  });

  $effect(() => {
    if (statsError && !loading && !hasShownStatsErrorToast) {
      showWarning(
        "Having trouble connecting to the API. Some data might not display correctly.",
      );
      hasShownStatsErrorToast = true;
    }
  });

  async function refreshBalance() {
    if (!participant?.address) return;
    isRefreshingBalance = true;
    try {
      const result = await getValidatorBalance(participant.address);
      testnetBalance = parseFloat(result.formatted);
    } catch (err) {
      testnetBalance = 0;
    } finally {
      isRefreshingBalance = false;
    }
  }

  async function fetchValidatorWallets() {
    if (loadingValidatorWallets || !participant?.address) return;
    loadingValidatorWallets = true;
    try {
      const response = await validatorsAPI.getValidatorWalletsByUserAddress(
        participant.address,
      );
      validatorWallets = response.data?.wallets || [];
    } catch (err) {
      validatorWallets = [];
    } finally {
      loadingValidatorWallets = false;
    }
  }

  async function claimBuilderWelcome() {
    if (!$authState.isAuthenticated) {
      document.querySelector(".auth-button")?.click();
      return;
    }
    isClaimingBuilderBadge = true;
    try {
      await journeyAPI.startBuilderJourney();
      participant = await getCurrentUser();
      // Wait for the DOM to render the builder journey section, then scroll to it
      requestAnimationFrame(() => {
        setTimeout(() => {
          const el = document.getElementById("builder-journey-section");
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        }, 50);
      });
    } catch (err) {
    } finally {
      isClaimingBuilderBadge = false;
    }
  }

  async function startCreatorJourney() {
    if (!$authState.isAuthenticated) return;
    error = null;
    try {
      const response = await creatorAPI.joinAsCreator();
      if (response.status === 201 || response.status === 200) {
        showSuccess(
          "You are now a Community Member! Start growing the community through referrals.",
        );
        participant = await getCurrentUser();
      }
    } catch (err) {
      error = err.response?.data?.message || "Failed to join the community";
    }
  }

  async function handleGitHubLinked(updatedUser) {
    participant = updatedUser;
  }

  async function checkRepoStar() {
    if (!participant?.github_username) return;
    isCheckingRepoStar = true;
    try {
      const response = await githubAPI.checkStar();
      hasStarredRepo = response.data.has_starred;
      repoToStar =
        response.data.repo || "genlayerlabs/genlayer-project-boilerplate";
    } catch (err) {
      hasStarredRepo = false;
    } finally {
      isCheckingRepoStar = false;
    }
  }

  function openStudio() {
    hasDeployedContract = true;
    window.open("https://studio.genlayer.com", "_blank", "noopener,noreferrer");
  }

  async function refreshBuilderStats() {
    const address = participant?.address;
    if (!address) return;
    try {
      const [statsRes, leaderboardRes] = await Promise.all([
        statsAPI.getUserStats(address, "builder"),
        leaderboardAPI.getLeaderboardEntry(address),
      ]);
      if (statsRes.data) builderStats = statsRes.data;
      if (leaderboardRes.data && Array.isArray(leaderboardRes.data)) {
        participant.leaderboard_entries = leaderboardRes.data;
      }
    } catch (_) {}
  }

  async function completeBuilderJourney() {
    if (!$authState.isAuthenticated || isCompletingJourney) return;
    isCompletingJourney = true;
    try {
      const response = await journeyAPI.completeBuilderJourney();
      if (response.status === 201 || response.status === 200) {
        if (response.data?.user) {
          participant = response.data.user;
        }
        showSuccess("Congratulations! 🎉 You are now a GenLayer Builder!");
        refreshBuilderStats();
      }
    } catch (err) {
      if (err.response?.status === 200) {
        if (err.response.data?.user) participant = err.response.data.user;
        showSuccess("Congratulations! 🎉 You are now a GenLayer Builder!");
        refreshBuilderStats();
      } else if (err.response?.status === 400) {
        showError(
          err.response?.data?.error || "Some requirements are not yet met.",
        );
      } else {
        showError("Something went wrong. Please try again later.");
      }
    } finally {
      isCompletingJourney = false;
    }
  }

  async function fetchParticipantData(participantAddress) {
    try {
      loading = true;
      error = null;
      contributionStatsLoaded = false;
      builderStatsLoaded = false;
      validatorStatsLoaded = false;

      const res = await usersAPI.getUserByAddress(participantAddress);
      participant = res.data;
      loading = false;

      if (participant.address) {
        loadingBalance = true;
        getValidatorBalance(participant.address)
          .then((result) => {
            balance = result;
            testnetBalance = parseFloat(result.formatted);
            loadingBalance = false;
          })
          .catch(() => {
            testnetBalance = 0;
            loadingBalance = false;
          });
      }

      leaderboardAPI
        .getLeaderboardEntry(participantAddress)
        .then((leaderboardRes) => {
          if (leaderboardRes.data && Array.isArray(leaderboardRes.data)) {
            participant.leaderboard_entries = leaderboardRes.data;
            participant.waitlist_entry = leaderboardRes.data.find(
              (entry) => entry.type === "validator-waitlist",
            );
            participant.validator_entry = leaderboardRes.data.find(
              (entry) => entry.type === "validator",
            );
            // Extract referral points from any leaderboard entry (for non-own profiles)
            const ownProfile =
              $authState.isAuthenticated &&
              participant?.address &&
              $authState.address?.toLowerCase() ===
                participant.address.toLowerCase();
            if (!ownProfile) {
              const anyEntry = leaderboardRes.data[0];
              if (anyEntry?.referral_points) {
                referralPoints = anyEntry.referral_points;
              }
            }
          }
        })
        .catch(() => {});

      statsAPI
        .getUserStats(participantAddress)
        .then((statsRes) => {
          if (statsRes.data) contributionStats = statsRes.data;
          contributionStatsLoaded = true;
        })
        .catch((statsErr) => {
          statsError = statsErr.message;
          contributionStatsLoaded = true;
        });

      if (participant.validator || participant.has_validator_waitlist) {
        statsAPI
          .getUserStats(participantAddress, "validator")
          .then((res) => {
            if (res.data) validatorStats = res.data;
            validatorStatsLoaded = true;
          })
          .catch(() => {
            validatorStatsLoaded = true;
          });
      } else {
        validatorStatsLoaded = true;
      }

      if (participant.builder || participant.has_builder_welcome) {
        statsAPI
          .getUserStats(participantAddress, "builder")
          .then((res) => {
            if (res.data) builderStats = res.data;
            builderStatsLoaded = true;
          })
          .catch(() => {
            builderStatsLoaded = true;
          });
      } else {
        builderStatsLoaded = true;
      }

      // Fetch referral points (authenticated endpoint for own profile)
      const isOwn =
        $authState.isAuthenticated &&
        participant?.address &&
        $authState.address?.toLowerCase() === participant.address.toLowerCase();
      if (isOwn) {
        usersAPI
          .getReferralPoints()
          .then((res) => {
            if (res.data) referralPoints = res.data;
          })
          .catch(() => {});
      }

      // Fetch referral data (uses isOwn already computed above)
      if (isOwn) {
        if (!loadingReferrals) {
          loadingReferrals = true;
          usersAPI
            .getReferrals()
            .then((response) => {
              referralData = response.data;
            })
            .catch(() => {
              referralData = null;
            })
            .finally(() => {
              loadingReferrals = false;
            });
        }
      } else if (participant?.referral_details) {
        referralData = participant.referral_details;
      }

      if (participant.validator) fetchValidatorWallets();
    } catch (err) {
      if (err.response && err.response.status === 404) {
        participant = {
          address: participantAddress,
          name: null,
          leaderboard_entry: { total_points: null, rank: null },
          created_at: null,
        };
        isValidatorOnly = true;
        loading = false;
        error = null;
      } else {
        error = err.message || "Failed to load participant data";
        loading = false;
      }
    }
  }

  function formatDate(dateString) {
    try {
      return format(new Date(dateString), "MMM d, yyyy");
    } catch (e) {
      return dateString;
    }
  }

  function formatStake(stakeWei) {
    if (!stakeWei) return "0 GEN";
    try {
      const stake = BigInt(stakeWei);
      const gen = Number(stake / BigInt(10 ** 18));
      return `${gen.toLocaleString()} GEN`;
    } catch {
      return "0 GEN";
    }
  }
</script>

<div class="profile-page">
  {#if loading}
    <!-- ProfileHeader skeleton -->
    <div
      class="bg-white rounded-[16px] overflow-hidden border border-[#f7f7f7] shadow-[0px_4px_12px_rgba(0,0,0,0.02)] mb-6 animate-pulse"
    >
      <div
        class="h-32 md:h-48 bg-gradient-to-r from-gray-200 via-gray-100 to-gray-200"
      ></div>
      <div class="p-[12px]">
        <div class="flex items-center gap-[12px]">
          <div
            class="w-[96px] h-[96px] rounded-full bg-gray-200 flex-shrink-0"
          ></div>
          <div class="flex flex-col gap-[8px]">
            <div class="flex gap-[12px] items-center">
              <div class="h-10 w-48 bg-gray-200 rounded"></div>
              <div class="flex gap-[5px]">
                <div class="w-8 h-8 rounded-full bg-gray-100"></div>
                <div class="w-8 h-8 rounded-full bg-gray-100"></div>
              </div>
            </div>
            <div class="h-4 w-32 bg-gray-100 rounded"></div>
          </div>
        </div>
        <div class="flex items-center justify-between w-full mt-6">
          <div class="flex gap-[8px]">
            <div class="h-7 w-24 bg-gray-100 rounded-[4px]"></div>
            <div class="h-7 w-20 bg-gray-100 rounded-[4px]"></div>
          </div>
          <div class="flex gap-[10px]">
            <div class="h-10 w-28 bg-gray-100 rounded-[6px]"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Stat cards skeleton -->
    <div class="mb-10 mt-6 w-full px-0 mx-0">
      <div class="flex flex-col md:flex-row gap-4 items-center">
        {#each [1, 2, 3] as _}
          <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full animate-pulse"
          >
            <div
              class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
            ></div>
            <div class="flex flex-col gap-2">
              <div class="h-7 w-16 bg-gray-200 rounded"></div>
              <div class="h-3 w-24 bg-gray-100 rounded"></div>
            </div>
          </div>
        {/each}
      </div>
    </div>

    <!-- Rankings skeleton -->
    <div class="mb-10 w-full mt-8">
      <div class="flex items-center justify-between mb-4 animate-pulse">
        <div class="h-5 w-20 bg-gray-200 rounded"></div>
        <div class="h-4 w-16 bg-gray-100 rounded"></div>
      </div>
      <div class="flex flex-col lg:flex-row gap-6">
        <div class="w-full lg:w-1/2 flex flex-col pt-2 min-h-[300px]">
          <div class="flex gap-6 border-b border-[#f0f0f0] mb-4 animate-pulse">
            <div class="h-4 w-16 bg-gray-200 rounded pb-2"></div>
            <div class="h-4 w-16 bg-gray-100 rounded pb-2"></div>
            <div class="h-4 w-20 bg-gray-100 rounded pb-2"></div>
          </div>
          <div
            class="bg-[#fcfcfc] border border-[#f0f0f0] rounded-[16px] p-[16px] animate-pulse"
          >
            <div class="flex flex-col gap-[6px]">
              {#each [1, 2, 3, 4] as _}
                <div
                  class="flex items-center gap-[10px] rounded-[10px] bg-white px-3 py-[10px]"
                >
                  <div class="w-5 h-4 bg-gray-200 rounded"></div>
                  <div class="w-8 h-8 rounded-full bg-gray-200"></div>
                  <div class="flex-1 h-4 bg-gray-200 rounded"></div>
                </div>
              {/each}
            </div>
          </div>
        </div>
        <div class="w-full lg:w-1/2 flex flex-col gap-3 pt-[36px]">
          {#each [1, 2, 3] as _}
            <div
              class="flex items-center justify-between bg-white rounded-[12px] border border-[#f0f0f0] p-5 h-[92px] shadow-sm animate-pulse"
            >
              <div class="flex items-center gap-4">
                <div class="w-[48px] h-[48px] rounded-full bg-gray-200"></div>
                <div class="flex flex-col gap-2">
                  <div class="h-6 w-14 bg-gray-200 rounded"></div>
                  <div class="h-3 w-24 bg-gray-100 rounded"></div>
                </div>
              </div>
              <div class="h-3 w-16 bg-gray-100 rounded self-start mt-1"></div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
      {error}
    </div>
  {:else if participant}
    <ProfileHeader {participant} {isOwnProfile} />

    {#if !isValidatorOnly}
      <div class="mb-10 mt-6 w-full px-0 mx-0">
        <div class="flex flex-col md:flex-row gap-4 items-center">
          <!-- Overall Points Card -->
          <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center justify-between p-[24px] h-[92px] w-full relative overflow-hidden"
          >
            {#if !contributionStatsLoaded}
              <div class="flex h-full items-center animate-pulse">
                <div
                  class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                ></div>
                <div class="flex flex-col gap-2">
                  <div class="h-7 w-16 bg-gray-200 rounded"></div>
                  <div class="h-3 w-20 bg-gray-100 rounded"></div>
                </div>
              </div>
            {:else}
              <div class="flex h-full items-center">
                <div
                  class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                >
                  <CategoryIcon category="genlayer" mode="hexagon" size={48} />
                </div>
                <div
                  class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                >
                  <p
                    class="font-medium text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                  >
                    {overallPoints}
                  </p>
                  <p
                    class="text-[14px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                  >
                    All Points
                  </p>
                </div>
              </div>
            {/if}
          </div>

          <!-- Total Contributions Card -->
          <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center justify-between p-[24px] h-[92px] w-full relative overflow-hidden"
          >
            {#if !contributionStatsLoaded}
              <div class="flex h-full items-center animate-pulse">
                <div
                  class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"
                ></div>
                <div class="flex flex-col gap-2">
                  <div class="h-7 w-16 bg-gray-200 rounded"></div>
                  <div class="h-3 w-28 bg-gray-100 rounded"></div>
                </div>
              </div>
            {:else}
              <div class="flex h-full items-center">
                <div
                  class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
                >
                  <img
                    src="/assets/icons/hexagon-genlayer.svg"
                    alt=""
                    class="w-full h-full"
                  />
                  <svg
                    class="absolute w-5 h-5 z-10 brightness-0 invert"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    ><path
                      d="M21 8V20.9932C21 21.5501 20.5552 22 20.0066 22H3.9934C3.44495 22 3 21.556 3 21.0082V2.9918C3 2.44405 3.44476 2 3.9934 2H14.9968L21 8ZM19 9H14V4H5V20H19V9Z"
                    /></svg
                  >
                </div>
                <div
                  class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
                >
                  <p
                    class="font-medium text-[32px] leading-[32px] tracking-[-0.96px] text-black"
                  >
                    {contributionStats.totalContributions || 0}
                  </p>
                  <p
                    class="text-[14px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                  >
                    Total Contributions
                  </p>
                </div>
              </div>
            {/if}
          </div>

          <!-- Date Joined Card -->
          <div
            class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center justify-between p-[24px] h-[92px] w-full relative overflow-hidden"
          >
            <div class="flex h-full items-center">
              <div
                class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
              >
                <img
                  src="/assets/icons/hexagon-genlayer.svg"
                  alt=""
                  class="w-full h-full"
                />
                <svg
                  class="absolute w-5 h-5 z-10 brightness-0 invert"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  ><path
                    d="M17 3H21C21.5523 3 22 3.44772 22 4V20C22 20.5523 21.5523 21 21 21H3C2.44772 21 2 20.5523 2 20V4C2 3.44772 2.44772 3 3 3H7V1H9V3H15V1H17V3ZM4 9V19H20V9H4ZM6 11H8V13H6V11ZM11 11H13V13H11V11ZM16 11H18V13H16V11Z"
                  /></svg
                >
              </div>
              <div
                class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
              >
                <p
                  class="font-medium text-[26px] leading-[32px] tracking-[-0.96px] text-black"
                >
                  {participant.created_at
                    ? formatDate(participant.created_at)
                    : "Oct, 2024"}
                </p>
                <p
                  class="text-[14px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
                >
                  Date joined
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-10 w-full">
        <RankingsWidget
          {participant}
          {isOwnProfile}
          {builderStats}
          {validatorStats}
          {overallPoints}
          {referralPoints}
        />
      </div>

      <!-- Steward Section -->
      {#if participant?.steward || participant?.working_groups?.length > 0}
        <div class="w-full mb-16 pt-10 border-t border-gray-100 mt-10">
          <StewardView {participant} />
        </div>
      {/if}

      <!-- Builder Section -->
      {#if participant?.builder}
        <div class="w-full mb-16 pt-10 border-t border-gray-100 mt-10">
          <RoleView
            role="builder"
            iconCategory="builder"
            colorTheme="orange"
            {participant}
            stats={{
              points: builderStats.totalPoints,
              contributions: builderStats.totalContributions,
              rank:
                participant.leaderboard_entries?.find(
                  (e) => e.type === "builder",
                )?.rank || "-",
            }}
            {isOwnProfile}
            loading={!builderStatsLoaded}
          />
        </div>
      {:else if participant?.has_builder_welcome && isOwnProfile}
        <div
          id="builder-journey-section"
          class="w-full mb-16 pt-10 border-t border-gray-100 mt-10"
        >
          <div class="w-full flex flex-col items-start mt-8">
            <!-- Header (same as RoleView) -->
            <div class="flex items-center gap-[10px] mb-4">
              <div
                class="relative flex-shrink-0"
                style="width: 32px; height: 32px;"
              >
                <img
                  src="/assets/icons/hexagon-builder-light.svg"
                  alt=""
                  class="w-full h-full"
                />
                <img
                  src="/assets/icons/terminal-line-orange.svg"
                  alt=""
                  class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
                  style="width: 16px; height: 16px;"
                />
              </div>
              <h2
                class="text-[20px] font-semibold text-black"
                style="letter-spacing: 0.4px;"
              >
                Builder Journey
              </h2>
            </div>

            <!-- Progress Journey Steps -->
            <div class="w-full">
              <ProgressJourney
                {testnetBalance}
                hasBuilderWelcome={participant?.has_builder_welcome || false}
                {hasDeployedContract}
                githubUsername={participant?.github_username || ""}
                {hasStarredRepo}
                {repoToStar}
                onClaimBuilderBadge={claimBuilderWelcome}
                {isClaimingBuilderBadge}
                onRefreshBalance={refreshBalance}
                {isRefreshingBalance}
                onGitHubLinked={handleGitHubLinked}
                onCheckRepoStar={checkRepoStar}
                {isCheckingRepoStar}
                onOpenStudio={openStudio}
                onCompleteJourney={completeBuilderJourney}
                {isCompletingJourney}
              />
            </div>
          </div>
        </div>
      {/if}

      {#if participant?.validator || participant?.has_validator_waitlist}
        <div class="w-full mb-16 pt-10 border-t border-gray-100 mt-10">
          <RoleView
            role="validator"
            iconCategory="validator"
            colorTheme="sky"
            {participant}
            stats={{
              points: validatorStats.totalPoints,
              contributions: validatorStats.totalContributions,
              rank:
                participant.leaderboard_entries?.find((e) =>
                  !participant?.validator && participant?.has_validator_waitlist
                    ? e.type === "validator-waitlist"
                    : e.type === "validator",
                )?.rank || "-",
            }}
            {isOwnProfile}
            isWaitlist={!participant?.validator &&
              participant?.has_validator_waitlist}
            loading={!validatorStatsLoaded}
          />
        </div>
      {/if}

      <!-- Community Section -->
      {#if participant?.creator}
        <div class="w-full mb-16 pt-10 border-t border-gray-100 mt-10">
          <CommunityView
            {participant}
            {referralData}
            {referralPoints}
            loading={loadingReferrals}
            {isOwnProfile}
          />
        </div>
      {/if}

      <!-- Footer action steps component -->
      {#if isOwnProfile}
        <div
          class="border-t border-gray-100 pt-10 mt-10 w-full pb-10 journey-actions-section"
        >
          <JourneyActions
            {participant}
            onJoinCommunity={startCreatorJourney}
            onApplyBuilder={claimBuilderWelcome}
          />
        </div>
      {/if}

      <div class="w-full px-0 mx-0">
        <ReferralBanner {participant} {overallPoints} {referralData} />
      </div>
    {/if}
  {:else}
    <div
      class="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded"
    >
      Participant not found
    </div>
  {/if}
</div>

<style>
  :global(.profile-content) {
    background-color: #fafafa;
  }

  .profile-page,
  .profile-page :global(*) {
    font-family:
      "Switzer",
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif;
  }
</style>
