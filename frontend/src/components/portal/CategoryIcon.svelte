<script>
  let { category = 'genlayer', mode = 'small', size = undefined, hexCategory = undefined, light = false } = $props();

  const hexagonMap = {
    genlayer: '/assets/icons/hexagon-genlayer.svg',
    builder: '/assets/icons/hexagon-builder.svg',
    validator: '/assets/icons/hexagon-validator.svg',
    community: '/assets/icons/hexagon-community.svg',
    steward: '/assets/icons/hexagon-steward.svg',
  };

  const lightHexagonMap = {
    genlayer: '/assets/icons/hexagon-light.svg',
    builder: '/assets/icons/hexagon-builder-light.svg',
    validator: '/assets/icons/hexagon-validator-light.svg',
    community: '/assets/icons/hexagon-community-light.svg',
    steward: '/assets/icons/hexagon-steward-light.svg',
  };

  const whiteIconMap = {
    genlayer: '/assets/icons/gl-symbol-white.svg',
    builder: '/assets/icons/terminal-fill-white.svg',
    validator: '/assets/icons/shield-white.svg',
    community: '/assets/icons/group-white.svg',
    steward: '/assets/icons/seedling-line.svg',
  };

  const blackIconMap = {
    genlayer: '/assets/icons/dashboard-fill-black.svg',
    builder: '/assets/icons/terminal-line.svg',
    validator: '/assets/icons/folder-shield-line.svg',
    community: '/assets/icons/group-3-line.svg',
    steward: '/assets/icons/seedling-line-green.svg',
  };

  const colorMap = {
    genlayer: '#7F52E1',
    builder: '#EE8521',
    validator: '#387DE8',
    community: '#7F52E1',
    steward: '#19A663',
  };

  let hexSize = $derived(size || 48);
  let smallSize = $derived(size || 16);
  let innerIconSize = $derived(Math.round(hexSize * 0.5));
</script>

{#if mode === 'hexagon'}
  <div class="relative flex-shrink-0" style="width: {hexSize}px; height: {hexSize}px;">
    <img src={(light ? lightHexagonMap : hexagonMap)[hexCategory || category]} alt="" class="w-full h-full" />
    {#if light}
      <div
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
        style="width: {innerIconSize}px; height: {innerIconSize}px; background-color: {colorMap[category] || '#7F52E1'}; -webkit-mask-image: url({blackIconMap[category]}); mask-image: url({blackIconMap[category]}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;"
      ></div>
    {:else}
      <img
        src={whiteIconMap[category]}
        alt=""
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
        style="width: {innerIconSize}px; height: {innerIconSize}px;{category === 'steward' ? ' filter: brightness(0) invert(1);' : ''}"
      />
    {/if}
  </div>
{:else}
  <img
    src={blackIconMap[category]}
    alt=""
    class="flex-shrink-0"
    style="width: {smallSize}px; height: {smallSize}px;"
  />
{/if}
