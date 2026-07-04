<script>
  import { push } from 'svelte-spa-router';
  import { format } from '../../lib/dates.js';
  import Avatar from '../Avatar.svelte';
  import { isHiddenWelcomeContribution } from '../../lib/hiddenContributions.js';
  import { parseMarkdown } from '../../lib/markdownLoader.js';

  let { highlight, height = 180 } = $props();

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

  let category = $derived(highlight?.contribution_type_category || 'validator');
  let colors = $derived(getCategoryColors(category));
  let user = $derived({
    name: highlight?.user_name,
    address: highlight?.user_address,
    profile_image_url: highlight?.user_profile_image_url,
    builder: highlight?.user_builder,
    validator: highlight?.user_validator,
    steward: highlight?.user_steward,
    has_validator_waitlist: highlight?.user_has_validator_waitlist,
    has_builder_welcome: highlight?.user_has_builder_welcome,
  });
  let isHidden = $derived(isHiddenWelcomeContribution(highlight));

  function handleCardClick(event) {
    if (event.target.closest('button') || event.target.closest('a')) return;
    if (highlight?.contribution) {
      push(`/contribution/${highlight.contribution}`);
    }
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
  style="background: {colors.tintedBg}; height: {height}px;"
  onclick={handleCardClick}
  onkeydown={handleKeydown}
  role="link"
  tabindex="0"
>
  <!-- Top: avatar + username | points pill + highlight star -->
  <div class="flex items-center justify-between">
    <div class="flex items-center gap-2 min-w-0">
      <Avatar {user} size="xs" clickable={true} />
      <button
        class="text-sm font-medium text-black truncate hover:underline"
        onclick={(e) => { e.stopPropagation(); push(`/participant/${user.address || ''}`); }}
      >
        {user.name || (user.address ? `${user.address.slice(0, 6)}...${user.address.slice(-4)}` : 'Anonymous')}
      </button>
    </div>
    <div class="flex items-center gap-2 flex-shrink-0">
      <span
        class="text-xs font-medium px-2 py-0.5 rounded-full"
        style="background: {colors.pillBg}; color: {colors.pillText};"
      >
        {highlight.contribution_points} pts
      </span>
      <div class="relative w-[32px] h-[32px] flex-shrink-0">
        <img src="/assets/icons/hexagon-highlight.svg" alt="" class="w-full h-full" />
        <div
          class="absolute inset-0 m-auto w-[16px] h-[16px]"
          style="background-color: #FFFFFF; -webkit-mask-image: url(/assets/icons/star-line.svg); mask-image: url(/assets/icons/star-line.svg); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
        ></div>
      </div>
    </div>
  </div>

  <!-- Middle: title + description -->
  <div class="flex-1 min-h-0 overflow-hidden">
    <h3 class="text-sm font-medium text-black truncate">
      {highlight.title || highlight.contribution_type_name || 'Contribution'}
    </h3>
    {#if highlight.description}
      <div class="markdown-content text-xs mt-1 line-clamp-3" style="color: #6b6b6b;">
        {@html parseMarkdown(highlight.description)}
      </div>
    {/if}
  </div>

  <!-- Bottom row: category tag + date -->
  <div class="flex items-center justify-between gap-2">
    <button
      class="text-xs px-2 py-0.5 rounded-full whitespace-nowrap truncate max-w-[70%] hover:opacity-80 transition-opacity"
      style="border: 1px solid {colors.tagBorder}; color: {colors.tagText};"
      onclick={(e) => { e.stopPropagation(); push(`/contribution-type/${highlight.contribution_type}`); }}
    >
      {highlight.contribution_type_name || 'Contribution'}
    </button>
    <span class="text-xs whitespace-nowrap" style="color: #bababa;">
      {formatDate(highlight.contribution_date)}
    </span>
  </div>
</div>
{/if}

<style>
  .markdown-content :global(p) {
    margin: 0;
  }
  .markdown-content :global(ul),
  .markdown-content :global(ol) {
    margin: 0;
    padding-left: 1.25rem;
  }
  .line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
</style>
