<script>
  import { onMount } from 'svelte';
  import { partnersAPI } from '../../lib/api.js';

  let partners = $state([]);
  let loading = $state(true);

  onMount(async () => {
    try {
      const response = await partnersAPI.listAll({ ordering: 'display_order', show_in_overview: true });
      const data = response.data || [];
      partners = data
        .map((partner) => ({
          ...partner,
          marqueeLogoUrl: partner.overview_logo_url || '',
        }))
        .filter((partner) => partner.marqueeLogoUrl);
    } catch (err) {
      partners = [];
    } finally {
      loading = false;
    }
  });

  // Two rows: even indexes scroll one way, odd indexes the other.
  const evenRow = $derived(partners.filter((_, i) => i % 2 === 0));
  const oddRow = $derived(partners.filter((_, i) => i % 2 === 1));
  // Tripled so the loop is seamless.
  const triple = (arr) => [...arr, ...arr, ...arr];
</script>

{#if loading || partners.length > 0}
  <section class="logo-marquee" aria-label="Ecosystem partner logos">
    {#if loading}
      <div class="rows">
        {#each [0, 1] as _row}
          <div class="logo-track">
            {#each [1, 2, 3, 4, 5, 6, 7, 8] as _}
              <div class="logo-skeleton"></div>
            {/each}
          </div>
        {/each}
      </div>
    {:else}
      <div class="rows">
        {#if evenRow.length}
          <div class="logo-track" style={`--partner-count: ${evenRow.length};`}>
            {#each triple(evenRow) as partner, index}
              <a
                href={partner.website_url}
                target="_blank"
                rel="noopener noreferrer"
                class="logo-item"
                aria-label={partner.name}
              >
                <img src={partner.marqueeLogoUrl} alt={partner.name} loading={index >= evenRow.length ? 'lazy' : 'eager'} />
              </a>
            {/each}
          </div>
        {/if}
        {#if oddRow.length}
          <div class="logo-track reverse" style={`--partner-count: ${oddRow.length};`}>
            {#each triple(oddRow) as partner, index}
              <a
                href={partner.website_url}
                target="_blank"
                rel="noopener noreferrer"
                class="logo-item"
                aria-label={partner.name}
              >
                <img src={partner.marqueeLogoUrl} alt={partner.name} loading={index >= oddRow.length ? 'lazy' : 'eager'} />
              </a>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </section>
{/if}

<style>
  .logo-marquee {
    background: #fff;
    border: 1px solid #ececf0;
    border-radius: 8px;
    overflow: hidden;
    padding: 20px 0;
    position: relative;
  }

  .logo-marquee::before,
  .logo-marquee::after {
    bottom: 0;
    content: '';
    pointer-events: none;
    position: absolute;
    top: 0;
    width: 72px;
    z-index: 2;
  }

  .logo-marquee::before {
    background: linear-gradient(90deg, #fff, rgba(255, 255, 255, 0));
    left: 0;
  }

  .logo-marquee::after {
    background: linear-gradient(90deg, rgba(255, 255, 255, 0), #fff);
    right: 0;
  }

  .rows {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .logo-track {
    animation: logo-scroll calc(max(var(--partner-count), 5) * 6s) linear infinite;
    display: flex;
    gap: 28px;
    width: max-content;
    will-change: transform;
  }

  /* Second row travels the opposite direction. */
  .logo-track.reverse {
    animation-direction: reverse;
  }

  .logo-marquee:hover .logo-track {
    animation-play-state: paused;
  }

  .logo-item,
  .logo-skeleton {
    align-items: center;
    display: flex;
    flex: 0 0 148px;
    height: 44px;
    justify-content: center;
  }

  .logo-item img {
    display: block;
    /* brightness(0) flattens every logo (incl. white-on-transparent ones) to a black silhouette;
       opacity softens it to grey on the light band. */
    filter: brightness(0);
    max-height: 30px;
    max-width: 132px;
    object-fit: contain;
    opacity: 0.5;
    transition: opacity 160ms ease;
  }

  .logo-item:hover img {
    opacity: 0.85;
  }

  .logo-skeleton {
    animation: shimmer 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #f2f3f5, #fbfbfc, #f2f3f5);
    background-size: 200% 100%;
    border-radius: 8px;
  }

  @keyframes logo-scroll {
    from {
      transform: translateX(0);
    }
    to {
      transform: translateX(-33.333%);
    }
  }

  @keyframes shimmer {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .logo-track,
    .logo-skeleton {
      animation: none;
    }

    .logo-marquee {
      overflow-x: auto;
    }
  }

  @media (max-width: 620px) {
    .logo-marquee {
      padding: 14px 0;
    }

    .logo-marquee::before,
    .logo-marquee::after {
      width: 38px;
    }

    .rows {
      gap: 12px;
    }

    .logo-track {
      gap: 18px;
    }

    .logo-item,
    .logo-skeleton {
      flex-basis: 124px;
      height: 40px;
    }

    .logo-item img {
      max-height: 26px;
      max-width: 108px;
    }
  }
</style>
