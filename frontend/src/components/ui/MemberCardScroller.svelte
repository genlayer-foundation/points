<script>
  import { push } from 'svelte-spa-router';
  import Avatar from '../Avatar.svelte';
  import CategoryIcon from '../portal/CategoryIcon.svelte';
  import { format } from 'date-fns';

  let { members = [], loading = false, viewAllPath = '' } = $props();

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

  function getAddress(member) {
    return member.address || member.user_address;
  }

  function getJoinDate(member) {
    const dateStr = member.date_joined || member.created_at;
    if (!dateStr) return '';
    try {
      return format(new Date(dateStr), 'MMM yyyy');
    } catch {
      return '';
    }
  }

  function getCategoryType(member) {
    if (member.steward) return 'steward';
    if (member.validator) return 'validator';
    if (member.builder) return 'builder';
    return 'community';
  }

  function copyAddress(event, member) {
    event.stopPropagation();
    const addr = getAddress(member);
    if (addr) navigator.clipboard.writeText(addr);
  }
</script>

{#if loading}
  <div class="flex gap-[10px] overflow-x-auto" style="-ms-overflow-style: none; scrollbar-width: none;">
    {#each [1, 2, 3, 4, 5, 6, 7, 8] as _}
      <div class="flex items-center flex-shrink-0 border border-[#f5f5f5] rounded-[8px] overflow-clip animate-pulse">
        <div class="w-[56px] h-[80px] flex items-center justify-center">
          <div class="w-10 h-10 rounded-full bg-gray-200"></div>
        </div>
        <div class="flex-1 min-w-0 flex flex-col gap-1 py-2 px-2">
          <div class="h-3.5 bg-gray-200 rounded w-16"></div>
          <div class="h-3.5 bg-gray-100 rounded w-12"></div>
        </div>
      </div>
    {/each}
  </div>
{:else if members.length === 0}
  <div class="text-sm text-gray-500 py-4">No members yet</div>
{:else}
  <div class="flex gap-[10px] overflow-x-auto" style="-ms-overflow-style: none; scrollbar-width: none;">
    {#each members as member}
      <button
        onclick={() => getAddress(member) && push(`/participant/${getAddress(member)}`)}
        class="flex items-center flex-shrink-0 border border-[#f5f5f5] rounded-[8px] overflow-clip hover:border-[#d0d0d0] transition-colors bg-white text-left"
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
        <div class="flex-1 min-w-0 flex flex-col justify-center py-2 px-2">
          <span class="text-[13px] font-medium text-black truncate" style="letter-spacing: 0.28px;">
            {getDisplayName(member)}
          </span>
          {#if getJoinDate(member)}
            <span class="text-[12px] text-[#6b6b6b] truncate" style="letter-spacing: 0.24px;">
              {getJoinDate(member)}
            </span>
          {/if}
        </div>

        <!-- Category hexagon -->
        <div class="pt-[12px] self-start px-2 flex-shrink-0">
          <CategoryIcon category={getCategoryType(member)} mode="hexagon" size={20} />
        </div>
      </button>
    {/each}
  </div>
{/if}
