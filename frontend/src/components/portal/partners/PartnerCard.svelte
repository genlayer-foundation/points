<script>
  let { item, showBadge = false } = $props();

  function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 0) return '?';
    if (parts.length === 1) {
      const first = parts[0];
      // For single-word names, use the first 2 characters when they include
      // a digit (e.g. "5ElementsNodes" → "5E"); otherwise just the first.
      return first.length > 1 && /[0-9]/.test(first[0])
        ? (first[0] + first[1]).toUpperCase()
        : first[0].toUpperCase();
    }
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }

  let initials = $derived(getInitials(item.name));

  let isPartner = $derived(item.category === 'partner');
  let isProject = $derived(item.category === 'project');

  // Soft gradients used for the initials fallback when there is no logo.
  // Listed verbatim so Tailwind keeps these classes in the build.
  const FALLBACK_GRADIENTS = [
    'from-indigo-400 to-violet-500',
    'from-sky-400 to-cyan-500',
    'from-emerald-400 to-teal-500',
    'from-rose-400 to-pink-500',
    'from-amber-400 to-orange-500',
    'from-violet-400 to-fuchsia-500',
    'from-blue-400 to-indigo-500',
    'from-teal-400 to-emerald-500',
    'from-fuchsia-400 to-pink-500',
    'from-orange-400 to-rose-500',
  ];

  function pickGradient(name) {
    let h = 0;
    const s = name || '';
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return FALLBACK_GRADIENTS[Math.abs(h) % FALLBACK_GRADIENTS.length];
  }

  let initialsGradient = $derived(pickGradient(item.name));

  // Partners and validators share the smaller circle so the visual rhythm
  // matches; projects keep the larger circle since their hero images benefit
  // from extra room.
  let outerPad = $derived(isProject ? 'p-3' : 'p-4');
  let circleSize = $derived(isProject ? 'w-[72%] h-[72%]' : 'w-3/5 h-3/5');

  let categoryLabel = $derived(
    item.category === 'validator'
      ? 'Validator'
      : item.category === 'project'
        ? 'Project'
        : 'Partner'
  );

  let labelBg = $derived(
    item.category === 'validator'
      ? 'bg-blue-600 text-white'
      : item.category === 'project'
        ? 'bg-orange-500 text-white'
        : 'bg-black text-white'
  );

  // Logo container background — partners get a black circle so brand logos
  // pop, the others sit on a subtle neutral so the round shape stays visible.
  let circleBg = $derived(isPartner ? 'bg-black' : 'bg-[#f4f4f5]');
</script>

<a
  href={item.href}
  target={item.isExternal ? '_blank' : undefined}
  rel={item.isExternal ? 'noopener noreferrer' : undefined}
  title={item.name}
  aria-label={item.name}
  class="group relative aspect-square overflow-hidden rounded-[12px] bg-white border border-[#ececec] transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-transparent hover:shadow-[0_10px_28px_rgba(0,0,0,0.08)]"
>
  {#if showBadge}
    <span
      class="absolute top-2 left-2 z-10 inline-flex items-center px-1.5 py-[2px] rounded text-[9px] font-semibold uppercase {labelBg}"
      style="letter-spacing: 0.4px;"
    >
      {categoryLabel}
    </span>
  {/if}

  <!-- Discrete redirect arrow -->
  <span
    class="absolute top-2 right-2 z-10 inline-flex items-center justify-center w-4 h-4 rounded bg-black/[0.04] opacity-0 group-hover:opacity-100 transition-opacity duration-200"
    aria-hidden="true"
  >
    <img
      src="/assets/icons/arrow-right-up-line.svg"
      alt=""
      class="w-2.5 h-2.5 opacity-50"
    />
  </span>

  <div class="absolute inset-0 flex items-center justify-center {outerPad}">
    {#if item.logo_url}
      <div class="{circleSize} rounded-full {circleBg} flex items-center justify-center overflow-hidden">
        <img
          src={item.logo_url}
          alt=""
          class={isPartner ? 'w-3/4 h-3/4 object-contain' : 'w-full h-full object-cover'}
          loading="lazy"
        />
      </div>
    {:else if isPartner}
      <div class="{circleSize} rounded-full bg-black flex items-center justify-center">
        <span class="text-[24px] font-medium font-display text-white">{initials}</span>
      </div>
    {:else}
      <div
        class="{circleSize} rounded-full bg-gradient-to-br {initialsGradient} flex items-center justify-center text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-2px_4px_rgba(0,0,0,0.08)]"
      >
        <span
          class="{isProject ? 'text-[28px]' : 'text-[22px]'} font-semibold tracking-tight"
          style="text-shadow: 0 1px 2px rgba(0,0,0,0.12);"
        >
          {initials}
        </span>
      </div>
    {/if}
  </div>

  <!-- Frosted name strip slides up on hover -->
  <div
    class="absolute inset-x-0 bottom-0 backdrop-blur-xl bg-black/55 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"
  >
    <div
      class="px-3 py-2 text-[12px] font-medium text-white text-center truncate"
      style="letter-spacing: 0.1px;"
    >
      {item.name}
    </div>
  </div>
</a>
