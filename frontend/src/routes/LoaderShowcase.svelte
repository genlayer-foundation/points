<script>
  import GenLayerLogo from '../components/GenLayerLogo.svelte';
  import SequenceLoader from '../components/SequenceLoader.svelte';
  
  const loaderEffects = [
    { name: 'Appear', class: 'loader-appear' },
    { name: 'Disappear', class: 'loader-disappear' },
    { name: 'Rotate', class: 'loader-rotate' },
    { name: 'Pulse', class: 'loader-pulse' },
    { name: 'Bounce', class: 'loader-bounce' },
    { name: 'Spin', class: 'loader-spin' },
    { name: 'Fade', class: 'loader-fade' },
    { name: 'Scale', class: 'loader-scale' },
    { name: 'Shake', class: 'loader-shake' },
    { name: 'Flip', class: 'loader-flip' },
    { name: 'Swing', class: 'loader-swing' },
    { name: 'Wobble', class: 'loader-wobble' },
    { name: 'Blink', class: 'loader-blink' },
    { name: 'Morph', class: 'loader-morph' },
    { name: 'Slide', class: 'loader-slide' },
    { name: 'Zoom', class: 'loader-zoom' },
    { name: 'Heartbeat', class: 'loader-heartbeat' },
    { name: 'Float', class: 'loader-float' },
    { name: 'Jello', class: 'loader-jello' },
    { name: 'RubberBand', class: 'loader-rubberband' },
    { name: 'Glow', class: 'loader-glow' },
    { name: 'Flash', class: 'loader-flash' },
    { name: 'Wiggle', class: 'loader-wiggle' },
    { name: 'Orbit', class: 'loader-orbit' },
    { name: 'Elastic', class: 'loader-elastic' },
    { name: 'Ripple', class: 'loader-ripple' },
    { name: 'Breathe', class: 'loader-breathe' },
    { name: 'Pendulum', class: 'loader-pendulum' },
    { name: 'Spiral', class: 'loader-spiral' },
    { name: 'Stretch', class: 'loader-stretch' },
    { name: 'Neon', class: 'loader-neon' },
    { name: 'AppearGlowFlip', class: 'loader-appearglowflip' },
    { name: 'Sequence Demo', component: 'sequence' }
  ];
  
  // Custom sequence for the demo
  const customSequence = [
    { effect: 'appear', duration: 300 },
    { effect: 'glow', duration: 400, repeat: 4 },
    { effect: 'flip', duration: 500 },
    { effect: 'glow', duration: 400, repeat: 4 },
    { effect: 'disappear', duration: 300 },
    { effect: 'wait', duration: 500 } // pause before restart
  ];
</script>

<div class="loader-showcase">
  <h1>GenLayer Loader Effects Showcase</h1>
  
  <div class="effects-grid">
    {#each loaderEffects as effect}
      <div class="effect-card">
        <div class="loader-container">
          {#if effect.component === 'sequence'}
            <SequenceLoader sequence={customSequence} />
          {:else}
            <GenLayerLogo class={effect.class} />
          {/if}
        </div>
        <h3>{effect.name}</h3>
      </div>
    {/each}
  </div>
</div>

<style>
  .loader-showcase {
    min-height: 100vh;
    padding: 2rem;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
  }

  h1 {
    text-align: center;
    color: #fff;
    margin-bottom: 3rem;
    font-size: 2.5rem;
    font-weight: 300;
    letter-spacing: 2px;
  }

  .effects-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }

  .effect-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
  }

  .effect-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(0, 200, 255, 0.3);
  }

  .loader-container {
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1rem;
  }

  .loader-container :global(svg) {
    width: 60px;
    height: 60px;
    fill: #00c8ff;
  }

  h3 {
    color: #fff;
    margin: 0;
    font-size: 1rem;
    font-weight: 400;
    letter-spacing: 1px;
  }

  /* Animation Effects */
  
  :global(.loader-appear) {
    animation: appear 2s ease-in-out infinite;
  }

  @keyframes appear {
    0%, 20% { opacity: 0; transform: scale(0.5); }
    40%, 100% { opacity: 1; transform: scale(1); }
  }

  :global(.loader-disappear) {
    animation: disappear 2s ease-in-out infinite;
  }

  @keyframes disappear {
    0%, 60% { opacity: 1; transform: scale(1); }
    80%, 100% { opacity: 0; transform: scale(0.5); }
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
    0% { transform: rotateY(0deg); }
    50% { transform: rotateY(90deg); }
    100% { transform: rotateY(0deg); }
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

  /* Separated Part Animations */
  
  :global(.loader-assemble .logo-center) {
    animation: assembleCenter 3s ease-out infinite;
  }
  
  :global(.loader-assemble .logo-left) {
    animation: assembleLeft 3s ease-out infinite;
  }
  
  :global(.loader-assemble .logo-right) {
    animation: assembleRight 3s ease-out infinite;
  }

  @keyframes assembleCenter {
    0%, 20% {
      transform: scale(0) rotate(180deg);
      opacity: 0;
    }
    40%, 85% {
      transform: scale(1) rotate(0deg);
      opacity: 1;
    }
    95%, 100% {
      transform: scale(0) rotate(-180deg);
      opacity: 0;
    }
  }

  @keyframes assembleLeft {
    0%, 40% {
      transform: translateX(-80px) translateY(-20px) rotate(45deg) scale(0.5);
      opacity: 0;
    }
    60%, 85% {
      transform: translateX(0) translateY(0) rotate(0deg) scale(1);
      opacity: 1;
    }
    95%, 100% {
      transform: translateX(-80px) translateY(-20px) rotate(45deg) scale(0.5);
      opacity: 0;
    }
  }

  @keyframes assembleRight {
    0%, 45% {
      transform: translateX(80px) translateY(-20px) rotate(-45deg) scale(0.5);
      opacity: 0;
    }
    65%, 85% {
      transform: translateX(0) translateY(0) rotate(0deg) scale(1);
      opacity: 1;
    }
    95%, 100% {
      transform: translateX(80px) translateY(-20px) rotate(-45deg) scale(0.5);
      opacity: 0;
    }
  }

  :global(.loader-cascade .logo-center) {
    animation: cascadeCenter 2.5s ease-in-out infinite;
  }
  
  :global(.loader-cascade .logo-left) {
    animation: cascadeLeft 2.5s ease-in-out infinite;
  }
  
  :global(.loader-cascade .logo-right) {
    animation: cascadeRight 2.5s ease-in-out infinite;
  }

  @keyframes cascadeCenter {
    0%, 15% { 
      transform: translateY(-60px) scale(0);
      opacity: 0;
    }
    30%, 70% { 
      transform: translateY(0) scale(1);
      opacity: 1;
    }
    85%, 100% { 
      transform: translateY(60px) scale(0);
      opacity: 0;
    }
  }

  @keyframes cascadeLeft {
    0%, 30% { 
      transform: translateY(-60px) translateX(-40px) scale(0);
      opacity: 0;
    }
    45%, 70% { 
      transform: translateY(0) translateX(0) scale(1);
      opacity: 1;
    }
    85%, 100% { 
      transform: translateY(60px) translateX(-40px) scale(0);
      opacity: 0;
    }
  }

  @keyframes cascadeRight {
    0%, 35% { 
      transform: translateY(-60px) translateX(40px) scale(0);
      opacity: 0;
    }
    50%, 70% { 
      transform: translateY(0) translateX(0) scale(1);
      opacity: 1;
    }
    85%, 100% { 
      transform: translateY(60px) translateX(40px) scale(0);
      opacity: 0;
    }
  }

  :global(.loader-converge .logo-center) {
    animation: convergeCenter 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  }
  
  :global(.loader-converge .logo-left) {
    animation: convergeLeft 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  }
  
  :global(.loader-converge .logo-right) {
    animation: convergeRight 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  }

  @keyframes convergeCenter {
    0%, 10% {
      transform: scale(2) rotate(360deg);
      opacity: 0;
    }
    30%, 70% {
      transform: scale(1) rotate(0deg);
      opacity: 1;
    }
    90%, 100% {
      transform: scale(0) rotate(-360deg);
      opacity: 0;
    }
  }

  @keyframes convergeLeft {
    0%, 25% {
      transform: translateX(-100px) translateY(30px) rotate(-90deg) scale(0);
      opacity: 0;
    }
    50%, 70% {
      transform: translateX(0) translateY(0) rotate(0deg) scale(1);
      opacity: 1;
    }
    90%, 100% {
      transform: translateX(-100px) translateY(30px) rotate(-90deg) scale(0);
      opacity: 0;
    }
  }

  @keyframes convergeRight {
    0%, 30% {
      transform: translateX(100px) translateY(30px) rotate(90deg) scale(0);
      opacity: 0;
    }
    55%, 70% {
      transform: translateX(0) translateY(0) rotate(0deg) scale(1);
      opacity: 1;
    }
    90%, 100% {
      transform: translateX(100px) translateY(30px) rotate(90deg) scale(0);
      opacity: 0;
    }
  }

  :global(.loader-unfold .logo-left) {
    transform-origin: right center;
    animation: unfoldLeft 2s ease-in-out infinite;
  }
  
  :global(.loader-unfold .logo-right) {
    transform-origin: left center;
    animation: unfoldRight 2s ease-in-out infinite;
  }
  
  :global(.loader-unfold .logo-center) {
    animation: unfoldCenter 2s ease-in-out infinite;
  }

  @keyframes unfoldLeft {
    0%, 100% {
      transform: rotateY(90deg);
      opacity: 0;
    }
    25%, 75% {
      transform: rotateY(0deg);
      opacity: 1;
    }
  }

  @keyframes unfoldRight {
    0%, 100% {
      transform: rotateY(-90deg);
      opacity: 0;
    }
    35%, 75% {
      transform: rotateY(0deg);
      opacity: 1;
    }
  }

  @keyframes unfoldCenter {
    0%, 100% {
      transform: scale(0) rotate(180deg);
      opacity: 0;
    }
    45%, 75% {
      transform: scale(1) rotate(0deg);
      opacity: 1;
    }
  }

  :global(.loader-spread .logo-left) {
    animation: spreadLeft 2s ease-in-out infinite;
  }
  
  :global(.loader-spread .logo-right) {
    animation: spreadRight 2s ease-in-out infinite;
  }
  
  :global(.loader-spread .logo-center) {
    animation: spreadCenter 2s ease-in-out infinite;
  }

  @keyframes spreadLeft {
    0%, 100% {
      transform: translateX(0);
    }
    50% {
      transform: translateX(-10px);
    }
  }

  @keyframes spreadRight {
    0%, 100% {
      transform: translateX(0);
    }
    50% {
      transform: translateX(10px);
    }
  }

  @keyframes spreadCenter {
    0%, 100% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.2);
    }
  }

  :global(.loader-wave .logo-center) {
    animation: waveCenter 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
  
  :global(.loader-wave .logo-left) {
    animation: waveLeft 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
  
  :global(.loader-wave .logo-right) {
    animation: waveRight 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  @keyframes waveCenter {
    0%, 20% { 
      transform: scale(1.5) rotate(0deg);
      opacity: 1;
    }
    40%, 60% { 
      transform: scale(0.8) rotate(180deg);
      opacity: 0.6;
    }
    80%, 100% { 
      transform: scale(1.5) rotate(360deg);
      opacity: 1;
    }
  }

  @keyframes waveLeft {
    0%, 10% { 
      transform: translateX(0) translateY(0) rotate(0deg);
      opacity: 1;
    }
    30% {
      transform: translateX(-30px) translateY(-20px) rotate(-20deg);
      opacity: 0.7;
    }
    50% { 
      transform: translateX(0) translateY(-30px) rotate(0deg);
      opacity: 0.5;
    }
    70% {
      transform: translateX(30px) translateY(-20px) rotate(20deg);
      opacity: 0.7;
    }
    90%, 100% { 
      transform: translateX(0) translateY(0) rotate(0deg);
      opacity: 1;
    }
  }

  @keyframes waveRight {
    0%, 10% { 
      transform: translateX(0) translateY(0) rotate(0deg);
      opacity: 1;
    }
    30% {
      transform: translateX(30px) translateY(-20px) rotate(20deg);
      opacity: 0.7;
    }
    50% { 
      transform: translateX(0) translateY(-30px) rotate(0deg);
      opacity: 0.5;
    }
    70% {
      transform: translateX(-30px) translateY(-20px) rotate(-20deg);
      opacity: 0.7;
    }
    90%, 100% { 
      transform: translateX(0) translateY(0) rotate(0deg);
      opacity: 1;
    }
  }

  :global(.loader-stagger .logo-left) {
    animation: staggerPulse 1.8s ease-in-out infinite;
  }
  
  :global(.loader-stagger .logo-center) {
    animation: staggerPulse 1.8s ease-in-out infinite 0.2s;
  }
  
  :global(.loader-stagger .logo-right) {
    animation: staggerPulse 1.8s ease-in-out infinite 0.4s;
  }

  @keyframes staggerPulse {
    0%, 100% {
      transform: scale(1);
      opacity: 0.5;
    }
    50% {
      transform: scale(1.15);
      opacity: 1;
    }
  }

  :global(.loader-build .logo-center) {
    animation: buildCenter 3.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }
  
  :global(.loader-build .logo-left) {
    animation: buildLeft 3.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }
  
  :global(.loader-build .logo-right) {
    animation: buildRight 3.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }

  @keyframes buildCenter {
    0% {
      transform: scale(0);
      opacity: 0;
    }
    15%, 25% {
      transform: scale(1.3);
      opacity: 1;
    }
    30%, 70% {
      transform: scale(1);
      opacity: 1;
    }
    85%, 100% {
      transform: scale(0) rotate(180deg);
      opacity: 0;
    }
  }

  @keyframes buildLeft {
    0%, 25% {
      transform: translateX(-150px) scale(0);
      opacity: 0;
    }
    35% {
      transform: translateX(10px) scale(1.1);
      opacity: 1;
    }
    45%, 70% {
      transform: translateX(0) scale(1);
      opacity: 1;
    }
    85%, 100% {
      transform: translateX(-150px) scale(0);
      opacity: 0;
    }
  }

  @keyframes buildRight {
    0%, 30% {
      transform: translateX(150px) scale(0);
      opacity: 0;
    }
    40% {
      transform: translateX(-10px) scale(1.1);
      opacity: 1;
    }
    50%, 70% {
      transform: translateX(0) scale(1);
      opacity: 1;
    }
    85%, 100% {
      transform: translateX(150px) scale(0);
      opacity: 0;
    }
  }

  :global(.loader-collapse .logo-left) {
    transform-origin: bottom right;
    animation: collapseLeft 2s ease-in-out infinite;
  }
  
  :global(.loader-collapse .logo-right) {
    transform-origin: bottom left;
    animation: collapseRight 2s ease-in-out infinite;
  }
  
  :global(.loader-collapse .logo-center) {
    animation: collapseCenter 2s ease-in-out infinite;
  }

  @keyframes collapseLeft {
    0%, 100% {
      transform: rotate(0deg) scale(1);
    }
    50% {
      transform: rotate(-20deg) scale(0.8);
    }
  }

  @keyframes collapseRight {
    0%, 100% {
      transform: rotate(0deg) scale(1);
    }
    50% {
      transform: rotate(20deg) scale(0.8);
    }
  }

  @keyframes collapseCenter {
    0%, 100% {
      transform: scale(1) translateY(0);
    }
    50% {
      transform: scale(0.6) translateY(10px);
    }
  }

  :global(.loader-dance .logo-center) {
    animation: danceCenter 3s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }
  
  :global(.loader-dance .logo-left) {
    animation: danceLeft 3s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }
  
  :global(.loader-dance .logo-right) {
    animation: danceRight 3s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
  }

  @keyframes danceCenter {
    0%, 10% {
      transform: scale(0) rotate(0deg);
      opacity: 0;
    }
    20%, 30% {
      transform: scale(1.5) rotate(360deg);
      opacity: 1;
    }
    40%, 80% {
      transform: scale(1) rotate(720deg);
      opacity: 1;
    }
    90%, 100% {
      transform: scale(0) rotate(1080deg);
      opacity: 0;
    }
  }

  @keyframes danceLeft {
    0%, 30% {
      transform: translateX(-100px) translateY(0) rotate(0deg) scale(0);
      opacity: 0;
    }
    40% {
      transform: translateX(0) translateY(-20px) rotate(20deg) scale(1.2);
      opacity: 1;
    }
    50% {
      transform: translateX(20px) translateY(0) rotate(-20deg) scale(1);
      opacity: 1;
    }
    60% {
      transform: translateX(-20px) translateY(-10px) rotate(20deg) scale(1.1);
      opacity: 1;
    }
    70%, 80% {
      transform: translateX(0) translateY(0) rotate(0deg) scale(1);
      opacity: 1;
    }
    90%, 100% {
      transform: translateX(-100px) translateY(0) rotate(-360deg) scale(0);
      opacity: 0;
    }
  }

  @keyframes danceRight {
    0%, 35% {
      transform: translateX(100px) translateY(0) rotate(0deg) scale(0);
      opacity: 0;
    }
    45% {
      transform: translateX(0) translateY(-20px) rotate(-20deg) scale(1.2);
      opacity: 1;
    }
    55% {
      transform: translateX(-20px) translateY(0) rotate(20deg) scale(1);
      opacity: 1;
    }
    65% {
      transform: translateX(20px) translateY(-10px) rotate(-20deg) scale(1.1);
      opacity: 1;
    }
    75%, 80% {
      transform: translateX(0) translateY(0) rotate(0deg) scale(1);
      opacity: 1;
    }
    90%, 100% {
      transform: translateX(100px) translateY(0) rotate(360deg) scale(0);
      opacity: 0;
    }
  }

  /* CenterFirst Animation */
  :global(.loader-centerfirst .logo-center) {
    animation: centerFirstCenter 3s ease-in-out infinite;
    transform-origin: center center;
  }
  
  :global(.loader-centerfirst .logo-left) {
    animation: centerFirstLeft 3s ease-in-out infinite;
  }
  
  :global(.loader-centerfirst .logo-right) {
    animation: centerFirstRight 3s ease-in-out infinite;
  }

  @keyframes centerFirstCenter {
    0%, 15% {
      opacity: 0;
      transform: scale(0);
    }
    30%, 80% {
      opacity: 1;
      transform: scale(1);
    }
    95%, 100% {
      opacity: 0;
      transform: scale(0);
    }
  }

  @keyframes centerFirstLeft {
    0%, 30% {
      opacity: 0;
      transform: translateX(-100px);
    }
    50%, 80% {
      opacity: 1;
      transform: translateX(0);
    }
    95%, 100% {
      opacity: 0;
      transform: translateX(-100px);
    }
  }

  @keyframes centerFirstRight {
    0%, 30% {
      opacity: 0;
      transform: translateX(100px);
    }
    50%, 80% {
      opacity: 1;
      transform: translateX(0);
    }
    95%, 100% {
      opacity: 0;
      transform: translateX(100px);
    }
  }

  /* AppearGlowFlip - Compound Animation with timing variables */
  :global(.loader-appearglowflip) {
    --duration: 10s;
    --appear-time: 0.3s;
    --glow-time: 0.4s;
    --flip-time: 0.5s;
    animation: appearGlowFlip var(--duration) ease-in-out infinite;
  }

  @keyframes appearGlowFlip {
    /* Appear phase */
    0% {
      opacity: 0;
      transform: scale(0);
    }
    3% {
      opacity: 1;
      transform: scale(1);
    }
    
    /* Four glow pulses */
    /* Glow 1 */
    8% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    10% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    12% {
      filter: none;
    }
    
    /* Glow 2 */
    16% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    18% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    20% {
      filter: none;
    }
    
    /* Glow 3 */
    24% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    26% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    28% {
      filter: none;
    }
    
    /* Glow 4 */
    32% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    34% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    36% {
      filter: none;
    }
    
    /* Single flip */
    40% {
      transform: scale(1) perspective(200px) rotateY(0deg);
    }
    42.5% {
      transform: scale(1) perspective(200px) rotateY(180deg);
    }
    45% {
      transform: scale(1) perspective(200px) rotateY(360deg);
    }
    46% {
      transform: scale(1) perspective(200px) rotateY(360deg);
    }
    47% {
      transform: scale(1);  /* Reset to normal, no rotation */
    }
    
    /* Four more glow pulses */
    /* Glow 5 */
    50% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    52% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    54% {
      filter: none;
    }
    
    /* Glow 6 */
    58% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    60% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    62% {
      filter: none;
    }
    
    /* Glow 7 */
    66% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    68% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    70% {
      filter: none;
    }
    
    /* Glow 8 */
    74% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    76% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
    78% {
      filter: none;
    }
    
    /* Stay visible */
    80%, 92% {
      opacity: 1;
      transform: scale(1);
      filter: none;
    }
    
    /* Disappear phase */
    95% {
      opacity: 0;
      transform: scale(0);
    }
    
    /* Stay hidden */
    96%, 100% {
      opacity: 0;
      transform: scale(0);
    }
  }

  @media (max-width: 768px) {
    .effects-grid {
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 1rem;
    }
    
    h1 {
      font-size: 1.8rem;
    }
  }
</style>