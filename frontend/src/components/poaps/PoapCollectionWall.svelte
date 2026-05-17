<script>
  import { push } from 'svelte-spa-router';
  import { format } from 'date-fns';

  let { items = [], density = 'large', showDetails = true, showCaptions = true, showOpenBadge = false } = $props();

  /** @param {any} item */
  function normalizePoap(item) {
    const drop = item?.drop || item || {};
    return {
      key: item?.drop ? `claim-${item.id}` : `drop-${drop.id || drop.slug}`,
      slug: drop.slug,
      title: drop.title || 'POAP',
      description: drop.description || '',
      artworkUrl: drop.artwork_url || '',
      eventStartAt: drop.event_start_at || item?.claimed_at || null,
      claimedAt: item?.claimed_at || null,
      status: drop.status || '',
      hasClaimed: Boolean(drop.has_claimed || item?.claimed_at),
      canClaim: Boolean(drop.can_claim),
      claimState: drop.claim_state || '',
      claimedCount: drop.claimed_count ?? item?.claimed_count ?? null,
      maxClaims: drop.max_claims ?? null,
    };
  }

  /** @param {string | Date | null | undefined} value */
  function toDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  /** @param {string | Date | null | undefined} value */
  function monthKey(value) {
    const date = toDate(value);
    if (!date) return 'unknown';
    return format(date, 'yyyy-MM');
  }

  /** @param {string | Date | null | undefined} value */
  function monthLabel(value) {
    const date = toDate(value);
    if (!date) return 'Unknown date';
    return format(date, 'MMMM yyyy');
  }

  /** @param {string | Date | null | undefined} value */
  function shortDate(value) {
    const date = toDate(value);
    if (!date) return '';
    return format(date, 'MMM d, yyyy');
  }

  /** @param {string} status */
  function statusLabel(status) {
    if (status === 'active') return 'Live';
    if (status === 'archived') return 'Archived';
    if (status === 'draft') return 'Draft';
    return status;
  }

  /** @param {any} poap */
  function metaLabel(poap) {
    if (poap.claimedAt) return `Claimed ${shortDate(poap.claimedAt)}`;
    if (poap.maxClaims) return `${poap.claimedCount || 0} of ${poap.maxClaims} claimed`;
    if (poap.claimedCount !== null && poap.claimedCount !== undefined) return `${poap.claimedCount} claimed`;
    return statusLabel(poap.status) || shortDate(poap.eventStartAt);
  }

  /** @param {any} poap */
  function isOpen(poap) {
    return poap.canClaim || poap.claimState === 'live';
  }

  /** @param {any} poap */
  function statusBadge(poap) {
    if (poap.hasClaimed) return 'CLAIMED';
    if (isOpen(poap)) return 'LIVE';
    return '';
  }

  /** @param {string} value */
  function initials(value) {
    return (value || 'POAP').slice(0, 2).toUpperCase();
  }

  /** @param {any[]} list */
  function buildGroups(list) {
    const groups = [];
    const byKey = {};
    for (const item of list) {
      const key = monthKey(item.eventStartAt);
      if (!byKey[key]) {
        byKey[key] = {
          key,
          label: monthLabel(item.eventStartAt),
          items: [],
        };
        groups.push(byKey[key]);
      }
      byKey[key].items.push(item);
    }
    return groups;
  }

  /** @param {string} slug */
  function openPoap(slug) {
    if (!slug) return;
    push(`/community/poaps/${slug}`);
  }

  let normalizedItems = $derived(items.map(normalizePoap).filter((item) => item.slug));
  let groups = $derived(buildGroups(normalizedItems));
</script>

<div class="poap-wall" class:compact={density === 'compact'}>
  {#each groups as group (group.key)}
    <section class="poap-month-section" aria-labelledby={`poap-month-${group.key}`}>
      <div class="poap-month-header">
        <h2 id={`poap-month-${group.key}`} class="poap-month-title">{group.label}</h2>
        <div class="poap-month-rule"></div>
      </div>

      <div class="poap-disc-grid">
        {#each group.items as poap (poap.key)}
          <button
            type="button"
            class="poap-disc-button"
            title={poap.title}
            aria-label={`Open ${poap.title}`}
            onclick={() => openPoap(poap.slug)}
          >
            <span class="poap-disc-frame" aria-hidden="true">
              <span class="poap-disc-core">
                {#if poap.artworkUrl}
                  <img src={poap.artworkUrl} alt="" class="poap-disc-art" loading="lazy" />
                {:else}
                  <span class="poap-disc-fallback">{initials(poap.title)}</span>
                {/if}
              </span>
              {#if showOpenBadge && statusBadge(poap)}
                <span class:claimed={poap.hasClaimed} class="poap-status-badge">{statusBadge(poap)}</span>
              {/if}
            </span>

            {#if showCaptions}
              <span class="poap-caption">
                <span class="poap-caption-title">{poap.title}</span>
                {#if showDetails}
                  <span class="poap-caption-meta">{metaLabel(poap)}</span>
                {/if}
              </span>
            {/if}
          </button>
        {/each}
      </div>
    </section>
  {/each}
</div>

<style>
  .poap-wall {
    --poap-size: 148px;
    --poap-tile: 166px;
    --poap-gap-x: 22px;
    --poap-gap-y: 28px;
  }

  .poap-wall.compact {
    --poap-size: 118px;
    --poap-tile: 138px;
    --poap-gap-x: 18px;
    --poap-gap-y: 24px;
  }

  .poap-month-section + .poap-month-section {
    margin-top: 34px;
  }

  .poap-month-header {
    align-items: center;
    display: flex;
    gap: 16px;
    margin-bottom: 16px;
    min-width: 0;
  }

  .poap-month-title {
    color: #d9c9ff;
    flex: 0 0 auto;
    font-family: var(--font-display, inherit);
    font-size: clamp(24px, 3vw, 34px);
    font-weight: 800;
    letter-spacing: 0;
    line-height: 1;
    margin: 0;
    text-shadow:
      1px 1px 0 #2f426a,
      2px 2px 0 rgba(127, 82, 225, 0.35),
      0 10px 22px rgba(127, 82, 225, 0.16);
    text-transform: uppercase;
    -webkit-text-stroke: 0.8px #51658d;
  }

  .poap-month-rule {
    background: linear-gradient(90deg, rgba(127, 82, 225, 0.26), rgba(25, 166, 99, 0.12), transparent);
    height: 1px;
    min-width: 24px;
    width: 100%;
  }

  .poap-disc-grid {
    align-items: start;
    display: grid;
    gap: var(--poap-gap-y) var(--poap-gap-x);
    grid-template-columns: repeat(auto-fill, minmax(var(--poap-tile), 1fr));
    justify-items: center;
  }

  .poap-disc-button {
    align-items: center;
    background: transparent;
    border: 0;
    border-radius: 18px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    min-height: var(--poap-size);
    padding: 0 4px 4px;
    text-align: center;
    width: var(--poap-tile);
  }

  .poap-disc-button:focus-visible {
    outline: 2px solid #7f52e1;
    outline-offset: 6px;
  }

  .poap-disc-frame {
    align-items: center;
    background:
      linear-gradient(#fff, #fff) padding-box,
      conic-gradient(from 135deg, rgba(127, 82, 225, 0.85), rgba(202, 190, 255, 0.42), rgba(25, 166, 99, 0.34), rgba(127, 82, 225, 0.85)) border-box;
    border: 1px solid transparent;
    border-radius: 999px;
    box-shadow:
      0 14px 30px rgba(38, 48, 75, 0.12),
      inset 0 0 0 1px rgba(127, 82, 225, 0.14);
    display: inline-flex;
    height: var(--poap-size);
    justify-content: center;
    padding: 7px;
    position: relative;
    transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
    width: var(--poap-size);
  }

  .poap-status-badge {
    background: #101010;
    border: 2px solid #fff;
    border-radius: 999px;
    bottom: 8px;
    box-shadow: 0 8px 18px rgba(16, 16, 16, 0.22);
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.4px;
    line-height: 1;
    padding: 5px 8px;
    position: absolute;
    right: 8px;
  }

  .poap-status-badge.claimed {
    background: #19a663;
    box-shadow: 0 8px 18px rgba(25, 166, 99, 0.24);
  }

  .poap-disc-core {
    background: #fff;
    border-radius: 999px;
    box-shadow: inset 0 0 0 2px #fff;
    display: block;
    height: 100%;
    overflow: hidden;
    width: 100%;
  }

  .poap-disc-art,
  .poap-disc-fallback {
    border-radius: inherit;
    display: block;
    height: 100%;
    width: 100%;
  }

  .poap-disc-art {
    background: #fff;
    object-fit: cover;
  }

  .poap-disc-fallback {
    align-items: center;
    background:
      radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.9), transparent 34%),
      linear-gradient(135deg, #7f52e1, #2f426a 58%, #19a663);
    color: #fff;
    display: flex;
    font-size: 20px;
    font-weight: 800;
    justify-content: center;
  }

  .poap-caption {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: 10px;
    max-width: 100%;
    min-width: 0;
  }

  .poap-caption-title {
    color: #101010;
    display: block;
    font-size: 13px;
    font-weight: 650;
    line-height: 17px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .poap-caption-meta {
    color: #66708a;
    display: block;
    font-size: 11px;
    line-height: 15px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .poap-disc-button:hover .poap-disc-frame {
    box-shadow:
      0 18px 36px rgba(80, 64, 150, 0.18),
      inset 0 0 0 1px rgba(127, 82, 225, 0.2);
    transform: translateY(-4px) scale(1.025);
  }

  .poap-disc-button:hover .poap-caption-title {
    color: #6b5bd6;
  }

  @media (max-width: 640px) {
    .poap-wall,
    .poap-wall.compact {
      --poap-size: 108px;
      --poap-tile: 124px;
      --poap-gap-x: 12px;
      --poap-gap-y: 20px;
    }

    .poap-month-header {
      gap: 12px;
      margin-bottom: 14px;
    }

    .poap-month-section + .poap-month-section {
      margin-top: 28px;
    }

    .poap-month-title {
      font-size: 24px;
    }

    .poap-disc-frame {
      padding: 6px;
    }
  }
</style>
