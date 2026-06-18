<script>
  import { AUDIENCE_META } from '../lib/whatsNewPresentation.js';

  let {
    slide,
    dialogEl = $bindable(null),
    labelledby = 'whats-new-title',
    showClose = false,
    closeLabel = "Close What's New",
    onClose = () => {},
    totalSlides = 1,
    currentIndex = 0,
    currentProgress = '',
    primaryLabel = 'Done',
    showSkip = false,
    onSkip = () => {},
    onPrimary = () => {},
    onOpenLink = () => {},
    error = '',
  } = $props();

  let progressText = $derived(currentProgress || `${currentIndex + 1} of ${totalSlides}`);
  let styleVars = $derived(
    `--wn-accent: ${slide?.accent || '#19A663'}; --wn-gradient: ${slide?.gradient || AUDIENCE_META.all.gradient};`
  );
</script>

{#if slide}
  <div
    class="whats-new-dialog"
    role="dialog"
    aria-modal="true"
    aria-labelledby={labelledby}
    tabindex="-1"
    bind:this={dialogEl}
    style={styleVars}
  >
    {#if showClose}
      <button
        type="button"
        class="close-button"
        aria-label={closeLabel}
        onclick={onClose}
      >
        <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
      </button>
    {/if}

    <div class="dialog-grid">
      <div class="visual-pane">
        <div class="visual-header">
          <span class="eyebrow-label">{slide.eyebrow}</span>
          {#if slide.showCommunityBadge}
            <span class="community-badge">{slide.audienceLabel}</span>
          {/if}
        </div>
        <div class="image-stage">
          <img src={slide.image} alt="" loading="lazy" />
        </div>
        {#if slide.linkUrl}
          <button type="button" class="image-link-action" onclick={onOpenLink}>
            {slide.linkLabel}
          </button>
        {/if}
      </div>

      <div class="copy-pane">
        <div class="copy-heading">
          {#if totalSlides > 1}
            <div class="copy-topline">
              <span class="progress-pill">{progressText}</span>
            </div>
          {/if}

          <h2 id={labelledby}>{slide.title}</h2>
        </div>
        <div class="slide-body">{@html slide.bodyHtml}</div>

        {#if error}
          <p class="error-copy">{error}</p>
        {/if}

        <div class="dialog-footer">
          {#if totalSlides > 1}
            <div class="step-dots" aria-label="Announcement progress">
              {#each Array(totalSlides) as _, index}
                <span class:active={index === currentIndex}></span>
              {/each}
            </div>
          {:else}
            <span class="footer-spacer" aria-hidden="true"></span>
          {/if}
          <div class="dialog-actions">
            {#if showSkip}
              <button type="button" class="secondary-action" onclick={onSkip}>
                Skip
              </button>
            {/if}
            <button type="button" class="primary-action" onclick={onPrimary}>
              {primaryLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .whats-new-dialog {
    position: relative;
    width: min(56rem, calc(100vw - 2rem));
    height: min(36rem, calc(100vh - 2rem));
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

  .dialog-grid {
    display: grid;
    grid-template-columns: minmax(22rem, 1.04fr) minmax(21rem, 0.96fr);
    height: 100%;
    min-height: 29rem;
  }

  .visual-pane {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 0.78rem;
    padding: 0.82rem;
    border-right: 1px solid rgba(238, 241, 246, 0.72);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.38));
  }

  .visual-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    min-height: 1.875rem;
    color: #506078;
    font-size: 0.75rem;
    font-weight: 650;
  }

  .visual-header .eyebrow-label {
    display: inline-flex;
    align-items: center;
    min-height: 1.75rem;
    padding: 0 0.65rem;
    border: 1px solid rgba(224, 229, 239, 0.92);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.9);
    color: #8a94a7;
    white-space: nowrap;
  }

  .community-badge,
  .progress-pill {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    border: 1px solid #e0e5ef;
    border-radius: 999px;
    background: #fff;
    color: #506078;
    white-space: nowrap;
  }

  .community-badge {
    min-height: 1.75rem;
    padding: 0 0.65rem;
  }

  .image-stage {
    position: relative;
    flex: 1;
    min-height: 21rem;
    overflow: hidden;
    border: 1px solid transparent;
    border-radius: 12px;
    background:
      linear-gradient(#eef1f7, #eef1f7) padding-box,
      var(--wn-gradient) border-box;
  }

  .image-stage img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 500ms ease;
  }

  .whats-new-dialog:hover .image-stage img {
    transform: scale(1.01);
  }

  .image-link-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    min-height: 2.45rem;
    width: 100%;
    border: 1px solid rgba(224, 229, 239, 0.9);
    border-radius: 999px;
    padding: 0.45rem 0.9rem;
    color: var(--wn-accent);
    background: rgba(255, 255, 255, 0.82);
    font-size: 0.86rem;
    font-weight: 700;
    line-height: 1.18;
    text-align: center;
    overflow-wrap: anywhere;
    transition: transform 150ms ease, background 150ms ease, border-color 150ms ease, color 150ms ease;
  }

  .image-link-action:hover {
    transform: translateY(-1px);
    border-color: #cdd5e3;
    color: #111827;
    background: #fff;
  }

  .copy-pane {
    display: grid;
    grid-template-rows: auto minmax(0, 1fr) auto auto;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    padding: 1.75rem 1.6rem 1.15rem;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.54));
  }

  .copy-heading {
    min-width: 0;
  }

  .copy-topline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin-bottom: 0.82rem;
    color: #8a94a7;
    font-size: 0.74rem;
    font-weight: 600;
  }

  .progress-pill {
    min-height: 1.7rem;
    padding: 0 0.62rem;
    color: var(--wn-accent);
  }

  .copy-pane h2 {
    margin: 0;
    color: #000;
    font-family: var(--font-display);
    font-size: clamp(1.65rem, 3vw, 2.7rem);
    font-weight: 650;
    letter-spacing: 0;
    line-height: 1;
  }

  .slide-body {
    min-height: 0;
    margin-top: 0.82rem;
    overflow-y: auto;
    padding-right: 0.2rem;
    color: #506078;
    font-size: 0.9rem;
    line-height: 1.55;
  }

  .slide-body :global(p + p) {
    margin-top: 0.7rem;
  }

  .slide-body :global(a) {
    color: #0284c7;
    text-decoration: underline;
    text-decoration-thickness: 1px;
    text-underline-offset: 3px;
  }

  .slide-body :global(ul),
  .slide-body :global(ol) {
    margin-top: 0.7rem;
    padding-left: 1.2rem;
  }

  .slide-body :global(ul) {
    list-style: disc;
  }

  .slide-body :global(ol) {
    list-style: decimal;
  }

  .dialog-footer {
    display: flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    min-width: 0;
    margin-top: auto;
    padding-top: 1rem;
  }

  .dialog-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.55rem;
    min-width: 0;
    max-width: 100%;
    flex: 0 1 auto;
    flex-wrap: wrap;
  }

  .footer-spacer {
    min-width: 0;
    flex: 1 1 auto;
  }

  .step-dots {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.34rem;
    min-width: 0;
    flex: 1 1 7rem;
    max-width: 12rem;
  }

  .step-dots span {
    width: 0.45rem;
    height: 0.45rem;
    border-radius: 999px;
    background: #d9dee9;
    transition: width 160ms ease, background 160ms ease;
  }

  .step-dots span.active {
    width: 1.35rem;
    background: var(--wn-accent);
  }

  .primary-action,
  .secondary-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 0;
    min-height: 2.5rem;
    max-width: 100%;
    border-radius: 20px;
    padding: 0.45rem 1rem;
    font-size: 0.88rem;
    font-weight: 650;
    line-height: 1.12;
    text-align: center;
    white-space: normal;
    overflow-wrap: anywhere;
    transition: transform 150ms ease, background 150ms ease, border-color 150ms ease, color 150ms ease;
  }

  .primary-action {
    border: 1px solid #000;
    color: #fff;
    background: #000;
  }

  .primary-action:hover {
    background: #1f2937;
    border-color: #1f2937;
  }

  .secondary-action {
    border: 1px solid #e0e5ef;
    color: #506078;
    background: #fff;
  }

  .secondary-action:hover {
    border-color: #cdd5e3;
    color: #111827;
    background: #f7f8fb;
  }

  .primary-action:hover,
  .secondary-action:hover {
    transform: translateY(-1px);
  }

  .primary-action:focus-visible,
  .secondary-action:focus-visible,
  .image-link-action:focus-visible,
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

  @media (max-width: 760px) {
    .whats-new-dialog {
      width: min(100%, calc(100vw - 1.5rem));
      height: auto;
      max-height: calc(100vh - 1.5rem);
    }

    .dialog-grid {
      grid-template-columns: 1fr;
      height: auto;
      min-height: 0;
    }

    .visual-pane {
      border-right: 0;
      border-bottom: 1px solid #eef1f6;
    }

    .image-stage {
      min-height: 9.5rem;
      max-height: 12.5rem;
    }

    .copy-pane {
      min-height: 0;
      max-height: min(25rem, calc(100vh - 17rem));
      padding: 1.18rem 1.08rem 0.95rem;
    }

    .copy-pane h2 {
      font-size: clamp(1.55rem, 7.5vw, 2.25rem);
    }

    .copy-topline,
    .dialog-footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .step-dots {
      max-width: 100%;
    }

    .dialog-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .primary-action,
    .secondary-action {
      flex: 1 1 0;
      padding-inline: 0.75rem;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .whats-new-dialog,
    .image-stage img {
      animation: none;
      transition: none;
    }

    .primary-action:hover,
    .image-link-action:hover,
    .secondary-action:hover,
    .close-button:hover,
    .whats-new-dialog:hover .image-stage img {
      transform: none;
    }
  }
</style>
