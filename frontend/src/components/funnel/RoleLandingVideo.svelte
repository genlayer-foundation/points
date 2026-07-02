<script>
  import { onMount } from 'svelte';

  let {
    variant = 'genlayer',
    eyebrow = 'Portal Preview',
    title = 'GenLayer in motion',
    description = 'Watch the network experience before starting your journey.',
    src = '/assets/landings/default-video-landings.mp4',
    poster = '/assets/landings/default-video-landings-poster.jpg',
  } = $props();

  const PALETTES = {
    builder: { accent: '#ee8521', rgb: '238, 133, 33' },
    community: { accent: '#7f52e1', rgb: '127, 82, 225' },
    validator: { accent: '#3a7ce7', rgb: '58, 124, 231' },
    genlayer: { accent: '#111827', rgb: '17, 24, 39' },
  };
  const CONTROL_HIDE_DELAY = 2200;

  let frameEl = $state(null);
  let videoEl = $state(null);
  let isPlaying = $state(false);
  let isMuted = $state(true);
  let isFullscreen = $state(false);
  let controlsVisible = $state(true);
  let hasControlFocus = $state(false);
  let isScrubbing = $state(false);
  let duration = $state(0);
  let currentTime = $state(0);
  let controlsHideTimer;

  const palette = $derived(PALETTES[variant] || PALETTES.genlayer);
  const progress = $derived(duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0);
  const rootStyle = $derived(`--player-accent: ${palette.accent}; --player-accent-rgb: ${palette.rgb};`);
  const progressStyle = $derived(`--progress: ${progress}%;`);

  onMount(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const handleFullscreenChange = () => {
      isFullscreen = document.fullscreenElement === frameEl;
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);

    if (videoEl) {
      videoEl.muted = isMuted;
      if (!reducedMotion) {
        videoEl.play()?.catch(() => {
          isPlaying = false;
        });
      }
    }

    return () => {
      clearControlsHideTimer();
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  });

  function clearControlsHideTimer() {
    if (!controlsHideTimer) return;
    clearTimeout(controlsHideTimer);
    controlsHideTimer = undefined;
  }

  function scheduleControlsHide() {
    clearControlsHideTimer();

    if (!isPlaying || hasControlFocus || isScrubbing) {
      controlsVisible = true;
      return;
    }

    controlsHideTimer = window.setTimeout(() => {
      controlsVisible = false;
    }, CONTROL_HIDE_DELAY);
  }

  function revealControls() {
    controlsVisible = true;
    scheduleControlsHide();
  }

  function handleFocusIn() {
    hasControlFocus = true;
    controlsVisible = true;
    clearControlsHideTimer();
  }

  function handleFocusOut(event) {
    const nextTarget = event.relatedTarget;

    if (nextTarget && frameEl?.contains(nextTarget)) {
      return;
    }

    hasControlFocus = false;
    scheduleControlsHide();
  }

  function syncMetadata() {
    if (!videoEl) return;
    duration = Number.isFinite(videoEl.duration) ? videoEl.duration : 0;
    currentTime = videoEl.currentTime || 0;
    isMuted = videoEl.muted;
    isPlaying = !videoEl.paused;
    scheduleControlsHide();
  }

  function syncTime() {
    if (!videoEl) return;
    currentTime = videoEl.currentTime || 0;
  }

  function handlePlay() {
    isPlaying = true;
    revealControls();
  }

  function handlePause() {
    isPlaying = false;
    controlsVisible = true;
    clearControlsHideTimer();
  }

  async function togglePlayback() {
    if (!videoEl) return;

    if (videoEl.paused) {
      await videoEl.play().catch(() => {});
    } else {
      videoEl.pause();
    }
  }

  function toggleMute() {
    if (!videoEl) return;
    videoEl.muted = !videoEl.muted;
    isMuted = videoEl.muted;
  }

  function seek(event) {
    if (!videoEl || !duration) return;
    const next = Number(event.currentTarget.value);
    videoEl.currentTime = (next / 100) * duration;
    currentTime = videoEl.currentTime;
    revealControls();
  }

  function beginScrubbing() {
    isScrubbing = true;
    controlsVisible = true;
    clearControlsHideTimer();
  }

  function endScrubbing() {
    isScrubbing = false;
    scheduleControlsHide();
  }

  async function toggleFullscreen() {
    if (!frameEl) return;

    if (document.fullscreenElement) {
      await document.exitFullscreen?.();
    } else {
      await frameEl.requestFullscreen?.();
    }
  }

  function formatTime(seconds) {
    if (!Number.isFinite(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  }
</script>

<div
  class="landing-video"
  class:is-paused={!isPlaying}
  class:controls-hidden={!controlsVisible && isPlaying}
  bind:this={frameEl}
  style={rootStyle}
  role="group"
  aria-labelledby={`landing-video-title-${variant}`}
  onpointerenter={revealControls}
  onpointermove={revealControls}
  onpointerleave={scheduleControlsHide}
  ontouchstart={revealControls}
  onfocusin={handleFocusIn}
  onfocusout={handleFocusOut}
>
  <video
    bind:this={videoEl}
    src={src}
    {poster}
    class="landing-video-media"
    autoplay
    muted={isMuted}
    loop
    playsinline
    preload="metadata"
    controlsList="nodownload"
    onloadedmetadata={syncMetadata}
    ontimeupdate={syncTime}
    onplay={handlePlay}
    onpause={handlePause}
    onclick={togglePlayback}
  ></video>

  <div class="landing-video-sheen" aria-hidden="true"></div>

  <div class="landing-video-copy">
    <div class="landing-video-kicker">
      <span aria-hidden="true"></span>
      {eyebrow}
    </div>
    <h2 id={`landing-video-title-${variant}`}>{title}</h2>
    <p>{description}</p>
  </div>

  <button
    type="button"
    class="landing-video-center"
    aria-label={isPlaying ? 'Pause video' : 'Play video'}
    onclick={togglePlayback}
  >
    {#if isPlaying}
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 5h3v14H8zM13 5h3v14h-3z"></path>
      </svg>
    {:else}
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 5v14l11-7z"></path>
      </svg>
    {/if}
  </button>

  <div
    class="landing-video-controls"
    role="group"
    aria-label="Video controls"
    onpointerenter={revealControls}
  >
    <button
      type="button"
      class="control-button"
      aria-label={isPlaying ? 'Pause video' : 'Play video'}
      onclick={togglePlayback}
    >
      {#if isPlaying}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8 5h3v14H8zM13 5h3v14h-3z"></path>
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8 5v14l11-7z"></path>
        </svg>
      {/if}
    </button>

    <div class="time-readout" aria-label={`${formatTime(currentTime)} of ${formatTime(duration)}`}>
      {formatTime(currentTime)}
      <span>/</span>
      {formatTime(duration)}
    </div>

    <input
      class="progress-control"
      style={progressStyle}
      type="range"
      min="0"
      max="100"
      step="0.1"
      value={progress}
      aria-label="Seek video"
      oninput={seek}
      onpointerdown={beginScrubbing}
      onpointerup={endScrubbing}
      onpointercancel={endScrubbing}
      onkeydown={revealControls}
    />

    <button
      type="button"
      class="control-button"
      aria-label={isMuted ? 'Unmute video' : 'Mute video'}
      onclick={toggleMute}
    >
      {#if isMuted}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 10v4h4l5 4V6L8 10H4zM18 9l3 3-3 3M21 9l-3 3 3 3"></path>
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 10v4h4l5 4V6L8 10H4zM17 9.5c1 .7 1.5 1.5 1.5 2.5S18 13.8 17 14.5M19.5 7c1.7 1.4 2.5 3 2.5 5s-.8 3.6-2.5 5"></path>
        </svg>
      {/if}
    </button>

    <button
      type="button"
      class="control-button"
      aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
      onclick={toggleFullscreen}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        {#if isFullscreen}
          <path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"></path>
        {:else}
          <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"></path>
        {/if}
      </svg>
    </button>
  </div>
</div>

<style>
  .landing-video {
    aspect-ratio: 16 / 9;
    background:
      radial-gradient(circle at 18% 18%, rgba(var(--player-accent-rgb), 0.3), transparent 32%),
      linear-gradient(145deg, #151515 0%, #050505 100%);
    border: 1px solid rgba(var(--player-accent-rgb), 0.2);
    border-radius: 8px;
    box-shadow:
      0 22px 60px rgba(var(--player-accent-rgb), 0.2),
      0 1px 0 rgba(255, 255, 255, 0.72) inset;
    color: #fff;
    container-type: inline-size;
    isolation: isolate;
    min-width: 0;
    overflow: hidden;
    position: relative;
    width: 100%;
  }

  .landing-video-media {
    background: #0d0d0d;
    display: block;
    height: 100%;
    object-fit: cover;
    width: 100%;
  }

  .landing-video-sheen {
    background:
      linear-gradient(180deg, rgba(0, 0, 0, 0.1) 0%, transparent 34%, rgba(0, 0, 0, 0.76) 100%),
      linear-gradient(90deg, rgba(0, 0, 0, 0.55) 0%, transparent 48%);
    inset: 0;
    pointer-events: none;
    position: absolute;
    z-index: 1;
  }

  .landing-video-copy {
    bottom: 78px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    left: 22px;
    max-width: min(420px, calc(100% - 44px));
    position: absolute;
    transform: translateY(0);
    transition:
      opacity 190ms cubic-bezier(0.2, 0, 0, 1),
      transform 190ms cubic-bezier(0.2, 0, 0, 1);
    z-index: 2;
  }

  .landing-video.controls-hidden .landing-video-copy {
    opacity: 0;
    pointer-events: none;
    transform: translateY(12px);
  }

  .landing-video-kicker {
    align-items: center;
    color: rgba(255, 255, 255, 0.8);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 11px;
    gap: 8px;
    letter-spacing: 0.8px;
    line-height: 16px;
    text-transform: uppercase;
  }

  .landing-video-kicker span {
    background: var(--player-accent);
    border-radius: 999px;
    box-shadow: 0 0 18px rgba(var(--player-accent-rgb), 0.85);
    height: 8px;
    width: 8px;
  }

  .landing-video-copy h2 {
    color: #fff;
    font-family: var(--font-display);
    font-size: clamp(22px, 3vw, 34px);
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1;
    margin: 0;
  }

  .landing-video-copy p {
    color: rgba(255, 255, 255, 0.72);
    font-size: 14px;
    line-height: 20px;
    margin: 0;
  }

  .landing-video-center {
    align-items: center;
    background: rgba(255, 255, 255, 0.88);
    border: 1px solid rgba(255, 255, 255, 0.64);
    border-radius: 999px;
    box-shadow: 0 16px 42px rgba(0, 0, 0, 0.28);
    color: var(--player-accent);
    display: flex;
    height: 64px;
    justify-content: center;
    left: 50%;
    opacity: 0;
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%) scale(0.92);
    transition: opacity 180ms ease, transform 180ms ease, background-color 180ms ease;
    width: 64px;
    z-index: 3;
  }

  .landing-video:hover .landing-video-center,
  .landing-video:focus-within .landing-video-center,
  .landing-video.is-paused .landing-video-center {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }

  .landing-video-center:hover {
    background: #fff;
  }

  .landing-video-center svg {
    fill: currentColor;
    height: 25px;
    width: 25px;
  }

  .landing-video-controls {
    align-items: center;
    background: rgba(12, 12, 14, 0.74);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    bottom: 16px;
    display: grid;
    gap: 10px;
    grid-template-columns: 32px auto minmax(72px, 1fr) 32px 32px;
    left: 16px;
    padding: 8px;
    position: absolute;
    right: 16px;
    transform: translateY(0);
    transition:
      opacity 190ms cubic-bezier(0.2, 0, 0, 1),
      transform 190ms cubic-bezier(0.2, 0, 0, 1);
    z-index: 4;
    -webkit-backdrop-filter: blur(18px);
    backdrop-filter: blur(18px);
  }

  .landing-video.controls-hidden .landing-video-controls {
    opacity: 0;
    pointer-events: none;
    transform: translateY(12px);
  }

  .control-button {
    align-items: center;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 7px;
    color: #fff;
    display: flex;
    height: 32px;
    justify-content: center;
    transition: background-color 160ms ease, transform 160ms ease;
    width: 32px;
  }

  .control-button:hover {
    background: rgba(255, 255, 255, 0.18);
  }

  .control-button:active {
    transform: scale(0.94);
  }

  .control-button svg {
    fill: none;
    height: 18px;
    stroke: currentColor;
    stroke-linecap: round;
    stroke-linejoin: round;
    stroke-width: 2;
    width: 18px;
  }

  .control-button:first-child svg {
    fill: currentColor;
    stroke: none;
  }

  .time-readout {
    color: rgba(255, 255, 255, 0.78);
    font-family: var(--font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    line-height: 16px;
    white-space: nowrap;
  }

  .time-readout span {
    color: rgba(255, 255, 255, 0.38);
    margin: 0 3px;
  }

  .progress-control {
    appearance: none;
    background:
      linear-gradient(90deg, var(--player-accent) 0 var(--progress), rgba(255, 255, 255, 0.22) var(--progress) 100%);
    border-radius: 999px;
    cursor: pointer;
    height: 5px;
    min-width: 0;
    width: 100%;
  }

  .progress-control::-webkit-slider-thumb {
    appearance: none;
    background: #fff;
    border: 2px solid var(--player-accent);
    border-radius: 999px;
    box-shadow: 0 0 0 4px rgba(var(--player-accent-rgb), 0.22);
    height: 15px;
    width: 15px;
  }

  .progress-control::-moz-range-thumb {
    background: #fff;
    border: 2px solid var(--player-accent);
    border-radius: 999px;
    box-shadow: 0 0 0 4px rgba(var(--player-accent-rgb), 0.22);
    height: 11px;
    width: 11px;
  }

  @container (max-width: 460px) {
    .landing-video-copy {
      bottom: 68px;
      gap: 6px;
      max-width: calc(100% - 28px);
    }

    .landing-video-copy p {
      display: none;
    }

    .landing-video-center {
      height: 54px;
      width: 54px;
    }

    .landing-video-center svg {
      height: 22px;
      width: 22px;
    }

    .landing-video-controls {
      bottom: 10px;
      gap: 8px;
      grid-template-columns: 32px minmax(84px, 1fr) 32px 32px;
      left: 10px;
      right: 10px;
    }

    .time-readout {
      display: none;
    }
  }

  @container (max-width: 340px) {
    .landing-video-copy {
      bottom: 62px;
      left: 12px;
      max-width: calc(100% - 24px);
    }

    .landing-video-kicker {
      font-size: 10px;
      line-height: 14px;
    }

    .landing-video-copy h2 {
      font-size: 20px;
    }

    .landing-video-center {
      height: 48px;
      width: 48px;
    }

    .landing-video-controls {
      grid-template-columns: 30px minmax(60px, 1fr) 30px 30px;
      padding: 7px;
    }

    .control-button {
      height: 30px;
      width: 30px;
    }
  }

  @media (max-width: 640px) {
    .landing-video-copy {
      left: 14px;
    }
  }
</style>
