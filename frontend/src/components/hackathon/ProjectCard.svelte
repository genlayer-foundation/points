<script>
  let {
    name,
    builder,
    avatar = '',
    screenshot = null,
    category,
    description = '',
    awardLabel = null,
    links = {},
    variant = 'medium',
  } = $props();

  let heightClass = $derived(
    variant === 'large' ? 'h-[400px]' :
    variant === 'small' ? 'h-[200px]' :
    'aspect-[2/1]'
  );

  // Parse twitter links — supports string, array of strings, or array of {handle, url}
  let twitterLinks = $derived.by(() => {
    if (!links.twitter) return [];
    if (typeof links.twitter === 'string') {
      const handle = links.twitter.replace('https://x.com/', '').replace('https://twitter.com/', '');
      return [{ handle: `@${handle}`, url: links.twitter }];
    }
    if (Array.isArray(links.twitter)) {
      return links.twitter.map(t => {
        if (typeof t === 'string') {
          const handle = t.replace('https://x.com/', '').replace('https://twitter.com/', '');
          return { handle: `@${handle}`, url: t };
        }
        return t;
      });
    }
    return [];
  });

  let showTwitterDropdown = $state(false);

  function toggleTwitterDropdown(e) {
    e.preventDefault();
    e.stopPropagation();
    showTwitterDropdown = !showTwitterDropdown;
  }

  function closeDropdown() {
    showTwitterDropdown = false;
  }

  // Close dropdown on outside click
  $effect(() => {
    if (!showTwitterDropdown) return;
    function handleClick() { showTwitterDropdown = false; }
    // Delay to avoid catching the opening click
    const timer = setTimeout(() => document.addEventListener('click', handleClick), 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClick);
    };
  });

  // Determine card link — prefer website, fall back to project (DoraHacks)
  let cardHref = $derived(links.website || links.project || '#');

  // When avatar and screenshot are the same URL, the image is a logo — display centered on dark bg
  // When they differ, screenshot covers the background and avatar is a small circular logo
  let isLogoOnly = $derived(avatar && screenshot && avatar === screenshot);
  let hasBg = $derived(screenshot && !isLogoOnly);
</script>

<div class="flex flex-col gap-3 w-full">
  <!-- Card Image Area -->
  <a
    href={cardHref}
    target={cardHref !== '#' ? '_blank' : undefined}
    rel={cardHref !== '#' ? 'noopener noreferrer' : undefined}
    class="relative rounded-[8px] overflow-hidden flex items-end justify-between p-4 {heightClass} {hasBg ? 'bg-black' : 'bg-gradient-to-br from-[#1a1a2e] to-[#16213e]'}"
  >
    {#if hasBg}
      <img
        src={screenshot}
        alt={name}
        class="absolute inset-0 w-full h-full object-cover pointer-events-none"
      />
    {:else if isLogoOnly || (!screenshot && avatar)}
      <!-- Logo centered on dark background -->
      <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
        <img
          src={avatar}
          alt={name}
          class="max-w-[50%] max-h-[50%] object-contain opacity-90"
        />
      </div>
    {/if}

    <!-- Left column: category badge + avatar/name -->
    <div class="flex flex-col h-full items-start justify-between relative z-10">
      <!-- Category badge -->
      <div class="backdrop-blur-[10px] bg-white/10 flex items-center p-2 rounded-[4px]">
        <span class="text-[14px] font-medium leading-[16px] text-white whitespace-nowrap">{category}</span>
      </div>

      <!-- Avatar + Name -->
      <div class="flex gap-1 items-center">
        {#if avatar && !isLogoOnly}
          <img src={avatar} alt={builder} class="w-10 h-10 rounded-full object-cover shrink-0" />
        {:else if isLogoOnly}
          <img src={avatar} alt={builder} class="w-10 h-10 rounded-full object-contain bg-white/10 backdrop-blur-sm p-1 shrink-0" />
        {:else}
          <div class="w-10 h-10 rounded-full bg-white/20 shrink-0"></div>
        {/if}
        <div class="flex flex-col justify-center whitespace-nowrap">
          <span class="text-[14px] font-medium leading-[21px] text-white">{name}</span>
          <span class="text-[12px] leading-[15px] text-[#bbb] tracking-[0.24px]">by {builder}</span>
        </div>
      </div>
    </div>

    <!-- Right column: arrow icon -->
    <div class="flex flex-col h-full items-start relative z-10">
      <div class="backdrop-blur-[10px] bg-white/10 flex items-center p-2 rounded-[4px]">
        <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17L17 7M17 7H7M17 7v10" />
        </svg>
      </div>
    </div>
  </a>

  <!-- Award label (honorable mentions only) -->
  {#if awardLabel}
    <div class="flex gap-2.5 items-center">
      <!-- Remix Icon: gift-line -->
      <svg class="w-6 h-6 text-[#6b6b6b] shrink-0" viewBox="0 0 24 24" fill="currentColor">
        <path d="M15 2a4 4 0 0 1 3.464 6.001L23 8v2h-1v10a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V10H1V8l4.536.001A4 4 0 0 1 12 3.355 3.983 3.983 0 0 1 15 2zm-2 10h-2v8h2v-8zm-5 0H5v8h3v-8zm8 0h-3v8h3v-8zM9 4a2 2 0 0 0-.15 3.995L9 8h2V6a2 2 0 0 0-1.697-1.977l-.154-.018L9 4zm6 0a2 2 0 0 0-1.995 1.85L13 6v2h2a2 2 0 0 0 1.995-1.85L17 6a2 2 0 0 0-2-2z" />
      </svg>
      <span class="text-[17px] leading-[28px] text-[#6b6b6b] tracking-[0.34px]">{awardLabel}</span>
    </div>
  {/if}

  <!-- Description (not shown for large/grand winner variant — handled in page layout) -->
  {#if variant !== 'large' && description}
    <p class="text-[17px] leading-[28px] text-[#6b6b6b] tracking-[0.34px]">{description}</p>
  {/if}

  <!-- Action buttons (not shown for large/grand winner variant) -->
  {#if variant !== 'large'}
    <div class="flex gap-2 items-start w-full">
      {#if links.project}
        <a
          href={links.project}
          target="_blank"
          rel="noopener noreferrer"
          class="bg-[#9e4bf6] flex flex-1 gap-2 h-[40px] items-center justify-center px-4 rounded-[20px] text-[14px] font-medium text-white tracking-[0.28px] whitespace-nowrap hover:bg-[#8a3de0] transition-colors"
        >
          View Project
          <!-- Globe icon -->
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" stroke-width="1.5" />
            <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke-width="1.5" />
          </svg>
        </a>
      {/if}
      {#if links.youtube}
        <a
          href={links.youtube}
          target="_blank"
          rel="noopener noreferrer"
          class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors"
        >
          <!-- YouTube icon -->
          <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
            <path d="M21.543 6.498C22 8.28 22 12 22 12s0 3.72-.457 5.502c-.254.985-.997 1.76-1.938 2.022C17.896 20 12 20 12 20s-5.893 0-7.605-.476c-.945-.266-1.687-1.04-1.938-2.022C2 15.72 2 12 2 12s0-3.72.457-5.502c.254-.985.997-1.76 1.938-2.022C6.107 4 12 4 12 4s5.896 0 7.605.476c.945.266 1.687 1.04 1.938 2.022zM10 15.5l6-3.5-6-3.5v7z" />
          </svg>
        </a>
      {/if}
      {#if links.github}
        <a
          href={links.github}
          target="_blank"
          rel="noopener noreferrer"
          class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors"
        >
          <!-- GitHub icon -->
          <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z" />
          </svg>
        </a>
      {/if}
      <!-- Twitter: single link or dropdown for multiple -->
      {#if twitterLinks.length === 1}
        <a
          href={twitterLinks[0].url}
          target="_blank"
          rel="noopener noreferrer"
          class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors"
        >
          <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
          </svg>
        </a>
      {:else if twitterLinks.length > 1}
        <div class="relative">
          <button
            onclick={toggleTwitterDropdown}
            class="bg-[#f5f5f5] flex items-center justify-center rounded-[20px] w-[40px] h-[40px] shrink-0 hover:bg-[#ebebeb] transition-colors cursor-pointer"
          >
            <svg class="w-5 h-5 text-black" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </button>
          {#if showTwitterDropdown}
            <div
              class="absolute bottom-full mb-2 right-0 bg-white border border-[#e8e8e8] rounded-xl shadow-lg overflow-hidden z-50 min-w-[180px] animate-dropdown"
            >
              {#each twitterLinks as tl}
                <a
                  href={tl.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex items-center gap-2.5 px-4 py-2.5 text-[14px] text-[#333] hover:bg-[#f5f5f5] transition-colors"
                >
                  <svg class="w-4 h-4 text-[#666] shrink-0" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                  </svg>
                  {tl.handle}
                </a>
              {/each}
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .animate-dropdown {
    animation: dropdownIn 0.15s ease-out;
    transform-origin: bottom right;
  }

  @keyframes dropdownIn {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(4px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
</style>
