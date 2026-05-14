<script>
  import { onMount } from 'svelte';
  import { featuredAPI } from '../lib/api.js';

  /**
   * @typedef {Object} FeaturedContent
   * @property {string | number} [id]
   * @property {string} [content_type]
   * @property {string} [title]
   * @property {string} [description]
   * @property {string} [author]
   * @property {string} [user_name]
   * @property {string} [hero_image_url]
   * @property {string} [hero_image_url_tablet]
   * @property {string} [hero_image_url_mobile]
   * @property {string} [link]
   * @property {string} [url]
   * @property {string} [created_at]
   */

  /**
   * @typedef {Object} Announcement
   * @property {string} id
   * @property {string} title
   * @property {string} description
   * @property {string} author
   * @property {string} image
   * @property {string} imageTablet
   * @property {string} imageMobile
   * @property {string} href
   * @property {boolean} external
   * @property {string} dateLabel
   * @property {number} createdAt
   */

  /** @type {Announcement[]} */
  let announcements = $state([]);
  let loading = $state(true);

  let featured = $derived(announcements[0] || null);
  let listAnnouncements = $derived(announcements.slice(1));

  /**
   * @param {any} maybe
   * @returns {FeaturedContent[]}
   */
  function asArray(maybe) {
    if (Array.isArray(maybe)) return maybe;
    if (Array.isArray(maybe?.results)) return maybe.results;
    return [];
  }

  /**
   * @param {string | undefined} dateString
   * @returns {string}
   */
  function formatDate(dateString) {
    if (!dateString) return '';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return '';
    }
  }

  /**
   * @param {string | undefined} dateString
   * @returns {number}
   */
  function getTimestamp(dateString) {
    if (!dateString) return 0;
    const timestamp = new Date(dateString).getTime();
    return Number.isNaN(timestamp) ? 0 : timestamp;
  }

  /**
   * @param {FeaturedContent} item
   * @returns {string}
   */
  function getLink(item) {
    const raw = item?.link || item?.url || '#';
    if (raw.startsWith('/')) return `#${raw}`;
    return raw;
  }

  /**
   * @param {string} href
   * @returns {boolean}
   */
  function isExternalLink(href) {
    return href.startsWith('http://') || href.startsWith('https://');
  }

  /**
   * @param {FeaturedContent} item
   * @param {string} fallbackType
   * @returns {Announcement}
   */
  function normalizeAnnouncement(item, fallbackType) {
    const contentType = item.content_type || fallbackType;
    const href = getLink(item);

    return {
      id: `${contentType}-${item.id || item.title || href}`,
      title: item.title || 'Announcement',
      description: item.description || '',
      author: item.author || item.user_name || 'GenLayer',
      image: item.hero_image_url || item.hero_image_url_tablet || item.hero_image_url_mobile || '',
      imageTablet: item.hero_image_url_tablet || item.hero_image_url || item.hero_image_url_mobile || '',
      imageMobile: item.hero_image_url_mobile || item.hero_image_url_tablet || item.hero_image_url || '',
      href,
      external: isExternalLink(href),
      dateLabel: formatDate(item.created_at),
      createdAt: getTimestamp(item.created_at),
    };
  }

  /**
   * @param {Announcement[]} items
   * @returns {Announcement[]}
   */
  function dedupeById(items) {
    const seen = new Set();
    return items.filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    });
  }

  onMount(async () => {
    try {
      const heroRes = await featuredAPI.getHero();
      const fetchedAnnouncements = dedupeById(
        asArray(heroRes.data).map((item) => normalizeAnnouncement(item, 'hero'))
      );
      announcements = fetchedAnnouncements.sort((a, b) => b.createdAt - a.createdAt);
    } catch {
      announcements = [];
    } finally {
      loading = false;
    }
  });
</script>

<div class="relative -mx-3 -my-3 overflow-hidden px-3 py-8 sm:px-5 sm:py-10 md:px-8 md:py-12">
  <div
    class="pointer-events-none absolute inset-x-0 top-0 h-[320px] overflow-hidden"
    style="-webkit-mask-image: linear-gradient(to bottom, black 0%, transparent 100%); mask-image: linear-gradient(to bottom, black 0%, transparent 100%);"
  >
    <img
      src="/assets/illustrations/welcome-gradient.png"
      alt=""
      class="absolute inset-0 h-full w-full object-cover opacity-70"
    />
    <div class="absolute inset-0 bg-white/25"></div>
  </div>

  <div class="relative z-10 space-y-6">
    <header class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div class="space-y-2">
        <h1
          class="font-display text-[34px] font-semibold leading-none text-black sm:text-[40px] md:text-[46px]"
          style="letter-spacing: 0;"
        >
          GenNews
        </h1>
        <p class="max-w-2xl text-[14px] text-[#3f4b5f] sm:text-[15px]" style="letter-spacing: 0;">
          Latest announcements from the GenLayer ecosystem.
        </p>
      </div>

      {#if !loading && announcements.length > 0}
        <span class="inline-flex h-[30px] w-fit items-center rounded-full border border-[#e0e5ef] bg-white/80 px-3 text-[12px] font-semibold text-[#506078] shadow-[0_6px_16px_rgba(31,42,68,0.06)]">
          {announcements.length} {announcements.length === 1 ? 'announcement' : 'announcements'}
        </span>
      {/if}
    </header>

    {#if loading}
      <section class="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div class="h-[360px] animate-pulse rounded-[8px] border border-white/70 bg-white/72 shadow-[0_18px_55px_rgba(38,48,75,0.14)]"></div>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {#each [1, 2, 3] as _}
            <div class="h-[156px] animate-pulse rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)]"></div>
          {/each}
        </div>
      </section>
    {:else if announcements.length === 0}
      <section class="rounded-[8px] border border-[#e8ebf2] bg-white p-12 text-center shadow-[0_8px_18px_rgba(31,42,68,0.07)]">
        <h2 class="font-heading font-semibold text-black">No announcements yet</h2>
        <p class="mt-1 text-[14px] text-[#6b6b6b]">Hero banner announcements will appear here when available.</p>
      </section>
    {:else}
      <section class="space-y-5">
        <a
          href={featured.href}
          target={featured.external ? '_blank' : undefined}
          rel={featured.external ? 'noopener noreferrer' : undefined}
          class="group block overflow-hidden rounded-[8px] border border-white/70 bg-white/86 shadow-[0_18px_55px_rgba(38,48,75,0.14)] outline-none backdrop-blur-md transition-transform duration-200 hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2"
        >
          <div class="bg-[#f7f8fb]">
            {#if featured.image}
              <picture class="block w-full">
                <source media="(min-width: 1024px)" srcset={featured.image} />
                <source media="(min-width: 768px)" srcset={featured.imageTablet || featured.image} />
                <img
                  src={featured.imageMobile || featured.imageTablet || featured.image}
                  alt=""
                  class="block h-auto max-h-[440px] w-full object-contain transition-transform duration-500 group-hover:scale-[1.005]"
                />
              </picture>
            {:else}
              <div class="flex h-[260px] w-full items-center justify-center bg-gradient-to-br from-[#eef1f7] via-[#dde4ef] to-[#f2c18a]">
                <span class="text-[13px] font-semibold text-[#6b7280]">GenLayer</span>
              </div>
            {/if}
          </div>

          <div class="grid gap-5 border-t border-[#eef1f6] p-5 sm:p-7 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="inline-flex h-7 items-center rounded-full border border-[#e0e5ef] bg-[#f7f8fb] px-3 text-[12px] font-semibold text-[#506078]">
                  Latest
                </span>
                {#if featured.dateLabel}
                  <span class="text-[12px] font-medium text-[#8a94a7]">{featured.dateLabel}</span>
                {/if}
                <span class="text-[12px] font-medium text-[#8a94a7]">By {featured.author}</span>
              </div>
              <h2 class="mt-3 max-w-4xl font-display text-[30px] font-semibold leading-tight text-black sm:text-[38px]" style="letter-spacing: 0;">
                {featured.title}
              </h2>
              {#if featured.description}
                <p class="mt-3 max-w-3xl text-[15px] leading-6 text-[#506078]">
                  {featured.description}
                </p>
              {/if}
            </div>

            <span class="inline-flex h-10 w-fit items-center gap-2 rounded-[20px] bg-black px-4 text-[14px] font-medium text-white transition-colors group-hover:bg-[#1f2937]">
              Open announcement
              <img src="/assets/icons/arrow-right-line.svg" alt="" class="h-4 w-4 brightness-0 invert">
            </span>
          </div>
        </a>

        {#if listAnnouncements.length > 0}
          <div class="space-y-3">
            {#each listAnnouncements as item (item.id)}
              <a
                href={item.href}
                target={item.external ? '_blank' : undefined}
                rel={item.external ? 'noopener noreferrer' : undefined}
                class="group grid overflow-hidden rounded-[8px] border border-[#e8ebf2] bg-white shadow-[0_8px_18px_rgba(31,42,68,0.07)] outline-none transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_26px_rgba(31,42,68,0.12)] focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 md:min-h-[148px] md:grid-cols-[304px_minmax(0,1fr)_180px]"
              >
                <div class="flex items-center border-b border-[#eef1f6] p-3 md:border-b-0 md:border-r-0">
                  <div class="w-full overflow-hidden rounded-[8px] bg-[#f7f8fb] md:w-[280px]">
                    {#if item.image}
                      <picture class="block w-full">
                        <source media="(min-width: 1024px)" srcset={item.image} />
                        <source media="(min-width: 768px)" srcset={item.imageTablet || item.image} />
                        <img
                          src={item.imageMobile || item.imageTablet || item.image}
                          alt=""
                          class="block h-auto max-h-[122px] w-full object-contain transition-transform duration-500 group-hover:scale-[1.01]"
                          loading="lazy"
                        />
                      </picture>
                    {:else}
                      <div class="flex h-[122px] w-full items-center justify-center bg-gradient-to-br from-[#eef1f7] to-[#d9dee9]">
                        <span class="text-[11px] font-semibold text-[#8a94a7]">GenLayer</span>
                      </div>
                    {/if}
                  </div>
                </div>

                <div class="min-w-0 p-4 md:flex md:flex-col md:justify-center md:p-5">
                  <div class="flex flex-wrap items-center gap-2">
                    {#if item.dateLabel}
                      <span class="text-[12px] text-[#8a94a7]">{item.dateLabel}</span>
                    {/if}
                    <span class="text-[12px] text-[#8a94a7]">By {item.author}</span>
                  </div>
                  <h3 class="mt-2 text-[20px] font-semibold leading-snug text-black">
                    {item.title}
                  </h3>
                  {#if item.description}
                    <p
                      class="mt-1 max-w-3xl text-[13px] leading-5 text-[#506078]"
                      style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;"
                    >
                      {item.description}
                    </p>
                  {/if}
                </div>

                <div class="hidden items-center justify-center gap-4 px-5 md:flex">
                  {#if item.dateLabel}
                    <span class="whitespace-nowrap text-[13px] font-medium text-[#8a94a7]">{item.dateLabel}</span>
                  {/if}
                  <span class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[#e0e5ef] bg-[#f7f8fb] transition-colors group-hover:border-[#cdd5e3] group-hover:bg-white">
                    <img src="/assets/icons/arrow-right-s-line.svg" alt="" class="h-4 w-4">
                  </span>
                </div>
              </a>
            {/each}
          </div>
        {/if}
      </section>
    {/if}
  </div>
</div>
