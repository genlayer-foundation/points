<script>
  import { onMount } from 'svelte';
  import FoundationsShell from '../components/foundations/FoundationsShell.svelte';

  const PDF_URL =
    'https://cdn.prod.website-files.com/66c4b3cf581ff27ab26a72bc/66c60f3d7295d3113d4699ba_GenLayer%20Whitepaper_%20The%20Intelligent%20Contract%20Network.pdf#view=FitH';

  const ABOUT = {
    title: 'The Intelligent Contract Network',
    text: 'February 2024, by Albert Castellana, Jose Maria Lago & Edgars Nemse. The founding technical document — Intelligent Contracts, GenVM, Optimistic Democracy, and the Equivalence Principle.',
  };

  const FOOT_LINKS = [
    { label: 'Open on genlayer.com', href: 'https://www.genlayer.com/whitepaper', icon: 'arrow' },
    { label: 'Documentation', href: 'https://docs.genlayer.com', icon: 'help' },
  ];

  const TOPBAR = [
    { kind: 'doc', key: 'compass', label: 'Compass' },
    { kind: 'doc', key: 'manifesto', label: 'Manifesto' },
    { kind: 'doc', key: 'whitepaper', label: 'Whitepaper' },
  ];

  let loaded = $state(false);

  onMount(() => {
    // PDF embeds don't reliably fire `load` in every browser — hide the
    // loader after a short grace period either way.
    const t = setTimeout(() => (loaded = true), 3500);
    return () => clearTimeout(t);
  });
</script>

<FoundationsShell current="whitepaper" about={ABOUT} footLinks={FOOT_LINKS} topbarBrand="Whitepaper" topbarItems={TOPBAR}>
  <div class="fd-page">
    <div class="wp-wrap">
      <div class="wp-bar">
        <div class="wp-bar-title">
          <h1>GenLayer: The Intelligent Contract Network</h1>
          <span class="wp-sub">Whitepaper &middot; February 2024 &middot; loaded from genlayer.com</span>
        </div>
        <div class="wp-bar-actions">
          <a class="wp-btn" href="https://www.genlayer.com/whitepaper" target="_blank" rel="noopener">Open in new tab &#8599;</a>
        </div>
      </div>
      <div class="wp-frame">
        <div class="wp-loading" class:hidden={loaded}>
          <div class="wp-spinner" aria-hidden="true"></div>
          Loading the whitepaper from genlayer.com&hellip;
        </div>
        <iframe src={PDF_URL} title="GenLayer Whitepaper (PDF)" loading="eager" onload={() => (loaded = true)}></iframe>
      </div>
    </div>
  </div>
</FoundationsShell>

<style>
  .fd-page {
    height: 100%;
    padding: 16px 20px;
    font-family: 'Switzer', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  }

  .wp-wrap {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-width: 1480px;
    margin: 0 auto;
  }
  .wp-bar {
    flex: 0 0 auto;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    box-shadow: 0 1px 2px rgba(16, 16, 16, 0.04), 0 1px 3px rgba(16, 16, 16, 0.03);
    padding: 12px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    flex-wrap: wrap;
  }
  .wp-bar-title {
    display: flex;
    align-items: baseline;
    gap: 11px;
    flex-wrap: wrap;
  }
  .wp-bar-title h1 {
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 16.5px;
    font-weight: 600;
    letter-spacing: -0.015em;
    color: #111827;
    margin: 0;
  }
  .wp-bar-title .wp-sub {
    font-size: 13px;
    color: #6b7280;
  }
  .wp-bar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .wp-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    border: 1px solid #e5e7eb;
    border-radius: 9999px;
    background: #fff;
    color: #111827;
    padding: 7px 15px;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none !important;
    transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
  }
  .wp-btn:hover {
    border-color: #ddd9f6;
    background: #fbfaff;
    color: #5b3df5;
  }
  .wp-frame {
    flex: 1;
    position: relative;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    box-shadow: 0 1px 2px rgba(16, 16, 16, 0.04), 0 1px 3px rgba(16, 16, 16, 0.03);
    overflow: hidden;
  }
  .wp-frame iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    background: #fff;
  }
  .wp-loading {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    color: #6b7280;
    font-size: 14px;
    background: #fff;
    transition: opacity 0.4s ease;
  }
  .wp-loading.hidden {
    opacity: 0;
    pointer-events: none;
  }
  .wp-spinner {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    border: 3px solid #eeedfb;
    border-top-color: #7c5cff;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 899.98px) {
    .fd-page {
      padding: 10px;
      /* leave room below the sticky topbar */
      height: auto;
      min-height: 100%;
    }
    .wp-wrap {
      height: calc(100vh - 180px);
      min-height: 420px;
    }
    .wp-bar {
      padding: 10px 14px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .wp-spinner {
      animation: none;
    }
  }
</style>
