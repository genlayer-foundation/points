<script>
  import GenLayerLogo from './GenLayerLogo.svelte';
  
  let { 
    sequence = [
      { effect: 'appear', duration: 500 },
      { effect: 'glow', duration: 400, repeat: 4 },
      { effect: 'flip', duration: 500 },
      { effect: 'glow', duration: 400, repeat: 4 },
      { effect: 'disappear', duration: 500 }
    ],
    loop = true,
    class: className = '',
    ...props
  } = $props();
  
  let currentEffect = $state('');
  let currentIndex = $state(0);
  let repeatCount = $state(0);
  
  function playSequence() {
    if (currentIndex >= sequence.length) {
      if (loop) {
        currentIndex = 0;
        repeatCount = 0;
      } else {
        return;
      }
    }
    
    const step = sequence[currentIndex];
    currentEffect = `loader-${step.effect}`;
    
    // Handle repeating effects
    if (step.repeat && repeatCount < step.repeat - 1) {
      repeatCount++;
      setTimeout(() => {
        currentEffect = ''; // Reset effect
        setTimeout(() => {
          playSequence(); // Play same effect again
        }, 50);
      }, step.duration);
    } else {
      repeatCount = 0;
      currentIndex++;
      setTimeout(() => {
        playSequence();
      }, step.duration);
    }
  }
  
  // Start the sequence
  $effect(() => {
    playSequence();
  });
  
  // Map of individual animation styles
  const effectStyles = {
    'loader-appear': `
      animation: quickAppear 0.5s ease-out forwards;
    `,
    'loader-disappear': `
      animation: quickDisappear 0.5s ease-out forwards;
    `,
    'loader-glow': `
      animation: quickGlow 0.4s ease-in-out;
    `,
    'loader-flip': `
      animation: quickFlip 0.5s ease-in-out;
    `,
    'loader-pulse': `
      animation: quickPulse 0.4s ease-in-out;
    `
  };
  
  let currentStyle = $derived(effectStyles[currentEffect] || '');
</script>

<div class="sequence-loader {className}" {...props}>
  <GenLayerLogo 
    class={currentEffect}
    style={currentStyle}
  />
</div>

<style>
  .sequence-loader {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  
  /* Quick individual animations for sequencing */
  @keyframes quickAppear {
    from {
      opacity: 0;
      transform: scale(0);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
  
  @keyframes quickDisappear {
    from {
      opacity: 1;
      transform: scale(1);
    }
    to {
      opacity: 0;
      transform: scale(0);
    }
  }
  
  @keyframes quickGlow {
    0%, 100% {
      filter: drop-shadow(0 0 2px #00c8ff);
    }
    50% {
      filter: drop-shadow(0 0 20px #00c8ff) drop-shadow(0 0 40px #00c8ff);
    }
  }
  
  @keyframes quickFlip {
    from {
      transform: perspective(200px) rotateY(0deg);
    }
    to {
      transform: perspective(200px) rotateY(360deg);
    }
  }
  
  @keyframes quickPulse {
    0%, 100% {
      transform: scale(1);
    }
    50% {
      transform: scale(1.1);
    }
  }
</style>