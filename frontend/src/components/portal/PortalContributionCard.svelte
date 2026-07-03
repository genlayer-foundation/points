<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';
  import { isHiddenWelcomeContribution } from '../../lib/hiddenContributions.js';

  let { contribution, category = null, height = 180, pathPrefix = '/contribution' } = $props();

  function getCategoryColors(cat) {
    const map = {
      builder: {
        pillBg: 'rgba(238,133,33,0.1)', pillText: '#ee8521',
        tagBorder: '#ee8521', tagText: '#ee8521',
        tintedBg: '#FEF3E2',
      },
      validator: {
        pillBg: 'rgba(56,125,232,0.1)', pillText: '#387DE8',
        tagBorder: '#387DE8', tagText: '#387DE8',
        tintedBg: '#EBF3FE',
      },
      community: {
        pillBg: 'rgba(127,82,225,0.1)', pillText: '#7F52E1',
        tagBorder: '#7F52E1', tagText: '#7F52E1',
        tintedBg: '#F4ECFD',
      },
    };
    return map[cat] || map.validator;
  }

  function formatDate(dateString) {
    if (!dateString) return '';
    try {
      return format(new Date(dateString), 'MMM d, yyyy');
    } catch {
      return dateString;
    }
  }

  let cat = $derived(
    contribution?.contribution_type_details?.category || category || 'validator'
  );
  let colors = $derived(getCategoryColors(cat));
  let typeName = $derived(
    contribution?.contribution_type_name ||
    contribution?.contribution_type_details?.name ||
    'Contribution'
  );
  let typeId = $derived(
    contribution?.contribution_type_details?.id ||
    contribution?.contribution_type ||
    null
  );
  let missionName = $derived(contribution?.mission?.name);
  let displayTitle = $derived(missionName || typeName);
  // frozen_global_points = post-multiplier value; fall back to raw points
  let points = $derived(
    contribution?.frozen_global_points ??
    contribution?.frozen_points ??
    contribution?.points ??
    0
  );
  let user = $derived(
    contribution?.user_details ||
    (contribution?.users && contribution.users[0]) ||
    null
  );
  let hasHighlight = $derived(!!contribution?.highlight);
  let realId = $derived(contribution?.id);
  let isHidden = $derived(isHiddenWelcomeContribution(contribution));

  function handleCardClick(event) {
    if (event.target.closest('button') || event.target.closest('a')) return;
    if (realId) push(`${pathPrefix}/${realId}`);
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleCardClick(event);
    }
  }
</script>

{#if !isHidden}
<div
  class="rounded-[8px] p-4 flex flex-col gap-2 cursor-pointer hover:shadow-md transition-shadow w-full"
  style="background: {hasHighlight ? colors.tintedBg : '#FFFFFF'}; height: {height}px;{hasHighlight ? '' : ' border: 1px solid #f5f5f5;'}"
  onclick={handleCardClick}
  onkeydown={handleKeydown}
  role="link"
  tabindex="0"
>
  <!-- Top row: avatar + username | points pill + (optional) highlight star -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2 min-w-0">
      {#if user?.profile_image_url}
        <img src={user.profile_image_url} alt="" class="w-6 h-6 rounded-full" />
      {:else}
        <div class="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-medium text-gray-500 flex-shrink-0">
          {(user?.name || '?')[0].toUpperCase()}
        </div>
      {/if}
      <button
        class="text-sm font-medium truncate hover:underline"
        style="color: #bbb;"
        onclick={(e) => { e.stopPropagation(); if (user?.address) push(`/participant/${user.address}`); }}
      >
        {user?.name || (user?.address ? `${user.address.slice(0, 6)}...` : 'Anonymous')}
      </button>
    </div>
    <div class="flex items-center gap-2 flex-shrink-0">
      <span
        class="text-xs font-medium px-2 py-0.5 rounded-full"
        style="background: {colors.pillBg}; color: {colors.pillText};"
      >
        {points} pts
      </span>
      {#if hasHighlight}
        <div class="relative w-[32px] h-[32px] flex-shrink-0">
          <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full" />
          <div
            class="absolute inset-0 m-auto w-[16px] h-[16px]"
            style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
          ></div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Middle: title + description -->
  <div class="flex-1 min-h-0 overflow-hidden">
    <h3 class="text-sm font-medium text-black truncate">
      {#if hasHighlight}
        {contribution.highlight.title || displayTitle}
      {:else if contribution?.title}
        {contribution.title}
      {:else}
        {displayTitle}
      {/if}
    </h3>
    <p class="text-xs mt-1 line-clamp-3" style="color: #6b6b6b;">
      {#if hasHighlight}
        {contribution.highlight.description}
      {:else if contribution?.notes}
        {contribution.notes}
      {:else}
        {typeName} contribution
      {/if}
    </p>
  </div>

  <!-- Bottom row: category tag + date -->
  <div class="flex items-center justify-between gap-2">
    <button
      class="text-xs px-2 py-0.5 rounded-full whitespace-nowrap truncate max-w-[70%] hover:opacity-80 transition-opacity"
      style="border: 1px solid {colors.tagBorder}; color: {colors.tagText};"
      onclick={(e) => { e.stopPropagation(); if (typeId) push(`/contribution-type/${typeId}`); }}
    >
      {typeName}
    </button>
    <span class="text-xs whitespace-nowrap" style="color: #bababa;">
      {formatDate(contribution?.contribution_date)}
    </span>
  </div>
</div>
{/if}
