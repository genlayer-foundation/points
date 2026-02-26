<script>
  let { category = 'genlayer', mode = 'small', size = undefined } = $props();

  const hexagonMap = {
    genlayer: '/assets/icons/hexagon-genlayer.svg',
    builder: '/assets/icons/hexagon-builder.svg',
    validator: '/assets/icons/hexagon-validator.svg',
    community: '/assets/icons/hexagon-community.svg',
  };

  const whiteIconMap = {
    genlayer: '/assets/icons/gl-symbol-white.svg',
    builder: '/assets/icons/terminal-fill-white.svg',
    validator: '/assets/icons/shield-white.svg',
    community: '/assets/icons/group-white.svg',
  };

  const blackIconMap = {
    genlayer: '/assets/icons/dashboard-fill-black.svg',
    builder: '/assets/icons/terminal-line.svg',
    validator: '/assets/icons/folder-shield-line.svg',
    community: '/assets/icons/group-3-line.svg',
  };

  let hexSize = $derived(size || 48);
  let smallSize = $derived(size || 16);
  let innerIconSize = $derived(Math.round(hexSize * 0.5));
</script>

{#if mode === 'hexagon'}
  <div class="relative flex-shrink-0" style="width: {hexSize}px; height: {hexSize}px;">
    <img src={hexagonMap[category]} alt="" class="w-full h-full" />
    <img
      src={whiteIconMap[category]}
      alt=""
      class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
      style="width: {innerIconSize}px; height: {innerIconSize}px;"
    />
  </div>
{:else}
  <img
    src={blackIconMap[category]}
    alt=""
    class="flex-shrink-0"
    style="width: {smallSize}px; height: {smallSize}px;"
  />
{/if}
