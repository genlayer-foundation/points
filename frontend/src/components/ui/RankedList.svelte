<script>
  import { push } from 'svelte-spa-router';
  import Avatar from '../Avatar.svelte';

  let { entries = [], loading = false, accentColor = '#3eb359', valueLabel = 'GP', showDelta = true, onRowClick = null } = $props();

  const RANK_OPACITY = [1, 0.85, 0.7, 0.6, 0.5];

  const HEX_PATH = 'M18.5346 0.602886C19.9269 -0.200962 21.6423 -0.200962 23.0346 0.602886L39.3192 10.0048C40.7115 10.8087 41.5692 12.2942 41.5692 13.9019V32.7058C41.5692 34.3135 40.7115 35.799 39.3192 36.6029L23.0346 46.0048C21.6423 46.8087 19.9269 46.8087 18.5346 46.0048L2.25 36.6029C0.857695 35.799 0 34.3135 0 32.7058V13.9019C0 12.2942 0.857695 10.8087 2.25 10.0048L18.5346 0.602886Z';

  const RANK_STYLES = [
    { grad: 'rl_goldGrad', filter: 'rl_goldFilter', textFill: 'white' },
    { grad: 'rl_silverGrad', filter: 'rl_silverFilter', textFill: '#333' },
    { grad: 'rl_bronzeGrad', filter: 'rl_bronzeFilter', textFill: 'white' },
  ];

  function getUserObj(entry) {
    const ud = entry.user_details || {};
    return {
      name: entry.user_name || ud.name || entry.name,
      address: entry.user_address || ud.address || entry.address,
      profile_image_url: entry.profile_image_url || ud.profile_image_url,
      builder: entry.builder ?? false,
      validator: entry.validator ?? false,
      steward: entry.steward ?? false,
      has_validator_waitlist: entry.has_validator_waitlist ?? false,
      has_builder_welcome: entry.has_builder_welcome ?? false,
    };
  }

  function getDisplayName(entry) {
    const ud = entry.user_details || {};
    const name = entry.user_name || ud.name || entry.name;
    const addr = entry.user_address || ud.address || entry.address;
    if (name) return name.length > 14 ? name.slice(0, 14) + '...' : name;
    if (addr) return addr.slice(0, 6) + '...' + addr.slice(-4);
    return 'Unknown';
  }

  function getAddress(entry) {
    const ud = entry.user_details || {};
    return entry.user_address || ud.address || entry.address;
  }

  function formatPoints(pts) {
    if (pts == null) return '\u2014';
    if (pts >= 1000000) return (pts / 1000000).toFixed(1) + 'M';
    if (pts >= 1000) return (pts / 1000).toFixed(1) + 'K';
    return pts.toString();
  }

  function handleRowClick(entry) {
    if (onRowClick) {
      onRowClick(entry);
    } else {
      const addr = getAddress(entry);
      if (addr) push(`/participant/${addr}`);
    }
  }
</script>

<!-- Hidden SVG defs for rank hexagon filters & gradients -->
<svg class="absolute w-0 h-0 overflow-hidden" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Gold -->
    <filter id="rl_goldFilter" x="-0.375" y="-0.375" width="42.3192" height="47.3577" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feFlood flood-opacity="0" result="bg"/>
      <feBlend mode="normal" in="SourceGraphic" in2="bg" result="shape"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="-0.375" dy="-0.375"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.15 0"/>
      <feBlend mode="lighten" in2="shape" result="e1"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="-0.1875" dy="-0.1875"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
      <feBlend mode="overlay" in2="e1" result="e2"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="0.375" dy="0.375"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.5 0"/>
      <feBlend mode="lighten" in2="e2" result="e3"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="0.1875" dy="0.1875"/>
      <feGaussianBlur stdDeviation="0.75"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
      <feBlend mode="overlay" in2="e3" result="e4"/>
    </filter>
    <linearGradient id="rl_goldGrad" x1="-3.15112" y1="-0.696152" x2="44.8489" y2="47.3039" gradientUnits="userSpaceOnUse">
      <stop offset="0.15" stop-color="#F8B93D"/>
      <stop offset="0.5" stop-color="#EE8D24"/>
      <stop offset="0.85" stop-color="#DB6917"/>
    </linearGradient>

    <!-- Silver -->
    <filter id="rl_silverFilter" x="-0.375" y="-0.375" width="42.3192" height="47.3577" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feFlood flood-opacity="0" result="bg"/>
      <feBlend mode="normal" in="SourceGraphic" in2="bg" result="shape"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="-0.375" dy="-0.375"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.3 0"/>
      <feBlend mode="lighten" in2="shape" result="e1"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="0.375" dy="0.375"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.04 0"/>
      <feBlend mode="normal" in2="e1" result="e2"/>
    </filter>
    <linearGradient id="rl_silverGrad" x1="-3.15112" y1="-0.696152" x2="44.8489" y2="47.3039" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#f7f7f7"/>
      <stop offset="1" stop-color="#eeeeee"/>
    </linearGradient>

    <!-- Bronze -->
    <filter id="rl_bronzeFilter" x="-0.375" y="-0.375" width="42.3192" height="47.3577" filterUnits="userSpaceOnUse" color-interpolation-filters="sRGB">
      <feFlood flood-opacity="0" result="bg"/>
      <feBlend mode="normal" in="SourceGraphic" in2="bg" result="shape"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="-0.375" dy="-0.375"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.15 0"/>
      <feBlend mode="lighten" in2="shape" result="e1"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="-0.1875" dy="-0.1875"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
      <feBlend mode="overlay" in2="e1" result="e2"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="0.375" dy="0.375"/>
      <feGaussianBlur stdDeviation="0.375"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 0.5 0"/>
      <feBlend mode="lighten" in2="e2" result="e3"/>
      <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
      <feOffset dx="0.1875" dy="0.1875"/>
      <feGaussianBlur stdDeviation="0.75"/>
      <feComposite in2="hardAlpha" operator="arithmetic" k2="-1" k3="1"/>
      <feColorMatrix type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.25 0"/>
      <feBlend mode="overlay" in2="e3" result="e4"/>
    </filter>
    <linearGradient id="rl_bronzeGrad" x1="-3.15112" y1="-0.696152" x2="44.8489" y2="47.3039" gradientUnits="userSpaceOnUse">
      <stop offset="0.15" stop-color="#E8C6A0"/>
      <stop offset="0.5" stop-color="#C9956B"/>
      <stop offset="0.85" stop-color="#A8714A"/>
    </linearGradient>
  </defs>
</svg>

<div class="bg-white border border-[#f7f7f7] rounded-[8px] overflow-clip p-[16px]">
  {#if loading}
    <div class="flex flex-col gap-[4px] animate-pulse">
      {#each [1, 2, 3, 4, 5] as _}
        <div class="h-[48px] flex items-center justify-between">
          <div class="flex items-center gap-[12px]">
            <div class="w-[20px] flex justify-center"><div class="w-4 h-5 rounded bg-gray-200"></div></div>
            <div class="flex items-center gap-[8px]">
              <div class="w-[40px] h-[40px] rounded-full bg-gray-200"></div>
              <div class="h-4 w-20 rounded bg-gray-100"></div>
            </div>
          </div>
          <div class="h-4 w-12 rounded bg-gray-100"></div>
        </div>
      {/each}
    </div>
  {:else if entries.length === 0}
    <div class="py-6 text-center text-sm text-[#6b6b6b]">No data</div>
  {:else}
    <div class="flex flex-col gap-[4px]">
      {#each entries as entry, i}
        <div class="flex items-center justify-between h-[48px]">
          <!-- Left: rank + avatar + name -->
          <button
            onclick={() => handleRowClick(entry)}
            class="flex items-center gap-[12px] hover:opacity-80 transition-opacity min-w-0"
          >
            <!-- Rank indicator -->
            <div class="w-[20px] flex items-center justify-center shrink-0">
              {#if i < 3}
                {@const rs = RANK_STYLES[i]}
                <svg width="20" height="22" viewBox="0 0 41.5692 46.6077" preserveAspectRatio="xMidYMid meet" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d={HEX_PATH} fill="url(#{rs.grad})" filter="url(#{rs.filter})"/>
                  <text x="20.78" y="23.3" text-anchor="middle" dominant-baseline="central" fill={rs.textFill} font-family="'F37 Lineca', 'Geist', sans-serif" font-size="24" font-weight="600">{i + 1}</text>
                </svg>
              {:else}
                <span class="font-display font-semibold text-[14px] text-[#1a1a1a]" style="opacity: {RANK_OPACITY[i] ?? 0.5};">{i + 1}</span>
              {/if}
            </div>
            <!-- Avatar + name -->
            <div class="flex items-center gap-[8px]">
              <div class="flex rounded-full ring-2 ring-[#f0f0f0]">
                <Avatar user={getUserObj(entry)} size="md" clickable={false} showBorder={false} />
              </div>
              <span class="text-[14px] font-medium text-black" style="letter-spacing: 0.28px;">{getDisplayName(entry)}</span>
            </div>
          </button>

          <!-- Right: points -->
          <div class="flex items-baseline gap-[2px]" style="color: {accentColor};">
            {#if showDelta}
              <svg class="w-4 h-4 self-center" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
              </svg>
            {/if}
            <span class="text-[14px] font-medium" style="letter-spacing: 0.28px;">{formatPoints(entry.total_points ?? entry.points)}</span>
            <span class="text-[12px] font-medium opacity-60" style="letter-spacing: 0.24px;">{valueLabel}</span>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
