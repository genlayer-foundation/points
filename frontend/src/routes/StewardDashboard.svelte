<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { userStore } from '../lib/userStore.js';
  import { stewardAPI } from '../lib/api.js';
  import { format } from 'date-fns';
  import Avatar from '../components/Avatar.svelte';
  import WorkingGroupsSection from '../components/WorkingGroupsSection.svelte';
  import SectionHeader from '../components/ui/SectionHeader.svelte';
  import CategoryIcon from '../components/portal/CategoryIcon.svelte';

  const pageGradientStyle = [
    'background: radial-gradient(circle at 14% 8%, rgba(25, 166, 99, 0.2) 0%, transparent 30%)',
    'radial-gradient(circle at 82% 12%, rgba(25, 166, 99, 0.12) 0%, transparent 28%)',
    'linear-gradient(180deg, rgba(25, 166, 99, 0.07) 0%, rgba(255, 255, 255, 0) 100%)'
  ].join(', ');

  let stewards = $state([]);
  let stewardsLoading = $state(true);
  let isSteward = $derived($userStore.user?.steward ? true : false);

  let stewardCards = $derived(stewards.filter((steward) => steward.role !== 'Reviewer'));
  let reviewerCards = $derived(stewards.filter((steward) => steward.role === 'Reviewer'));

  onMount(async () => {
    await loadStewards();
  });

  async function loadStewards() {
    try {
      stewardsLoading = true;
      const stewardsRes = await stewardAPI.getStewards();
      stewards = stewardsRes.data || [];
    } catch {
      stewards = [];
    } finally {
      stewardsLoading = false;
    }
  }

  function formatJoined(dateString) {
    if (!dateString) return 'Unknown';
    try {
      return format(new Date(dateString), 'MMM yyyy');
    } catch {
      return 'Unknown';
    }
  }

  function displayName(person) {
    if (person?.name) return person.name;
    if (person?.address) return `${person.address.slice(0, 6)}...${person.address.slice(-4)}`;
    return 'Unnamed steward';
  }

  function avatarUser(person) {
    return { ...person, steward: true };
  }

  function openProfile(person) {
    if (person?.address) {
      push(`/participant/${person.address}`);
    }
  }
</script>

<div class="relative -mx-3 -my-3 min-h-screen overflow-hidden bg-white px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div class="pointer-events-none absolute inset-0">
    <div class="absolute inset-0" style={pageGradientStyle}></div>
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div class="space-y-2">
        <div class="flex items-start gap-3">
          <CategoryIcon category="steward" mode="hexagon" size={44} />
          <h1
            class="steward-heading min-w-0 break-words text-[34px] font-semibold font-display leading-none text-black sm:text-[40px] md:text-[46px]"
            style="letter-spacing: -1px;"
          >
            Steward Dashboard
          </h1>
        </div>
        <p class="max-w-2xl text-[14px] text-[#3f4b5f] sm:text-[15px]" style="letter-spacing: 0.2px;">
          Track contribution review health, steward coverage, and working-group participation.
        </p>
      </div>

      {#if isSteward}
        <button
          type="button"
          onclick={() => push('/stewards/submissions')}
          class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-[8px] border border-[#19A663] bg-[#19A663] px-4 text-[13px] font-semibold text-white shadow-[0_8px_22px_rgba(25,166,99,0.22)] transition-transform hover:-translate-y-0.5 active:scale-[0.96] sm:w-auto"
        >
          Manage submissions
          <img src="/assets/icons/arrow-right-line-white.svg" alt="" class="h-4 w-4" />
        </button>
      {/if}
    </header>

    <section class="glass-panel rounded-[10px] border border-white/70 bg-white/78 p-5 shadow-[0_18px_55px_rgba(38,48,75,0.15)] backdrop-blur-md sm:p-7 md:p-8">
      <SectionHeader
        title="Active Stewards"
        subtitle="Current steward coverage separated by review responsibility."
        showLink={false}
      />

      {#if stewardsLoading}
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 2xl:grid-cols-8">
          {#each [1, 2, 3, 4, 5, 6] as _}
            <div class="h-[154px] animate-pulse rounded-[8px] border border-[#eef1f4] bg-white/80 p-3">
              <div class="mx-auto h-20 w-20 rounded-full bg-gray-200"></div>
              <div class="mx-auto mt-4 h-3 w-24 rounded bg-gray-200"></div>
              <div class="mx-auto mt-2 h-3 w-16 rounded bg-gray-100"></div>
            </div>
          {/each}
        </div>
      {:else if stewards.length === 0}
        <div class="rounded-[8px] border border-dashed border-[#d8f3e4] bg-white/70 p-8 text-center">
          <div class="mx-auto flex w-fit">
            <CategoryIcon category="steward" mode="hexagon" size={54} />
          </div>
          <p class="mt-4 text-sm font-medium text-gray-900">No active stewards found</p>
        </div>
      {:else}
        <div class="space-y-7">
          <div class="space-y-3">
            <div class="flex items-center">
              <h3 class="text-base font-semibold text-gray-950">Stewards</h3>
            </div>

            {#if stewardCards.length === 0}
              <div class="rounded-[8px] border border-[#eef1f4] bg-white/78 p-5 text-sm text-gray-500">No stewards in this section.</div>
            {:else}
              <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 2xl:grid-cols-8">
                {#each stewardCards as steward (steward.id)}
                  <article class="person-card rounded-[8px] bg-white/86">
                    <button
                      type="button"
                      onclick={() => openProfile(steward)}
                      class="block h-full w-full rounded-[8px] p-3 text-center"
                    >
                      <div class="person-avatar-frame steward-avatar-frame mx-auto rounded-full bg-white p-1">
                        <Avatar user={avatarUser(steward)} size="full" clickable={false} />
                      </div>
                      <p class="mt-3 truncate text-sm font-semibold text-gray-950" title={displayName(steward)}>
                        {displayName(steward)}
                      </p>
                      <p class="mt-1 text-xs font-medium text-[#6b7280]">Joined {formatJoined(steward.created_at)}</p>
                    </button>
                  </article>
                {/each}
              </div>
            {/if}
          </div>

          <div class="space-y-3">
            <div class="flex items-center">
              <h3 class="text-base font-semibold text-gray-950">Reviewers</h3>
            </div>

            {#if reviewerCards.length === 0}
              <div class="rounded-[8px] border border-[#eef1f4] bg-white/78 p-5 text-sm text-gray-500">No reviewers in this section.</div>
            {:else}
              <div class="grid grid-cols-3 gap-2.5 sm:grid-cols-4 md:grid-cols-6 xl:grid-cols-10">
                {#each reviewerCards as reviewer (reviewer.id)}
                  <article class="person-card reviewer-card rounded-[8px] bg-white/86">
                    <button
                      type="button"
                      onclick={() => openProfile(reviewer)}
                      class="block h-full w-full rounded-[8px] p-2 text-center"
                    >
                      <div class="person-avatar-frame reviewer-avatar-frame mx-auto rounded-full bg-white p-0.5">
                        <Avatar user={avatarUser(reviewer)} size="full" clickable={false} />
                      </div>
                      <p class="mt-2 truncate text-[12px] font-semibold leading-4 text-gray-950" title={displayName(reviewer)}>
                        {displayName(reviewer)}
                      </p>
                      <p class="mt-0.5 text-[11px] font-medium leading-4 text-[#6b7280]">Joined {formatJoined(reviewer.created_at)}</p>
                    </button>
                  </article>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    </section>

    <WorkingGroupsSection />
  </div>
</div>

<style>
  .steward-heading {
    text-wrap: balance;
  }

  .glass-panel {
    -webkit-backdrop-filter: blur(12px);
  }

  .person-card {
    box-shadow:
      0 0 0 1px rgba(232, 235, 242, 0.9),
      0 8px 18px rgba(31, 42, 68, 0.06);
    transition-property: transform, box-shadow;
    transition-duration: 160ms;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .person-card:hover {
    transform: translateY(-1px);
    box-shadow:
      0 0 0 1px rgba(216, 243, 228, 0.95),
      0 14px 26px rgba(31, 42, 68, 0.12);
  }

  .person-avatar-frame {
    box-shadow:
      0 0 0 1px rgba(216, 243, 228, 0.9),
      0 8px 18px rgba(25, 166, 99, 0.12);
    transition-property: transform;
    transition-duration: 160ms;
    transition-timing-function: cubic-bezier(0.2, 0, 0, 1);
  }

  .person-card:hover .person-avatar-frame {
    transform: scale(1.02);
  }

  .steward-avatar-frame {
    height: 80px;
    width: 80px;
  }

  .reviewer-avatar-frame {
    height: 54px;
    width: 54px;
  }

  .person-avatar-frame :global(img) {
    outline: 1px solid rgba(0, 0, 0, 0.1);
  }
</style>
