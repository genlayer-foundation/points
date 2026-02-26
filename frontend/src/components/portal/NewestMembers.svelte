<script>
  import { onMount } from 'svelte';
  import { push } from 'svelte-spa-router';
  import { buildersAPI, validatorsAPI, usersAPI } from '../../lib/api';
  import Avatar from '../Avatar.svelte';
  import { format } from 'date-fns';

  const LIMIT = 14;

  let activeTab = $state('overall');
  let members = $state([]);
  let loading = $state(true);
  let error = $state(null);

  const tabs = [
    { key: 'overall', label: 'Overall' },
    { key: 'builders', label: 'Builders' },
    { key: 'validators', label: 'Validators' },
    { key: 'community', label: 'Community' },
  ];


  async function fetchMembers(tab) {
    loading = true;
    error = null;
    try {
      let response;
      if (tab === 'builders') {
        response = await buildersAPI.getNewestBuilders(LIMIT);
        members = response.data?.results ?? response.data ?? [];
      } else if (tab === 'validators') {
        response = await validatorsAPI.getNewestValidators(LIMIT);
        members = response.data?.results ?? response.data ?? [];
      } else {
        // overall and community: use users API with ordering
        response = await usersAPI.getUsers({ ordering: '-date_joined', page_size: LIMIT });
        const raw = response.data?.results ?? response.data ?? [];
        if (tab === 'community') {
          members = raw.filter(u => !u.builder && !u.validator);
        } else {
          members = raw;
        }
      }
    } catch (err) {
      error = err.message || 'Failed to load members';
      members = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchMembers(activeTab);
  });

  function selectTab(tab) {
    activeTab = tab;
    fetchMembers(tab);
  }

  function getUserObj(member) {
    return {
      name: member.name || member.user_name,
      address: member.address || member.user_address,
      profile_image_url: member.profile_image_url,
      builder: member.builder ?? false,
      validator: member.validator ?? false,
      steward: member.steward ?? false,
      has_validator_waitlist: member.has_validator_waitlist ?? false,
      has_builder_welcome: member.has_builder_welcome ?? false,
    };
  }

  function getDisplayName(member) {
    const name = member.name || member.user_name;
    const addr = member.address || member.user_address;
    if (name) return name.length > 12 ? name.slice(0, 12) + '...' : name;
    if (addr) return addr.slice(0, 6) + '...' + addr.slice(-4);
    return 'Unknown';
  }

  function getJoinDate(member) {
    const dateStr = member.date_joined || member.created_at;
    if (!dateStr) return '';
    try {
      return format(new Date(dateStr), 'd MMM yyyy');
    } catch {
      return '';
    }
  }

  function getAddress(member) {
    return member.address || member.user_address;
  }

  function getTabViewPath(tab) {
    if (tab === 'builders') return '/builders';
    if (tab === 'validators') return '/validators';
    return '/leaderboard';
  }

  // Priority: steward > validator > builder > community
  function getCategoryType(member) {
    if (member.steward) return 'steward';
    if (member.validator) return 'validator';
    if (member.builder) return 'builder';
    return 'community';
  }

  const categoryConfig = {
    steward:   { icon: '/assets/icons/seedling-line.svg',        color: '#19A663', hexagon: '/assets/icons/hexagon-steward-light.svg' },
    validator: { icon: '/assets/icons/folder-shield-line.svg',   color: '#387DE8', hexagon: '/assets/icons/hexagon-validator-light.svg' },
    builder:   { icon: '/assets/icons/terminal-line.svg',        color: '#EE8521', hexagon: '/assets/icons/hexagon-builder-light.svg' },
    community: { icon: '/assets/icons/group-3-line.svg',         color: '#7F52E1', hexagon: '/assets/icons/hexagon-community-light.svg' },
  };
</script>

<div>
  <!-- Header -->
  <div class="flex items-end justify-between mb-4">
    <div>
      <h2 class="text-[20px] font-semibold text-black" style="letter-spacing: 0.4px;">Newest members</h2>
      <p class="text-[14px] text-[#6b6b6b] mt-1" style="letter-spacing: 0.28px;">New</p>

      <!-- Tab pills -->
      <div class="flex border border-[#f7f7f7] p-[4px] rounded-[24px] gap-[8px] mt-2 w-fit">
        {#each tabs as tab}
          <button
            onclick={() => selectTab(tab.key)}
            class="text-[14px] text-black px-[10px] py-[8px] rounded-[18px] transition-colors {activeTab === tab.key ? 'bg-[#f5f5f5]' : ''}"
            style="letter-spacing: 0.28px;"
          >
            {tab.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- View all -->
    <button
      onclick={() => push(getTabViewPath(activeTab))}
      class="flex items-center gap-1 text-[14px] text-[#6b6b6b] hover:text-black transition-colors"
      style="letter-spacing: 0.28px;"
    >
      View all
      <img src="/assets/icons/arrow-right-line.svg" alt="" class="w-4 h-4" />
    </button>
  </div>

  <!-- Content -->
  {#if loading}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 gap-[10px]">
      {#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14] as _}
        <div class="flex items-center border border-[#f0f0f0] rounded-[8px] overflow-clip animate-pulse">
          <div class="w-[56px] h-[80px] flex items-center justify-center flex-shrink-0">
            <div class="w-10 h-10 rounded-full bg-gray-200"></div>
          </div>
          <div class="flex-1 min-w-0 flex flex-col gap-1 py-2">
            <div class="h-3.5 bg-gray-200 rounded w-3/4"></div>
            <div class="h-3.5 bg-gray-100 rounded w-1/2"></div>
          </div>
          <div class="pt-[16px] self-start px-2 flex-shrink-0">
            <div class="w-5 h-5 bg-gray-100 rounded-full"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="text-sm text-gray-500 py-4">Could not load members</div>
  {:else if members.length === 0}
    <div class="text-sm text-gray-500 py-4">No members yet</div>
  {:else}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-7 gap-[10px]">
      {#each members as member}
        <button
          onclick={() => getAddress(member) && push(`/participant/${getAddress(member)}`)}
          class="flex items-center border border-[#f0f0f0] rounded-[8px] overflow-clip hover:border-[#d0d0d0] transition-colors bg-white text-left"
        >
          <!-- Avatar container -->
          <div class="w-[56px] h-[80px] flex items-center justify-center flex-shrink-0">
            <Avatar
              user={getUserObj(member)}
              size="md"
              showBorder={false}
              clickable={false}
            />
          </div>

          <!-- Name & date -->
          <div class="flex-1 min-w-0 flex flex-col justify-center py-2">
            <span class="text-[13px] font-medium text-black truncate" style="letter-spacing: 0.28px;">
              {getDisplayName(member)}
            </span>
            {#if getJoinDate(member)}
              <span class="text-[12px] text-[#6b6b6b] truncate" style="letter-spacing: 0.24px;">
                {getJoinDate(member)}
              </span>
            {/if}
          </div>

          <!-- Category label: tinted hexagon + colored icon -->
          <div class="pt-[12px] self-start px-2 flex-shrink-0">
            <div class="relative w-5 h-5">
              <img src={categoryConfig[getCategoryType(member)].hexagon} alt="" class="w-full h-full" />
              <div
                class="absolute inset-0 m-auto w-2.5 h-2.5"
                style="background-color: {categoryConfig[getCategoryType(member)].color}; -webkit-mask-image: url({categoryConfig[getCategoryType(member)].icon}); mask-image: url({categoryConfig[getCategoryType(member)].icon}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
              ></div>
            </div>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>
