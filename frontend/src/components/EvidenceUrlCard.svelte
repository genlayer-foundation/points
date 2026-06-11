<script>
  import TweetEmbed from './TweetEmbed.svelte';
  import { getXPostUrl } from '../lib/xPost.js';
  import { isSafeHttpUrl } from '../lib/urlSafety.js';

  /**
   * @typedef {{
   *   description?: string,
   *   url?: string,
   *   url_type?: { name?: string } | null
   * }} EvidenceItem
   */

  /** @type {{ evidence: EvidenceItem, compact?: boolean }} */
  let { evidence, compact = false } = $props();

  let showPreview = $state(false);
  let previewUnavailable = $state(false);
  let lastUrl = $state('');

  let url = $derived(evidence?.url || '');
  let post = $derived(getXPostUrl(url));
  let canPreview = $derived(Boolean(post) && !previewUnavailable);
  let typeLabel = $derived(evidence?.url_type?.name || 'Evidence URL');
  let description = $derived(
    evidence?.description && evidence.description !== typeLabel
      ? evidence.description
      : ''
  );

  $effect(() => {
    if (url === lastUrl) return;
    lastUrl = url;
    showPreview = false;
    previewUnavailable = false;
  });

  function handlePreviewClick() {
    showPreview = true;
  }

  function handlePreviewError() {
    showPreview = false;
    previewUnavailable = true;
  }
</script>

<div class="evidence-url-card" class:evidence-url-card-compact={compact}>
  <div class="evidence-url-header">
    <span class="evidence-url-type">{typeLabel}</span>
    {#if canPreview}
      <button
        type="button"
        class="evidence-preview-button"
        aria-expanded={showPreview}
        onclick={handlePreviewClick}
      >
        Preview
      </button>
    {/if}
  </div>

  {#if description}
    <p class="evidence-url-description">{description}</p>
  {/if}

  {#if isSafeHttpUrl(url)}
    <a href={url} target="_blank" rel="noopener noreferrer" class="evidence-url-link">
      {url}
    </a>
  {:else}
    <!-- Non-http(s) URLs are shown as plain text, never as a link target -->
    <span class="evidence-url-link">{url}</span>
  {/if}

  {#if showPreview && canPreview}
    <div class="evidence-preview">
      <TweetEmbed
        {url}
        description={description || typeLabel}
        {compact}
        showFallback={false}
        onError={handlePreviewError}
      />
    </div>
  {/if}
</div>

<style>
  .evidence-url-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
    width: 100%;
    min-width: 0;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #ffffff;
    padding: 12px 14px;
  }

  .evidence-url-card-compact {
    padding: 10px 12px;
  }

  .evidence-url-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-width: 0;
  }

  .evidence-url-type {
    min-width: 0;
    color: #374151;
    font-size: 12px;
    font-weight: 600;
    line-height: 16px;
  }

  .evidence-preview-button {
    flex: 0 0 auto;
    border: 1px solid #d1d5db;
    border-radius: 999px;
    background: #ffffff;
    color: #111827;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    line-height: 16px;
    padding: 4px 10px;
    transition: background 120ms ease, border-color 120ms ease;
  }

  .evidence-preview-button:hover {
    background: #f9fafb;
    border-color: #9ca3af;
  }

  .evidence-url-link {
    color: #2563eb;
    font-size: 13px;
    line-height: 18px;
    overflow-wrap: anywhere;
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .evidence-url-description {
    color: #111827;
    font-size: 13px;
    font-weight: 500;
    line-height: 18px;
    margin: 0;
    overflow-wrap: anywhere;
  }

  .evidence-url-link:hover {
    color: #1d4ed8;
  }

  .evidence-preview {
    margin-top: 2px;
  }
</style>
