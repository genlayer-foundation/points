<script>
  let { item } = $props();

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
  let isValidator = $derived(item.category === 'validator');

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

  let fallbackGradient = $derived(
    isProject
      ? 'from-orange-400 to-orange-600'
      : isValidator
        ? 'from-[#65b7ff] to-[#6c55ff]'
        : initialsGradient
  );
</script>

<a
  href={item.href}
  target={item.isExternal ? '_blank' : undefined}
  rel={item.isExternal ? 'noopener noreferrer' : undefined}
  title={item.name}
  aria-label={item.name}
  class="group flex h-[92px] min-w-0 items-center gap-4 rounded-[8px] border border-[#e8ebf2] bg-white px-4 shadow-[0_8px_18px_rgba(31,42,68,0.07)] outline-none transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2"
>
  <div class="flex h-[58px] w-[58px] flex-shrink-0 items-center justify-center">
    {#if item.logo_url}
      {#if isPartner}
        <div class="flex h-[58px] w-[58px] items-center justify-center rounded-[8px] bg-black p-2.5">
          <img
            src={item.logo_url}
            alt=""
            class="w-full h-full object-contain"
            loading="lazy"
          />
        </div>
      {:else}
        <img
          src={item.logo_url}
          alt=""
          class="h-[58px] w-[58px] rounded-[8px] object-cover"
          loading="lazy"
        />
      {/if}
    {:else if isPartner}
      <div class="flex h-[58px] w-[58px] items-center justify-center rounded-[8px] bg-black">
        <span class="text-[18px] font-medium font-display text-white">{initials}</span>
      </div>
    {:else}
      <div
        class="flex h-[58px] w-[58px] items-center justify-center rounded-[8px] bg-gradient-to-br {fallbackGradient} text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-2px_4px_rgba(0,0,0,0.08)]"
      >
        <span
          class="text-[20px] font-semibold tracking-tight"
          style="text-shadow: 0 1px 2px rgba(0,0,0,0.12);"
        >
          {initials}
        </span>
      </div>
    {/if}
  </div>

  <div
    class="min-w-0 flex-1 text-left text-[14px] font-semibold leading-snug text-[#111827] transition-colors group-hover:text-black group-focus-visible:text-black"
    style="letter-spacing: 0;"
  >
    <span
      class="block overflow-hidden"
      style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;"
    >
      {item.name}
    </span>
  </div>
</a>
