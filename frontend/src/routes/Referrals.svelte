<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import Avatar from '../components/Avatar.svelte';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';
  import { usersAPI } from '../lib/api';
  import { showSuccess } from '../lib/toastStore';

  let referralData = $state(null);
  let loading = $state(true);
  let error = $state(null);
  let searchQuery = $state('');

  let totalReferrals = $derived(referralData?.total_referrals ?? 0);
  let builderReferralPoints = $derived(referralData?.builder_points ?? 0);
  let validatorReferralPoints = $derived(referralData?.validator_points ?? 0);
  let totalReferralPoints = $derived(builderReferralPoints + validatorReferralPoints);

  let filteredReferrals = $derived(
    (() => {
      const list = referralData?.referrals ?? [];
      const q = searchQuery.trim().toLowerCase();
      const filtered = !q
        ? list
        : list.filter((entry) => {
            const name = entry.name?.toLowerCase() || '';
            const address = entry.address?.toLowerCase() || '';
            return name.includes(q) || address.includes(q);
          });
      return filtered
        .slice()
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    })()
  );

  async function fetchReferrals() {
    try {
      loading = true;
      error = null;
      const response = await usersAPI.getReferrals();
      referralData = response.data;
    } catch (err) {
      error = err.message || 'Failed to load referrals';
    } finally {
      loading = false;
    }
  }

  function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function shortAddress(addr) {
    if (!addr) return '';
    return addr.slice(0, 6) + '...' + addr.slice(-4);
  }

  function referralUserObj(referral) {
    return {
      name: referral.name,
      address: referral.address,
      profile_image_url: referral.profile_image_url,
      builder: referral.is_builder,
      validator: referral.is_validator,
    };
  }

  function builderEarned(referral) {
    return Math.round((referral.builder_contribution_points || 0) * 0.1);
  }

  function validatorEarned(referral) {
    return Math.round((referral.validator_contribution_points || 0) * 0.1);
  }

  onMount(() => {
    fetchReferrals();
  });
</script>

<div class="referrals-page">
  <!-- Header -->
  <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
    <div class="flex items-center gap-[10px]">
      <div
        class="relative flex-shrink-0"
        style="width: 32px; height: 32px;"
      >
        <img
          src="/assets/icons/hexagon-genlayer.svg"
          alt=""
          class="w-full h-full"
        />
        <img
          src="/assets/icons/link-m.svg"
          alt=""
          class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 brightness-0 invert"
          style="width: 16px; height: 16px;"
        />
      </div>
      <div>
        <h1
          class="text-[24px] font-semibold text-black"
          style="letter-spacing: 0.4px;"
        >
          My Referrals
        </h1>
        <p class="text-[13px] text-[#999] mt-1">
          People you've brought to the GenLayer ecosystem
        </p>
      </div>
    </div>
    <button
      onclick={() => push('/referral-program')}
      class="flex items-center gap-[4px] text-[12px] font-medium text-black tracking-[0.24px] leading-[16px] hover:opacity-70 transition-opacity self-start sm:self-center"
    >
      Referral Program
      <img
        src="/assets/icons/arrow-right-up-line.svg"
        alt=""
        class="w-4 h-4"
      />
    </button>
  </div>

  {#if loading}
    <!-- Stats skeleton -->
    <div class="flex flex-col md:flex-row gap-4 w-full mb-6">
      {#each [1, 2, 3] as _}
        <div
          class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full animate-pulse"
        >
          <div class="w-[48px] h-[48px] rounded-full bg-gray-200 mr-4 shrink-0"></div>
          <div class="flex flex-col gap-2">
            <div class="h-7 w-16 bg-gray-200 rounded"></div>
            <div class="h-3 w-24 bg-gray-100 rounded"></div>
          </div>
        </div>
      {/each}
    </div>

    <!-- List skeleton -->
    <div class="bg-[#fcfcfc] border border-[#f0f0f0] rounded-[16px] p-[16px]">
      <div class="flex flex-col gap-[6px]">
        {#each [1, 2, 3, 4, 5] as _}
          <div
            class="flex items-center gap-[10px] rounded-[10px] bg-white px-3 py-[14px] animate-pulse"
          >
            <div class="w-8 h-8 rounded-full bg-gray-200"></div>
            <div class="flex-1 h-4 bg-gray-200 rounded"></div>
            <div class="w-20 h-4 bg-gray-100 rounded"></div>
          </div>
        {/each}
      </div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-[12px]">
      <p class="text-sm font-medium">Error loading referrals</p>
      <p class="text-sm mt-1">{error}</p>
    </div>
  {:else if !referralData || referralData.referrals.length === 0}
    <!-- Empty State -->
    <div
      class="bg-[#1a1c1d] w-full rounded-[16px] p-[40px] flex flex-col items-center text-center"
    >
      <div
        class="relative flex-shrink-0 mb-4"
        style="width: 64px; height: 64px;"
      >
        <img
          src="/assets/icons/hexagon-genlayer.svg"
          alt=""
          class="w-full h-full"
        />
        <img
          src="/assets/icons/link-m.svg"
          alt=""
          class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 brightness-0 invert"
          style="width: 32px; height: 32px;"
        />
      </div>
      <h2
        class="font-['Switzer'] font-semibold text-[20px] text-white leading-[25px] tracking-[0.4px] mb-2"
      >
        No referrals yet
      </h2>
      <p
        class="font-['Switzer'] text-[14px] text-[#b0b0b0] leading-[21px] tracking-[0.28px] max-w-[420px]"
      >
        Start inviting builders and validators. For each referred user who
        submits at least one contribution, you receive 10% of the points they
        earn permanently.
      </p>
    </div>
  {:else}
    <!-- Stats Cards -->
    <div class="flex flex-col md:flex-row gap-4 w-full mb-6">
      <!-- Total Referrals -->
      <div
        class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative"
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
            <img
              src="/assets/icons/link-m.svg"
              alt=""
              class="absolute w-5 h-5 brightness-0 invert"
            />
          </div>
          <div
            class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
          >
            <p
              class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
            >
              {totalReferrals}
            </p>
            <p
              class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
            >
              Total Referrals
            </p>
          </div>
        </div>
      </div>

      <!-- Builder Referral Points -->
      <div
        class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative"
      >
        <div class="flex h-full items-center">
          <div
            class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
          >
            <CategoryIcon category="builder" mode="hexagon" size={48} />
          </div>
          <div
            class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
          >
            <p
              class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
            >
              {builderReferralPoints}
            </p>
            <p
              class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
            >
              Builder Referral Points
            </p>
          </div>
        </div>
      </div>

      <!-- Validator Referral Points -->
      <div
        class="bg-white border border-[#f0f0f0] rounded-[16px] flex items-center p-[24px] h-[92px] w-full relative"
      >
        <div class="flex h-full items-center">
          <div
            class="w-[48px] h-[48px] relative flex items-center justify-center mr-4 shrink-0"
          >
            <CategoryIcon category="validator" mode="hexagon" size={48} />
          </div>
          <div
            class="flex flex-col h-full items-start justify-center whitespace-nowrap z-10"
          >
            <p
              class="font-semibold text-[32px] leading-[32px] tracking-[-0.96px] text-black"
            >
              {validatorReferralPoints}
            </p>
            <p
              class="text-[13px] leading-[15px] tracking-[0.24px] text-[#6b6b6b] mt-1"
            >
              Validator Referral Points
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Search + Counter -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-3">
      <p class="text-[13px] text-[#6b6b6b]">
        Showing {searchQuery ? `${filteredReferrals.length} of ` : ''}{referralData.referrals.length} referrals
      </p>
      <div class="relative w-full sm:w-72">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <img src="/assets/icons/search-line.svg" alt="" class="w-4 h-4 opacity-60" />
        </div>
        <input
          bind:value={searchQuery}
          type="search"
          placeholder="Search by name or address"
          class="block w-full pl-9 pr-3 py-2 text-[13px] bg-white border border-[#f0f0f0] rounded-[10px] placeholder-[#999] focus:outline-none focus:border-[#1a1c1d] transition-colors"
        />
      </div>
    </div>

    <!-- Referrals List -->
    <div
      class="bg-[#fcfcfc] border border-[#f0f0f0] rounded-[16px] p-[16px]"
    >
      {#if searchQuery && filteredReferrals.length === 0}
        <div class="text-center py-8 text-[14px] text-[#999]">
          No referrals found matching "{searchQuery}"
        </div>
      {:else}
        <div class="flex flex-col gap-[6px]">
          {#each filteredReferrals as referral}
            <button
              onclick={() => push(`/participant/${referral.address}`)}
              class="flex flex-col sm:flex-row sm:items-center sm:justify-between rounded-[10px] bg-white hover:bg-[#f8f8f8] px-3 py-[14px] transition-colors w-full gap-3 text-left"
            >
              <!-- Participant -->
              <div class="flex items-center gap-[10px] min-w-0 flex-1">
                <Avatar
                  user={referralUserObj(referral)}
                  size="sm"
                  clickable={false}
                />
                <div class="flex flex-col items-start min-w-0">
                  <span
                    class="text-[14px] font-medium text-black truncate max-w-[240px]"
                    style="letter-spacing: 0.2px;"
                  >
                    {referral.name || 'Anonymous'}
                  </span>
                  <span class="text-[12px] text-[#999] leading-[14px]">
                    {shortAddress(referral.address)}
                  </span>
                </div>
              </div>

              <!-- Points earned breakdown -->
              <div class="flex items-center gap-3 flex-shrink-0">
                <div class="flex items-center gap-[6px] min-w-[120px]">
                  <CategoryIcon category="builder" mode="hexagon" size={20} />
                  {#if (referral.builder_contribution_points || 0) > 0}
                    <div class="flex items-center gap-[4px] text-[12px]">
                      <span class="text-[#6b6b6b]"
                        >{(referral.builder_contribution_points || 0).toLocaleString()}</span
                      >
                      <span class="text-[#999]">→</span>
                      <span class="font-medium text-[#ee8521]"
                        >+{builderEarned(referral)}</span
                      >
                    </div>
                  {:else}
                    <span class="text-[12px] text-[#cfcfcf]">—</span>
                  {/if}
                </div>

                <div class="flex items-center gap-[6px] min-w-[120px]">
                  <CategoryIcon category="validator" mode="hexagon" size={20} />
                  {#if (referral.validator_contribution_points || 0) > 0}
                    <div class="flex items-center gap-[4px] text-[12px]">
                      <span class="text-[#6b6b6b]"
                        >{(referral.validator_contribution_points || 0).toLocaleString()}</span
                      >
                      <span class="text-[#999]">→</span>
                      <span class="font-medium text-[#387de8]"
                        >+{validatorEarned(referral)}</span
                      >
                    </div>
                  {:else}
                    <span class="text-[12px] text-[#cfcfcf]">—</span>
                  {/if}
                </div>

                <span
                  class="text-[12px] text-[#999] leading-[14px] hidden md:block min-w-[100px] text-right"
                >
                  Joined {formatDate(referral.created_at)}
                </span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .referrals-page,
  .referrals-page :global(*) {
    font-family:
      "Switzer",
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif;
  }
</style>
