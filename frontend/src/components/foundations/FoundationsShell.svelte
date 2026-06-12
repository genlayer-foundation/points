<script>
  import { onMount } from 'svelte';

  /**
   * Shared frame for the Foundations documents (Manifesto / Compass / Whitepaper).
   * Renders the inner document sidebar (col 2), the mobile pill topbar, and the
   * scrolling content column, and owns the scrollspy + scroll-reveal observers.
   */
  let {
    current = 'compass', // 'manifesto' | 'compass' | 'whitepaper'
    toc = [], // [{ id, label, icon }] — icon is an inline <svg> string
    tocTitle = 'On this page',
    about = null, // { title, text } — replaces the TOC (whitepaper)
    footLinks = [{ label: 'genlayer.com', href: 'https://genlayer.com', icon: 'arrow' }],
    topbarBrand = '',
    topbarItems = [], // [{ kind: 'section', id, label } | { kind: 'doc', key, label }]
    children,
  } = $props();

  const DOCS = [
    { key: 'manifesto', label: 'Manifesto', href: '#/genesis/manifesto' },
    { key: 'compass', label: 'The Compass', href: '#/genesis/compass' },
    { key: 'whitepaper', label: 'Whitepaper', href: '#/genesis/whitepaper' },
  ];

  function docHref(key) {
    return DOCS.find((d) => d.key === key)?.href ?? '#/genesis';
  }

  let scrollEl = $state(null);
  let activeSection = $state(toc[0]?.id ?? '');

  function scrollToSection(id) {
    const el = scrollEl?.querySelector(`#${id}`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function scrollToTop() {
    scrollEl?.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onMount(() => {
    // Scrollspy — keeps the sidebar TOC and mobile topbar in sync with reading position
    let spy;
    if (toc.length && 'IntersectionObserver' in window) {
      spy = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) activeSection = e.target.id;
          });
        },
        { root: scrollEl, rootMargin: '-15% 0px -70% 0px' }
      );
      toc.forEach((item) => {
        const el = scrollEl?.querySelector(`#${item.id}`);
        if (el) spy.observe(el);
      });
    }

    // Scroll reveal — .reveal / .reveal-stagger blocks fade in as they enter the viewport
    const reveals = Array.from(scrollEl?.querySelectorAll('.reveal, .reveal-stagger') ?? []);
    let revealObserver;
    if (!('IntersectionObserver' in window)) {
      reveals.forEach((el) => el.classList.add('in'));
    } else {
      revealObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add('in');
              setTimeout(() => e.target.classList.add('settled'), 1100);
              revealObserver.unobserve(e.target);
            }
          });
        },
        { threshold: 0.05 }
      );
      reveals.forEach((el) => revealObserver.observe(el));
    }

    return () => {
      spy?.disconnect();
      revealObserver?.disconnect();
    };
  });
</script>

<div class="fd-root">
  <!-- Col 2 — documents + index -->
  <aside class="fd-sidebar">
    <div class="nav-label">Foundations</div>
    <ul class="nav-list">
      <li>
        <a href={docHref('manifesto')} class:current={current === 'manifesto'}>
          <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17V5a2 2 0 0 0-2-2H4" /><path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3" /><path d="M15 8h-5" /><path d="M15 12h-5" /></svg>
          Manifesto</a>
      </li>
      <li>
        <a href={docHref('compass')} class:current={current === 'compass'}>
          <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></svg>
          The Compass</a>
      </li>
      <li>
        <a href={docHref('whitepaper')} class:current={current === 'whitepaper'}>
          <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>
          Whitepaper</a>
      </li>
    </ul>

    <div class="nav-sep"></div>
    {#if about}
      <div class="nav-label">About this document</div>
      <div class="wp-about">
        <strong>{about.title}</strong>
        {about.text}
      </div>
    {:else if toc.length}
      <div class="nav-label">{tocTitle}</div>
      <nav aria-label={tocTitle}>
        <ul class="nav-list">
          {#each toc as item (item.id)}
            <li>
              <button
                type="button"
                class:current={activeSection === item.id}
                onclick={() => scrollToSection(item.id)}
              >
                {@html item.icon}
                {item.label}{#if item.num}<span class="nav-num">{item.num}</span>{/if}
              </button>
            </li>
          {/each}
        </ul>
      </nav>
    {/if}

    <div class="sidebar-foot">
      <div class="nav-sep"></div>
      <ul class="nav-list util">
        {#each footLinks as link (link.href)}
          <li>
            <a href={link.href} target="_blank" rel="noopener">
              {#if link.icon === 'help'}
                <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
              {:else}
                <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7" /><polyline points="7 7 17 7 17 17" /></svg>
              {/if}
              {link.label}</a>
          </li>
        {/each}
      </ul>
    </div>
  </aside>

  <!-- Col 3 — content -->
  <div class="fd-content" bind:this={scrollEl}>
    <!-- Mobile pill topbar -->
    <header class="topbar">
      <button type="button" class="tb-brand" onclick={scrollToTop}>
        <span class="tb-mark">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none"><path d="M8 1.5 L9.6 8 L8 14.5 L6.4 8 Z" fill="#8b5cf6" /></svg>
        </span>
        {topbarBrand}
      </button>
      <nav class="tb-nav" aria-label="Sections">
        {#each topbarItems as item, i (i)}
          {#if item.kind === 'doc'}
            <a href={docHref(item.key)} class:current={item.key === current}>{item.label}</a>
          {:else}
            <button
              type="button"
              class:current={activeSection === item.id}
              onclick={() => scrollToSection(item.id)}
            >
              {item.label}
            </button>
          {/if}
        {/each}
      </nav>
    </header>

    {@render children?.()}
  </div>
</div>

<style>
  .fd-root {
    --sidebar-w: 224px;
    display: flex;
    height: 100%;
    background: #f9fafb;
  }
  @media (min-width: 1800px) {
    .fd-root {
      --sidebar-w: 240px;
    }
  }

  /* ============ Document index sidebar (col 2) ============ */
  .fd-sidebar {
    width: var(--sidebar-w);
    flex-shrink: 0;
    height: 100%;
    background: #fbfbfc;
    border-right: 1px solid #e6e6e6;
    display: flex;
    flex-direction: column;
    padding: 14px 12px 12px;
    overflow-y: auto;
  }

  .nav-label {
    font-size: 12px;
    font-weight: 400;
    color: #6b6b6b;
    letter-spacing: 0.24px;
    padding: 16px 12px 6px;
  }
  .nav-list {
    list-style: none;
    display: flex;
    flex-direction: column;
    gap: 1px;
    margin: 0;
    padding: 0;
  }
  .nav-list a,
  .nav-list button {
    display: flex;
    align-items: center;
    gap: 11px;
    width: 100%;
    padding: 9px 12px;
    border-radius: 9px;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.28px;
    color: #131214;
    text-decoration: none;
    background: none;
    border: 0;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    transition:
      background 0.13s ease,
      color 0.13s ease;
  }
  .nav-list :global(svg) {
    flex-shrink: 0;
    width: 17px;
    height: 17px;
    stroke: #3a3a3a;
    fill: none;
  }
  .nav-list .nav-num {
    display: none;
  }
  .nav-list a:hover,
  .nav-list button:hover {
    background: #f4f4f5;
  }
  .nav-list a.current,
  .nav-list button.current {
    background: #eeedfb;
    color: #131214;
  }
  .nav-list a.current :global(svg),
  .nav-list button.current :global(svg) {
    stroke: #7c5cff;
  }
  .nav-list.util a {
    color: #656567;
  }
  .nav-list.util a :global(svg) {
    stroke: #9a9a9c;
  }
  .nav-list.util a:hover {
    background: #f4f4f5;
    color: #131214;
  }
  .nav-sep {
    height: 1px;
    background: #e6e6e6;
    margin: 8px 8px;
  }
  .sidebar-foot {
    margin-top: auto;
    padding-top: 8px;
  }

  /* about card in sidebar (whitepaper) */
  .wp-about {
    margin: 12px 8px 0;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px 15px;
    font-size: 12.5px;
    color: #6b7280;
    line-height: 1.55;
  }
  .wp-about strong {
    display: block;
    font-family: 'Geist', system-ui, sans-serif;
    font-size: 13px;
    color: #111827;
    margin-bottom: 4px;
    font-weight: 600;
    letter-spacing: -0.01em;
  }

  /* ============ Content column (col 3) ============ */
  .fd-content {
    flex: 1;
    min-width: 0;
    height: 100%;
    overflow-y: auto;
    scroll-behavior: smooth;
  }
  .fd-content :global(::selection) {
    background: #eeedfb;
    color: #6d4aff;
  }

  /* ============ Mobile pill topbar ============ */
  .topbar {
    display: none;
  }
  @media (max-width: 899.98px) {
    .fd-sidebar {
      display: none;
    }
    .topbar {
      display: flex;
      align-items: center;
      gap: 6px;
      position: sticky;
      top: 0;
      z-index: 40;
      background: rgba(255, 255, 255, 0.88);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-bottom: 1px solid #e5e7eb;
      padding: 10px 16px;
      overflow-x: auto;
      scrollbar-width: none;
    }
    .topbar::-webkit-scrollbar {
      display: none;
    }
    .tb-brand {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
      font-family: 'Geist', system-ui, sans-serif;
      font-weight: 600;
      font-size: 14px;
      color: #111827;
      text-decoration: none;
      padding: 0 10px 0 0;
      margin-right: 4px;
      border: 0;
      border-right: 1px solid #e5e7eb;
      border-radius: 0;
      background: none;
      cursor: pointer;
    }
    .tb-mark {
      width: 26px;
      height: 26px;
      border-radius: 8px;
      background: #131214;
      display: grid;
      place-items: center;
      flex-shrink: 0;
    }
    .tb-nav {
      display: flex;
      gap: 4px;
    }
    .tb-nav a,
    .tb-nav button {
      flex-shrink: 0;
      font-size: 13px;
      font-weight: 500;
      color: #6b7280;
      padding: 6px 13px;
      border-radius: 9999px;
      text-decoration: none;
      white-space: nowrap;
      background: none;
      border: 0;
      cursor: pointer;
      font-family: inherit;
    }
    .tb-nav a:hover,
    .tb-nav button:hover {
      background: #f3f4f6;
      color: #111827;
    }
    .tb-nav a.current,
    .tb-nav button.current {
      background: #eeedfb;
      color: #5b3df5;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .fd-content {
      scroll-behavior: auto;
    }
  }
</style>
