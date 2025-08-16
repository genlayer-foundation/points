<script>
  import GenLayerLogo from '../../components/GenLayerLogo.svelte';
  
  let { 
    size = 'medium',
    effect = 'pulse',
    color = '#00c8ff',
    fullscreen = false,
    message = '',
    class: className = '',
    ...props 
  } = $props();
  
  const sizeMap = {
    small: '30px',
    medium: '60px',
    large: '90px',
    xlarge: '120px'
  };
  
  const effectMap = {
    appear: 'loader-appear',
    rotate: 'loader-rotate',
    pulse: 'loader-pulse',
    bounce: 'loader-bounce',
    spin: 'loader-spin',
    fade: 'loader-fade',
    scale: 'loader-scale',
    shake: 'loader-shake',
    flip: 'loader-flip',
    swing: 'loader-swing',
    wobble: 'loader-wobble',
    blink: 'loader-blink',
    morph: 'loader-morph',
    slide: 'loader-slide',
    zoom: 'loader-zoom',
    heartbeat: 'loader-heartbeat',
    float: 'loader-float',
    jello: 'loader-jello',
    rubberband: 'loader-rubberband',
    glow: 'loader-glow',
    flash: 'loader-flash',
    wiggle: 'loader-wiggle',
    orbit: 'loader-orbit',
    elastic: 'loader-elastic',
    ripple: 'loader-ripple',
    breathe: 'loader-breathe',
    pendulum: 'loader-pendulum',
    spiral: 'loader-spiral',
    stretch: 'loader-stretch',
    neon: 'loader-neon'
  };
  
  $: loaderClass = effectMap[effect] || 'loader-pulse';
  $: loaderSize = sizeMap[size] || sizeMap.medium;
</script>

<div 
  class="loader-wrapper {fullscreen ? 'fullscreen' : ''} {className}"
  {...props}
>
  <div class="loader-content">
    <GenLayerLogo 
      class={loaderClass}
      style="width: {loaderSize}; height: {loaderSize}; fill: {color};"
    />
    {#if message}
      <p class="loader-message">{message}</p>
    {/if}
  </div>
</div>

<style>
  .loader-wrapper {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }
  
  .loader-wrapper.fullscreen {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(5px);
    z-index: 9999;
  }
  
  .loader-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
  }
  
  .loader-message {
    color: #fff;
    margin: 0;
    font-size: 1rem;
    letter-spacing: 1px;
    animation: fadeInOut 2s ease-in-out infinite;
  }
  
  @keyframes fadeInOut {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; }
  }
  
  /* Import all animation effects */
  
  :global(.loader-appear) {
    animation: appear 2s ease-in-out infinite;
  }

  @keyframes appear {
    0%, 100% { opacity: 0; transform: scale(0.5); }
    50% { opacity: 1; transform: scale(1); }
  }

  :global(.loader-rotate) {
    animation: rotate 2s linear infinite;
  }

  @keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  :global(.loader-pulse) {
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.1); opacity: 0.8; }
  }

  :global(.loader-bounce) {
    animation: bounce 1s ease-in-out infinite;
  }

  @keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-20px); }
  }

  :global(.loader-spin) {
    animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg) scale(1); }
    50% { transform: rotate(180deg) scale(0.8); }
    to { transform: rotate(360deg) scale(1); }
  }

  :global(.loader-fade) {
    animation: fade 2s ease-in-out infinite;
  }

  @keyframes fade {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }

  :global(.loader-scale) {
    animation: scale 1.5s ease-in-out infinite;
  }

  @keyframes scale {
    0%, 100% { transform: scale(0.8); }
    50% { transform: scale(1.2); }
  }

  :global(.loader-shake) {
    animation: shake 0.5s ease-in-out infinite;
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-5px); }
    75% { transform: translateX(5px); }
  }

  :global(.loader-flip) {
    animation: flip 2s ease-in-out infinite;
  }

  @keyframes flip {
    0% { transform: perspective(200px) rotateY(0deg); }
    50% { transform: perspective(200px) rotateY(180deg); }
    100% { transform: perspective(200px) rotateY(360deg); }
  }

  :global(.loader-swing) {
    transform-origin: top center;
    animation: swing 2s ease-in-out infinite;
  }

  @keyframes swing {
    0%, 100% { transform: rotate(0deg); }
    20% { transform: rotate(15deg); }
    40% { transform: rotate(-10deg); }
    60% { transform: rotate(5deg); }
    80% { transform: rotate(-5deg); }
  }

  :global(.loader-wobble) {
    animation: wobble 1s ease-in-out infinite;
  }

  @keyframes wobble {
    0%, 100% { transform: translateX(0) rotate(0deg); }
    15% { transform: translateX(-10px) rotate(-5deg); }
    30% { transform: translateX(8px) rotate(3deg); }
    45% { transform: translateX(-6px) rotate(-3deg); }
    60% { transform: translateX(4px) rotate(2deg); }
    75% { transform: translateX(-2px) rotate(-1deg); }
  }

  :global(.loader-blink) {
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
  }

  :global(.loader-morph) {
    animation: morph 2s ease-in-out infinite;
  }

  @keyframes morph {
    0%, 100% { transform: scale(1, 1) skew(0deg); filter: hue-rotate(0deg); }
    25% { transform: scale(1.2, 0.8) skew(5deg); filter: hue-rotate(90deg); }
    50% { transform: scale(0.8, 1.2) skew(-5deg); filter: hue-rotate(180deg); }
    75% { transform: scale(1.1, 0.9) skew(3deg); filter: hue-rotate(270deg); }
  }

  :global(.loader-slide) {
    animation: slide 2s ease-in-out infinite;
  }

  @keyframes slide {
    0%, 100% { transform: translateX(-20px); opacity: 0; }
    50% { transform: translateX(0); opacity: 1; }
  }

  :global(.loader-zoom) {
    animation: zoom 1.5s ease-in-out infinite;
  }

  @keyframes zoom {
    0%, 100% { transform: scale(0); opacity: 0; }
    50% { transform: scale(1); opacity: 1; }
  }

  :global(.loader-heartbeat) {
    animation: heartbeat 1.5s ease-in-out infinite;
  }

  @keyframes heartbeat {
    0%, 100% { transform: scale(1); }
    14% { transform: scale(1.3); }
    28% { transform: scale(1); }
    42% { transform: scale(1.3); }
    70% { transform: scale(1); }
  }

  :global(.loader-float) {
    animation: float 3s ease-in-out infinite;
  }

  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-15px); }
  }

  :global(.loader-jello) {
    animation: jello 1s ease-in-out infinite;
  }

  @keyframes jello {
    0%, 100% { transform: skewX(0deg) skewY(0deg); }
    30% { transform: skewX(-12.5deg) skewY(-12.5deg); }
    40% { transform: skewX(6.25deg) skewY(6.25deg); }
    50% { transform: skewX(-3.125deg) skewY(-3.125deg); }
    65% { transform: skewX(1.5625deg) skewY(1.5625deg); }
    75% { transform: skewX(-0.78125deg) skewY(-0.78125deg); }
    85% { transform: skewX(0.390625deg) skewY(0.390625deg); }
    95% { transform: skewX(-0.1953125deg) skewY(-0.1953125deg); }
  }

  :global(.loader-rubberband) {
    animation: rubberBand 1s ease-in-out infinite;
  }

  @keyframes rubberBand {
    0%, 100% { transform: scale(1); }
    30% { transform: scaleX(1.25) scaleY(0.75); }
    40% { transform: scaleX(0.75) scaleY(1.25); }
    60% { transform: scaleX(1.15) scaleY(0.85); }
    70% { transform: scaleX(0.95) scaleY(1.05); }
    80% { transform: scaleX(1.05) scaleY(0.95); }
  }

  :global(.loader-glow) {
    animation: glow 2s ease-in-out infinite;
  }

  @keyframes glow {
    0%, 100% { 
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    50% { 
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
  }

  :global(.loader-flash) {
    animation: flash 2s ease-in-out infinite;
  }

  @keyframes flash {
    0%, 100% { opacity: 1; }
    25%, 75% { opacity: 0; }
    50% { opacity: 1; }
  }

  :global(.loader-wiggle) {
    animation: wiggle 0.8s ease-in-out infinite;
  }

  @keyframes wiggle {
    0%, 100% { transform: rotate(0deg); }
    20% { transform: rotate(8deg); }
    40% { transform: rotate(-8deg); }
    60% { transform: rotate(4deg); }
    80% { transform: rotate(-4deg); }
  }

  :global(.loader-orbit) {
    animation: orbit 3s linear infinite;
  }

  @keyframes orbit {
    from { 
      transform: rotate(0deg) translateX(30px) rotate(0deg);
    }
    to { 
      transform: rotate(360deg) translateX(30px) rotate(-360deg);
    }
  }

  :global(.loader-elastic) {
    animation: elastic 1.5s ease-in-out infinite;
  }

  @keyframes elastic {
    0%, 100% { transform: scale(1); }
    25% { transform: scale(0.9); }
    50% { transform: scale(1.15); }
    75% { transform: scale(0.95); }
  }

  :global(.loader-ripple) {
    position: relative;
    animation: ripple 1.5s ease-out infinite;
  }

  @keyframes ripple {
    0% {
      box-shadow: 0 0 0 0 rgba(0, 200, 255, 0.7);
    }
    70% {
      box-shadow: 0 0 0 20px rgba(0, 200, 255, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(0, 200, 255, 0);
    }
  }

  :global(.loader-breathe) {
    animation: breathe 3s ease-in-out infinite;
  }

  @keyframes breathe {
    0%, 100% { transform: scale(0.95); opacity: 0.7; }
    50% { transform: scale(1.05); opacity: 1; }
  }

  :global(.loader-pendulum) {
    transform-origin: top center;
    animation: pendulum 2s ease-in-out infinite;
  }

  @keyframes pendulum {
    0%, 100% { transform: rotate(30deg); }
    50% { transform: rotate(-30deg); }
  }

  :global(.loader-spiral) {
    animation: spiral 2s ease-in-out infinite;
  }

  @keyframes spiral {
    0% { 
      transform: rotate(0deg) scale(1);
      opacity: 1;
    }
    100% { 
      transform: rotate(720deg) scale(0);
      opacity: 0;
    }
  }

  :global(.loader-stretch) {
    animation: stretch 1.5s ease-in-out infinite;
  }

  @keyframes stretch {
    0%, 100% { transform: scaleY(1); }
    50% { transform: scaleY(1.5); }
  }

  :global(.loader-neon) {
    animation: neon 1.5s ease-in-out infinite;
  }

  @keyframes neon {
    0%, 100% {
      filter: 
        drop-shadow(0 0 2px #fff)
        drop-shadow(0 0 10px #00c8ff)
        drop-shadow(0 0 20px #00c8ff);
    }
    50% {
      filter: 
        drop-shadow(0 0 5px #fff)
        drop-shadow(0 0 20px #00c8ff)
        drop-shadow(0 0 40px #00c8ff)
        drop-shadow(0 0 60px #00c8ff);
    }
  }
</style>