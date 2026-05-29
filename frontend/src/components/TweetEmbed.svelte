<script>
  import { getXPostUrl } from '../lib/xPost.js';

  let { url, description = '', compact = false } = $props();

  let container = $state(null);
  let loaded = $state(false);
  let failed = $state(false);

  let post = $derived(getXPostUrl(url));
  let embedUrl = $derived(post?.url || url);

  let widgetsPromise = null;

  function waitForWidgets() {
    if (window.twttr?.widgets) return Promise.resolve(window.twttr);
    if (widgetsPromise) return widgetsPromise;

    widgetsPromise = new Promise((resolve, reject) => {
      const existingScript = document.querySelector('script[src="https://platform.twitter.com/widgets.js"]');
      if (!existingScript) {
        const script = document.createElement('script');
        script.src = 'https://platform.twitter.com/widgets.js';
        script.async = true;
        script.charset = 'utf-8';
        script.onerror = () => reject(new Error('Failed to load X embed script'));
        document.head.appendChild(script);
      }

      const startedAt = Date.now();
      const interval = window.setInterval(() => {
        if (window.twttr?.widgets) {
          window.clearInterval(interval);
          resolve(window.twttr);
        } else if (Date.now() - startedAt > 10000) {
          window.clearInterval(interval);
          reject(new Error('Timed out loading X embed script'));
        }
      }, 100);
    });

    return widgetsPromise;
  }

  function buildBlockquote() {
    container.innerHTML = '';

    const blockquote = document.createElement('blockquote');
    blockquote.className = 'twitter-tweet';
    blockquote.setAttribute('data-dnt', 'true');
    blockquote.setAttribute('data-width', compact ? '420' : '550');

    const link = document.createElement('a');
    link.href = embedUrl;
    link.textContent = description || 'View post on X';

    blockquote.appendChild(link);
    container.appendChild(blockquote);
  }

  $effect(() => {
    if (!container || !post || typeof window === 'undefined') return;

    let cancelled = false;
    loaded = false;
    failed = false;
    buildBlockquote();

    waitForWidgets()
      .then((twttr) => twttr.widgets.load(container))
      .then(() => {
        if (cancelled) return;
        loaded = Boolean(container.querySelector('iframe'));
        failed = !loaded;
      })
      .catch(() => {
        if (cancelled) return;
        failed = true;
        loaded = false;
      });

    return () => {
      cancelled = true;
    };
  });
</script>

<div class="tweet-shell" class:tweet-shell-compact={compact} class:tweet-loaded={loaded} class:tweet-failed={failed}>
  {#if !loaded && !failed}
    <div class="tweet-skeleton" aria-hidden="true">
      <div class="tweet-skeleton-row">
        <div class="tweet-skeleton-avatar"></div>
        <div class="tweet-skeleton-lines">
          <div></div>
          <div></div>
        </div>
      </div>
      <div class="tweet-skeleton-body"></div>
      <div class="tweet-skeleton-body short"></div>
    </div>
  {/if}

  <div bind:this={container} class="tweet-container" class:tweet-container-hidden={!loaded || failed}></div>

  {#if failed}
    <a href={embedUrl} target="_blank" rel="noopener noreferrer" class="tweet-fallback">
      <span>{description || 'View post on X'}</span>
      <svg class="tweet-fallback-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 17L17 7M17 7H7M17 7V17" />
      </svg>
    </a>
  {/if}
</div>

<style>
  .tweet-shell {
    width: 100%;
    max-width: 550px;
    min-width: 0;
    overflow: hidden;
  }

  .tweet-shell-compact {
    max-width: 420px;
  }

  .tweet-container {
    width: 100%;
    min-width: 0;
    overflow: hidden;
  }

  .tweet-container :global(iframe) {
    max-width: 100% !important;
    min-width: 0 !important;
  }

  .tweet-container-hidden {
    height: 0;
    overflow: hidden;
    visibility: hidden;
  }

  .tweet-skeleton {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #ffffff;
    padding: 14px;
  }

  .tweet-skeleton-row {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .tweet-skeleton-avatar,
  .tweet-skeleton-lines div,
  .tweet-skeleton-body {
    background: linear-gradient(90deg, #f3f4f6 0%, #e5e7eb 50%, #f3f4f6 100%);
    background-size: 200% 100%;
    animation: tweet-pulse 1.2s ease-in-out infinite;
  }

  .tweet-skeleton-avatar {
    width: 34px;
    height: 34px;
    border-radius: 999px;
    flex: 0 0 auto;
  }

  .tweet-skeleton-lines {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .tweet-skeleton-lines div {
    height: 10px;
    border-radius: 999px;
  }

  .tweet-skeleton-lines div:first-child {
    width: 42%;
  }

  .tweet-skeleton-lines div:last-child {
    width: 28%;
  }

  .tweet-skeleton-body {
    height: 12px;
    border-radius: 999px;
    margin-top: 14px;
  }

  .tweet-skeleton-body.short {
    width: 72%;
    margin-top: 8px;
  }

  .tweet-fallback {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #ffffff;
    color: #111827;
    font-size: 14px;
    font-weight: 500;
    line-height: 20px;
    padding: 12px 14px;
    text-decoration: none;
  }

  .tweet-fallback:hover {
    background: #f9fafb;
  }

  .tweet-fallback-icon {
    width: 16px;
    height: 16px;
    flex: 0 0 auto;
    color: #6b7280;
  }

  @keyframes tweet-pulse {
    0% {
      background-position: 100% 0;
    }
    100% {
      background-position: -100% 0;
    }
  }
</style>
