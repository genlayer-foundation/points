<script>
  import { onMount, tick } from 'svelte';
  import { push } from 'svelte-spa-router';
  import WhatsNewAnnouncementSurface from './whats-new-announcement-surface.svelte';
  import { authState } from '../lib/auth.js';
  import { followNotificationLink } from '../lib/notificationUtils.js';
  import { whatsNewStore } from '../lib/whatsNewStore.js';
  import { CAUGHT_UP_GRADIENT, normalizeWhatsNewItem } from '../lib/whatsNewPresentation.js';

  /**
   * @typedef {Object} WhatsNewSlide
   * @property {number | string} id
   * @property {string} audience
   * @property {string} audienceLabel
   * @property {string} eyebrow
   * @property {string} title
   * @property {string} body
   * @property {string} bodyHtml
   * @property {string} linkUrl
   * @property {string} linkLabel
   * @property {string} accent
   * @property {string} gradient
   * @property {string} image
   * @property {boolean} showCommunityContribution
   */

  let visible = $state(false);
  let loading = $state(false);
  let error = $state('');
  /** @type {WhatsNewSlide[]} */
  let slides = $state([]);
  let currentIndex = $state(0);
  /** @type {HTMLElement | null} */
  let dialogPanel = $state(null);

  let activeSlide = $derived(slides[currentIndex] || null);
  let totalSlides = $derived(slides.length);
  let primaryLabel = $derived(currentIndex >= totalSlides - 1 ? 'Done' : 'Next');
  let currentProgress = $derived(`${currentIndex + 1} of ${totalSlides}`);

  /** @type {string | null} */
  let lastAuthKey = null;

  async function loadUnseen({ auto = false } = {}) {
    if (!$authState.isAuthenticated) return;

    if (!auto) {
      openDialog();
    }

    loading = true;
    error = '';

    try {
      const nextSlides = (await whatsNewStore.loadUnseen()).map(normalizeWhatsNewItem);
      slides = nextSlides;
      currentIndex = 0;

      if (!auto || nextSlides.length > 0) {
        openDialog();
      }
    } catch (err) {
      error = 'Could not load updates right now.';
      if (!auto) {
        openDialog();
      }
    } finally {
      loading = false;
    }
  }

  function openDialog() {
    visible = true;
    tick().then(() => {
      dialogPanel?.focus();
    });
  }

  function closeDialog({ clear = false } = {}) {
    visible = false;
    whatsNewStore.close();
    if (clear) {
      slides = [];
      currentIndex = 0;
    }
  }

  /** @param {WhatsNewSlide | null} slide */
  async function markSlideSeen(slide, action = 'seen') {
    if (!slide?.id) return;
    try {
      await whatsNewStore.markSeen([slide.id], action);
    } catch (err) {
      error = 'Could not save that update as seen.';
    }
  }

  /** @param {WhatsNewSlide[]} slidesToMark */
  async function markSlidesSeen(slidesToMark, action = 'skipped') {
    const ids = slidesToMark.map((slide) => slide.id).filter(Boolean);
    if (ids.length === 0) return;
    try {
      await whatsNewStore.markSeen(ids, action);
    } catch (err) {
      error = 'Could not save these updates as seen.';
    }
  }

  async function handlePrimary() {
    if (!activeSlide) {
      closeDialog({ clear: true });
      return;
    }

    await markSlideSeen(activeSlide);

    if (currentIndex < totalSlides - 1) {
      currentIndex += 1;
      return;
    }

    closeDialog({ clear: true });
  }

  async function handleSkip() {
    if (slides.length > 0) {
      await markSlidesSeen(slides, 'skipped');
    }
    closeDialog({ clear: true });
  }

  async function openLinkedSlide() {
    if (!activeSlide?.linkUrl) return;
    await markSlideSeen(activeSlide, 'opened');
    closeDialog({ clear: true });
    followNotificationLink({ link_url: activeSlide.linkUrl });
  }

  function openAnnouncementsView() {
    closeDialog({ clear: true });
    push('/notifications?tab=announcements');
  }

  /** @param {KeyboardEvent} event */
  function handleKeydown(event) {
    if (!visible || event.key !== 'Escape') return;
    event.preventDefault();
    handleSkip();
  }

  $effect(() => {
    const isAuthenticated = $authState.isAuthenticated;
    const address = $authState.address;

    if (!isAuthenticated) {
      lastAuthKey = null;
      whatsNewStore.reset();
      closeDialog({ clear: true });
      return;
    }

    const authKey = address || 'authenticated';
    if (authKey === lastAuthKey) return;

    lastAuthKey = authKey;
    whatsNewStore.refresh().catch(() => {});
    loadUnseen({ auto: true });
  });

  $effect(() => {
    if ($whatsNewStore.visible && !visible && $authState.isAuthenticated) {
      loadUnseen({ auto: false });
    }
  });

  $effect(() => {
    if (!visible || typeof document === 'undefined') return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  });

  onMount(() => {
    document.addEventListener('keydown', handleKeydown);

    return () => {
      document.removeEventListener('keydown', handleKeydown);
    };
  });
</script>

{#if visible && $authState.isAuthenticated}
  <div
    class="whats-new-layer"
    style="--wn-accent: {activeSlide?.accent || '#19A663'}; --wn-gradient: {activeSlide?.gradient || CAUGHT_UP_GRADIENT};"
  >
    <button
      type="button"
      class="dialog-backdrop"
      aria-label="Close What's New"
      onclick={handleSkip}
    ></button>

    <div class="dialog-wrap">
      {#if loading && slides.length === 0}
        <div
          class="whats-new-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="whats-new-title"
          tabindex="-1"
          bind:this={dialogPanel}
        >
          <div class="dialog-loading" aria-busy="true">
            <div class="loading-visual"></div>
            <div class="loading-copy">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      {:else if !activeSlide}
        <div
          class="whats-new-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="whats-new-title"
          tabindex="-1"
          bind:this={dialogPanel}
        >
          <button
            type="button"
            class="close-button"
            aria-label="Close What's New"
            onclick={() => closeDialog({ clear: true })}
          >
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </button>
          <div class="empty-state">
            <div class="empty-mark">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M20 7L10 17l-5-5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </div>
            <p class="eyebrow">What's new</p>
            <h2 id="whats-new-title">You are caught up</h2>
            <p class="empty-copy">
              There are no unseen portal announcements for your account right now.
            </p>
            {#if error}
              <p class="error-copy">{error}</p>
            {/if}
            <button type="button" class="empty-action" onclick={openAnnouncementsView}>
              View announcements
            </button>
          </div>
        </div>
      {:else}
        <WhatsNewAnnouncementSurface
          slide={activeSlide}
          bind:dialogEl={dialogPanel}
          labelledby="whats-new-title"
          showClose={true}
          closeLabel="Close What's New"
          onClose={handleSkip}
          {totalSlides}
          {currentIndex}
          {currentProgress}
          {primaryLabel}
          showSkip={totalSlides > 1}
          onSkip={handleSkip}
          onPrimary={handlePrimary}
          onOpenLink={openLinkedSlide}
          {error}
        />
      {/if}
    </div>
  </div>
{/if}

<style>
  .whats-new-layer {
    position: fixed;
    inset: 0;
    z-index: 9000;
    pointer-events: none;
  }

  .dialog-backdrop {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    background: rgba(17, 24, 39, 0.38);
    backdrop-filter: blur(4px) saturate(0.96);
    pointer-events: auto;
    animation: backdropIn 180ms ease-out both;
  }

  .dialog-wrap {
    position: absolute;
    inset: 0;
    z-index: 3;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.25rem;
    pointer-events: none;
  }

  .whats-new-dialog {
    position: relative;
    width: min(40rem, calc(100vw - 2rem));
    max-height: min(36rem, calc(100vh - 2rem));
    overflow: hidden;
    border: 1px solid rgba(232, 235, 242, 0.88);
    border-radius: 16px;
    background:
      linear-gradient(135deg, rgba(255, 255, 255, 0.44) 0%, rgba(255, 255, 255, 0.24) 48%, rgba(247, 248, 251, 0.52) 100%),
      var(--wn-gradient),
      url('/assets/illustrations/cta-gradient.webp');
    background-position: center;
    background-size: cover;
    box-shadow: 0 18px 48px rgba(38, 48, 75, 0.17);
    color: #111827;
    pointer-events: auto;
    animation: dialogIn 220ms cubic-bezier(0.2, 0.8, 0.2, 1) both;
  }

  .whats-new-dialog:focus {
    outline: none;
  }

  .close-button {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    z-index: 4;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.1rem;
    height: 2.1rem;
    border: 1px solid #e0e5ef;
    border-radius: 999px;
    color: #506078;
    background: rgba(255, 255, 255, 0.9);
    transition: background 150ms ease, border-color 150ms ease, color 150ms ease, transform 150ms ease;
  }

  .close-button:hover {
    transform: translateY(-1px);
    border-color: #cdd5e3;
    color: #111827;
    background: #fff;
  }

  .close-button svg {
    width: 1rem;
    height: 1rem;
  }

  .dialog-loading {
    display: grid;
    grid-template-columns: minmax(22rem, 1.04fr) minmax(21rem, 0.96fr);
    min-height: 29rem;
  }

  .empty-state {
    display: flex;
    min-height: 20rem;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2.35rem 1.65rem 2rem;
    text-align: center;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.54), rgba(255, 255, 255, 0.28));
  }

  .empty-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 3.2rem;
    height: 3.2rem;
    margin-bottom: 1rem;
    border-radius: 999px;
    color: #19A663;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
  }

  .empty-mark svg {
    width: 1.35rem;
    height: 1.35rem;
  }

  .empty-state h2 {
    margin: 0;
    color: #000;
    font-family: var(--font-display);
    font-size: clamp(1.65rem, 3vw, 2.7rem);
    font-weight: 650;
    letter-spacing: 0;
    line-height: 1;
  }

  .eyebrow {
    margin: 0 0 0.65rem;
    color: #8a94a7;
    font-size: 0.74rem;
    font-weight: 700;
  }

  .empty-copy {
    max-width: 28rem;
    margin: 0.9rem auto 0;
    color: #506078;
    line-height: 1.55;
  }

  .empty-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 2.55rem;
    margin-top: 1.35rem;
    padding: 0 1.05rem;
    border: 1px solid #000;
    border-radius: 20px;
    background: #000;
    color: #fff;
    font-size: 0.88rem;
    font-weight: 700;
    transition: transform 150ms ease, background 150ms ease, border-color 150ms ease;
  }

  .empty-action:hover {
    transform: translateY(-1px);
    border-color: #1f2937;
    background: #1f2937;
  }

  .empty-action:focus-visible {
    outline: 2px solid var(--wn-accent);
    outline-offset: 2px;
  }

  .close-button:focus-visible {
    outline: 2px solid var(--wn-accent);
    outline-offset: 2px;
  }

  .error-copy {
    margin: 0.6rem 0 0;
    color: #be123c;
    font-size: 0.86rem;
    font-weight: 620;
  }

  .dialog-loading {
    padding: 0.82rem;
    gap: 1.25rem;
  }

  .loading-visual,
  .loading-copy span {
    border-radius: 8px;
    background: linear-gradient(90deg, #eef1f7 0%, #f7f8fb 48%, #eef1f7 100%);
    background-size: 220% 100%;
    animation: loadingSweep 1.1s ease-in-out infinite;
  }

  .loading-copy {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 1rem;
    padding-right: 1rem;
  }

  .loading-copy span {
    display: block;
    height: 1rem;
  }

  .loading-copy span:first-child {
    width: 78%;
    height: 3.2rem;
  }

  .loading-copy span:nth-child(2) {
    width: 94%;
  }

  .loading-copy span:nth-child(3) {
    width: 62%;
  }

  @keyframes backdropIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes dialogIn {
    from {
      opacity: 0;
      transform: translateY(10px) scale(0.985);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @keyframes loadingSweep {
    0% { background-position: 120% 0; }
    100% { background-position: -120% 0; }
  }

  @media (max-width: 760px) {
    .dialog-wrap {
      align-items: flex-end;
      padding: 0.75rem;
    }

    .whats-new-dialog {
      width: min(100%, calc(100vw - 1.5rem));
      height: auto;
      max-height: calc(100vh - 1.5rem);
    }

    .dialog-loading {
      grid-template-columns: 1fr;
      min-height: 0;
    }

    .empty-state h2 {
      font-size: clamp(1.55rem, 7.5vw, 2.25rem);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .dialog-backdrop,
    .whats-new-dialog,
    .loading-visual,
    .loading-copy span {
      animation: none;
      transition: none;
    }

    .empty-action:hover,
    .close-button:hover {
      transform: none;
    }
  }
</style>
