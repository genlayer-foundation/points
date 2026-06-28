<script>
  let { activity = [], activityWindow = null, loading = false } = $props();

  const MS_PER_DAY = 24 * 60 * 60 * 1000;
  const MONTH_FORMAT = new Intl.DateTimeFormat(undefined, { month: 'short' });
  const DATE_FORMAT = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' });

  function parseDay(value) {
    const [year, month, day] = String(value || '').split('-').map(Number);
    if (!year || !month || !day) return null;
    return new Date(Date.UTC(year, month - 1, day));
  }

  function addDays(date, days) {
    return new Date(date.getTime() + days * MS_PER_DAY);
  }

  function startOfWeek(date) {
    return addDays(date, -date.getUTCDay());
  }

  function endOfWeek(date) {
    return addDays(date, 6 - date.getUTCDay());
  }

  function dayKey(date) {
    return date.toISOString().slice(0, 10);
  }

  function formatNumber(value) {
    const n = Number(value || 0);
    return n.toLocaleString();
  }

  function plural(value, word) {
    return `${formatNumber(value)} ${word}${Number(value) === 1 ? '' : 's'}`;
  }

  function buildHeatmap(rows, window) {
    const entries = rows
      .map((row) => ({ row, date: parseDay(row?.date) }))
      .filter((entry) => entry.date)
      .sort((a, b) => a.date - b.date);

    if (!entries.length) {
      return { weeks: [], monthLabels: [], max: 0 };
    }

    // Prefer the backend's declared window so the grid bounds follow the
    // six-month contract even if leading/trailing zero days are ever omitted.
    const first = parseDay(window?.start) || entries[0].date;
    const last = parseDay(window?.end) || entries[entries.length - 1].date;
    const rangeLabel = `${DATE_FORMAT.format(first)} - ${DATE_FORMAT.format(last)}`;
    const start = startOfWeek(first);
    const end = endOfWeek(last);
    const byDate = new Map(entries.map((entry) => [dayKey(entry.date), entry.row]));
    const max = Math.max(...entries.map((entry) => Number(entry.row?.decisions_made || 0)), 0);
    const todayKey = dayKey(new Date());
    const weeks = [];

    for (let cursor = new Date(start); cursor <= end; cursor = addDays(cursor, 7)) {
      const days = [];
      for (let offset = 0; offset < 7; offset += 1) {
        const date = addDays(cursor, offset);
        const key = dayKey(date);
        const row = byDate.get(key);
        const decisions = Number(row?.decisions_made || 0);
        const transactions = Number(row?.chain_transactions || 0);
        const ratio = max > 0 ? decisions / max : 0;
        const level = decisions <= 0 ? 0 : Math.max(1, Math.min(4, Math.ceil(ratio * 4)));
        const label = DATE_FORMAT.format(date);
        const isPastOrToday = key <= todayKey;

        days.push({
          key,
          label,
          decisions,
          transactions,
          level,
          inRange: date >= first && date <= last && isPastOrToday,
          title: `${label}: ${plural(decisions, 'decision')}, ${plural(transactions, 'transaction')}`,
        });
      }
      weeks.push({ key: dayKey(cursor), days });
    }

    let lastMonth = '';
    const monthLabels = weeks.map((week, index) => {
      const monthStartDay = week.days.find((day) => {
        const date = parseDay(day.key);
        return day.inRange && date && date.getUTCDate() === 1;
      });
      const labelDay = index === 0 ? week.days.find((day) => day.inRange) : monthStartDay;
      if (!labelDay) return '';
      const date = parseDay(labelDay.key);
      if (!date) return '';
      const month = MONTH_FORMAT.format(date);
      if (month === lastMonth) return '';
      lastMonth = month;
      if (index === 0 || date.getUTCDate() === 1) return month;
      return '';
    });

    return { weeks, monthLabels, max, rangeLabel };
  }

  const heatmap = $derived(buildHeatmap(activity, activityWindow));
</script>

<div class="activity-wrap">
  {#if loading}
    <div class="activity-skeleton" aria-hidden="true"></div>
  {:else if !heatmap.weeks.length}
    <div class="activity-empty">Daily network activity will appear here shortly.</div>
  {:else}
    <div class="activity-scroll" aria-label="Daily network activity heatmap">
      <div class="activity-content">
        <div class="activity-range">{heatmap.rangeLabel}</div>

        <div class="month-row" style={`--week-count: ${heatmap.weeks.length}`}>
          <span aria-hidden="true"></span>
          {#each heatmap.monthLabels as month, index (`month-${index}`)}
            <span>{month}</span>
          {/each}
        </div>

        <div class="heatmap-row">
          <div class="weekday-labels" aria-hidden="true">
            <span></span>
            <span>Mon</span>
            <span></span>
            <span>Wed</span>
            <span></span>
            <span>Fri</span>
            <span></span>
          </div>

          <div class="week-grid" style={`--week-count: ${heatmap.weeks.length}`}>
            {#each heatmap.weeks as week}
              <div class="week-column">
                {#each week.days as day}
                  {#if day.inRange}
                    <button
                      class="activity-cell"
                      class:has-activity={day.decisions > 0 || day.transactions > 0}
                      data-level={day.level}
                      type="button"
                      title={day.title}
                      aria-label={day.title}
                    >
                      <span class="activity-tooltip" role="tooltip">
                        <strong>{day.label}</strong>
                        <span>{plural(day.decisions, 'decision')}</span>
                        <span>{plural(day.transactions, 'transaction')}</span>
                      </span>
                    </button>
                  {:else}
                    <span class="activity-cell empty" aria-hidden="true"></span>
                  {/if}
                {/each}
              </div>
            {/each}
          </div>
        </div>

        <div class="legend" aria-hidden="true">
          <span>Less</span>
          <span class="legend-cell" data-level="0"></span>
          <span class="legend-cell" data-level="1"></span>
          <span class="legend-cell" data-level="2"></span>
          <span class="legend-cell" data-level="3"></span>
          <span class="legend-cell" data-level="4"></span>
          <span>More</span>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .activity-wrap {
    background: linear-gradient(180deg, rgba(48, 73, 255, 0.035), rgba(255, 255, 255, 0) 34%);
    border-radius: 8px;
    display: flex;
    min-height: 320px;
    position: relative;
    width: 100%;
    z-index: 2;
  }

  .activity-scroll {
    --cell-gap: 4px;
    --cell-size: clamp(16px, 1.35vw, 20px);
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 320px;
    overflow-x: auto;
    padding: 22px 2px 12px;
  }

  .activity-content {
    display: flex;
    flex: 1;
    flex-direction: column;
    margin-inline: auto;
    min-width: max-content;
    width: max-content;
  }

  .activity-range {
    color: #7d8491;
    font-size: 14px;
    font-weight: 700;
    line-height: 20px;
    margin-bottom: 20px;
    padding-left: 0;
    white-space: nowrap;
  }

  .month-row {
    color: #6b7280;
    display: grid;
    font-size: 14px;
    gap: var(--cell-gap);
    grid-template-columns: 40px repeat(var(--week-count), var(--cell-size));
    line-height: 20px;
    min-width: max-content;
  }

  .heatmap-row {
    display: flex;
    gap: 12px;
    min-width: max-content;
  }

  .weekday-labels,
  .week-column {
    display: grid;
    gap: var(--cell-gap);
    grid-template-rows: repeat(7, var(--cell-size));
  }

  .weekday-labels {
    color: #6b7280;
    flex: 0 0 28px;
    font-size: 13px;
    line-height: var(--cell-size);
    text-align: right;
  }

  .week-grid {
    display: grid;
    gap: var(--cell-gap);
    grid-template-columns: repeat(var(--week-count), var(--cell-size));
  }

  .activity-cell {
    appearance: none;
    background: #eef1ff;
    border: 0;
    border-radius: 4px;
    box-shadow: inset 0 0 0 1px rgba(48, 73, 255, 0.05);
    display: block;
    height: var(--cell-size);
    padding: 0;
    position: relative;
    width: var(--cell-size);
  }

  .activity-cell.empty {
    background: transparent;
  }

  .activity-cell[data-level='1'],
  .legend-cell[data-level='1'] {
    background: #dbe1ff;
  }

  .activity-cell[data-level='2'],
  .legend-cell[data-level='2'] {
    background: #aeb8ff;
  }

  .activity-cell[data-level='3'],
  .legend-cell[data-level='3'] {
    background: #6f80ff;
  }

  .activity-cell[data-level='4'],
  .legend-cell[data-level='4'] {
    background: #3049ff;
  }

  .activity-cell.has-activity {
    cursor: default;
  }

  .activity-cell:focus-visible {
    outline: 2px solid rgba(48, 73, 255, 0.62);
    outline-offset: 2px;
    z-index: 3;
  }

  .activity-cell:hover .activity-tooltip,
  .activity-cell:focus-visible .activity-tooltip {
    opacity: 1;
    transform: translate(-50%, 8px);
    visibility: visible;
  }

  .activity-tooltip {
    background: #101010;
    border-radius: 8px;
    box-shadow: 0 12px 30px rgba(16, 16, 16, 0.22);
    color: #e7e9ee;
    display: flex;
    flex-direction: column;
    font-size: 12px;
    gap: 3px;
    left: 50%;
    line-height: 16px;
    min-width: 164px;
    opacity: 0;
    padding: 10px 12px;
    pointer-events: none;
    position: absolute;
    text-align: left;
    top: 100%;
    transform: translate(-50%, 2px);
    transition: opacity 140ms ease, transform 140ms ease, visibility 140ms ease;
    visibility: hidden;
    z-index: 10;
  }

  .activity-tooltip::after {
    border-bottom: 6px solid #101010;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    content: '';
    left: 50%;
    position: absolute;
    top: -6px;
    transform: translateX(-50%);
  }

  .week-column:nth-child(-n + 5) .activity-tooltip {
    left: 0;
    right: auto;
    transform: translate(0, 2px);
  }

  .week-column:nth-child(-n + 5) .activity-cell:hover .activity-tooltip,
  .week-column:nth-child(-n + 5) .activity-cell:focus-visible .activity-tooltip {
    transform: translate(0, 8px);
  }

  .week-column:nth-child(-n + 5) .activity-tooltip::after {
    left: 10px;
    transform: none;
  }

  .week-column:nth-last-child(-n + 5) .activity-tooltip {
    left: auto;
    right: 0;
    transform: translate(0, 2px);
  }

  .week-column:nth-last-child(-n + 5) .activity-cell:hover .activity-tooltip,
  .week-column:nth-last-child(-n + 5) .activity-cell:focus-visible .activity-tooltip {
    transform: translate(0, 8px);
  }

  .week-column:nth-last-child(-n + 5) .activity-tooltip::after {
    left: auto;
    right: 10px;
    transform: none;
  }

  .activity-tooltip strong {
    color: #fff;
    font-size: 13px;
    font-weight: 600;
  }

  .legend {
    align-items: center;
    color: #6b7280;
    display: flex;
    font-size: 12px;
    gap: 6px;
    justify-content: flex-end;
    margin-top: auto;
    min-width: max-content;
    padding-right: 2px;
  }

  .legend-cell {
    background: #eef1ff;
    border-radius: 4px;
    height: var(--cell-size);
    width: var(--cell-size);
  }

  .activity-skeleton {
    animation: heatmap-shimmer 1.4s ease-in-out infinite;
    background: linear-gradient(90deg, #f2f3f5, #fbfbfc, #f2f3f5);
    background-size: 200% 100%;
    border-radius: 8px;
    height: 320px;
    width: 100%;
  }

  .activity-empty {
    align-items: center;
    color: #9aa1ad;
    display: flex;
    font-size: 13px;
    height: 320px;
    justify-content: center;
    text-align: center;
  }

  @keyframes heatmap-shimmer {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .activity-skeleton,
    .activity-tooltip {
      animation: none;
      transition: none;
    }
  }

  @media (max-width: 620px) {
    .activity-wrap,
    .activity-scroll,
    .activity-skeleton,
    .activity-empty {
      min-height: 280px;
    }
  }
</style>
