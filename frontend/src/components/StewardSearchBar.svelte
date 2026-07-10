<script>
  import { onMount } from 'svelte';

  let {
    value = $bindable(''),
    variant = 'submissions', // 'submissions' | 'xp'
    contributionTypes = [],
    stewardsList = [],
    templates = [],
    missions = [],
    placeholder = 'Search URL or text, or type sort:-reviewed...',
    onSearch = () => {}
  } = $props();

  let inputRef = $state(null);
  let containerRef = $state(null);
  let showAutocomplete = $state(false);
  let showHelp = $state(false);
  let suggestions = $state([]);
  let selectedIndex = $state(-1);
  let lastSearchedValue = $state('');

  const stewardSearchValues = () => stewardsList
    .map(s => {
      const identifier = s.name || s.address?.slice(0, 10);
      return identifier?.toLowerCase().replace(/\s+/g, '-');
    })
    .filter(Boolean);

  const XP_TAGS = [
    { name: 'type', description: 'Filter by community contribution type', values: () => contributionTypes.map(t => t.slug || t.name.toLowerCase().replace(/\s+/g, '-')) },
    { name: 'from', description: 'Search by name, wallet, or Discord username', values: () => [] },
    { name: 'include', description: 'Only show contributions containing text', values: () => [] },
    { name: 'exclude', description: 'Exclude contributions containing text', values: () => [] },
    { name: 'sort', description: 'Sort order', values: () => ['created', '-created', 'date', '-date', 'points', '-points', 'distributed', '-distributed'] }
  ];

  const SUBMISSION_TAGS = [
    {
      name: 'status',
      description: 'Filter by review status',
      values: () => ['pending', 'accepted', 'rejected', 'canceled', 'more_info_needed']
    },
    { name: 'type', description: 'Filter by contribution type', values: () => contributionTypes.map(t => t.name.toLowerCase().replace(/\s+/g, '-')) },
    { name: 'category', description: 'Filter by category', values: () => [...new Set(contributionTypes.map(t => t.category).filter(Boolean))] },
    { name: 'from', description: 'Search by user name or address', values: () => [] },
    { name: 'assigned', description: 'Filter by assignment', values: () => ['me', 'unassigned', ...stewardSearchValues()] },
    { name: 'reviewed', description: 'Filter by steward who reviewed', values: () => ['me', ...stewardSearchValues()] },
    { name: 'proposed-by', description: 'Filter by proposal creator', values: () => ['ai', 'me', 'none', ...stewardSearchValues()] },
    { name: 'exclude', description: 'Exclude submissions containing text', values: () => ['medium.com'] },
    { name: 'include', description: 'Only show submissions containing text', values: () => [] },
    { name: 'has', description: 'Filter by presence', values: () => ['url', 'evidence', 'proposal', 'appeal'] },
    { name: 'no', description: 'Filter by absence', values: () => ['url', 'evidence', 'proposal', 'appeal'] },
    { name: 'is', description: 'Filter by internal flag', values: () => ['interesting', 'appealed', 'ai-reviewed'] },
    { name: 'not', description: 'Exclude by internal flag', values: () => ['interesting', 'appealed', 'ai-reviewed'] },
    { name: 'proposal', description: 'Filter by proposed action', values: () => ['accept', 'reject', 'more-info'] },
    { name: 'proposal-status', description: 'Filter by proposal review status', values: () => ['pending', 'questioned'] },
    { name: 'confidence', description: 'Filter by proposal confidence', values: () => ['high', 'medium', 'low'] },
    { name: 'template', description: 'Filter by review template', values: () => templates.map(t => t.label.toLowerCase().replace(/\s+/g, '-')) },
    { name: 'mission', description: 'Filter by mission', values: () => ['none', ...missions.map(m => m.name.toLowerCase().replace(/\s+/g, '-'))] },
    { name: 'min-contributions', description: 'Min accepted contributions', values: () => ['1', '2', '3', '4', '5'] },
    { name: 'sort', description: 'Sort order', values: () => ['created', '-created', 'date', '-date', 'reviewed', '-reviewed', 'points', '-points'] }
  ];

  const TAGS = variant === 'xp' ? XP_TAGS : SUBMISSION_TAGS;

  function getCurrentWord() {
    if (!inputRef) return { word: '', start: 0, end: 0 };

    const cursorPos = inputRef.selectionStart;
    const text = value;

    let start = cursorPos;
    let end = cursorPos;

    while (start > 0 && text[start - 1] !== ' ') start--;
    while (end < text.length && text[end] !== ' ') end++;

    return { word: text.slice(start, end), start, end };
  }

  function updateSuggestions() {
    const { word } = getCurrentWord();

    if (!word) {
      suggestions = TAGS.map(t => `${t.name}:`);
      return;
    }

    const colonIndex = word.indexOf(':');

    if (colonIndex === -1) {
      // Suggesting tag names
      const prefix = word.replace(/^-/, '').toLowerCase();
      suggestions = TAGS
        .filter(t => t.name.startsWith(prefix))
        .map(t => word.startsWith('-') ? `-${t.name}:` : `${t.name}:`);
    } else {
      // Suggesting tag values
      const tagName = word.slice(0, colonIndex).replace(/^-/, '').toLowerCase();
      const valuePrefix = word.slice(colonIndex + 1).toLowerCase();
      const tag = TAGS.find(t => t.name === tagName);

      if (tag) {
        const values = tag.values();
        suggestions = values
          .filter(v => v.toLowerCase().startsWith(valuePrefix))
          .map(v => `${word.slice(0, colonIndex + 1)}${v}`);
      } else {
        suggestions = [];
      }
    }

    selectedIndex = suggestions.length > 0 ? 0 : -1;
  }

  function handleInput(event) {
    value = event.target.value;
    showAutocomplete = true;
    updateSuggestions();
  }

  function selectSuggestion(suggestion) {
    const { start, end } = getCurrentWord();
    const before = value.slice(0, start);
    const after = value.slice(end);

    // Don't add space if suggestion ends with ':' (user needs to type value)
    const needsSpace = !suggestion.endsWith(':');
    const spacer = needsSpace ? ' ' : '';
    value = before + suggestion + (after.startsWith(' ') || !needsSpace ? after.trimStart() : spacer + after.trimStart());
    showAutocomplete = false;

    // Focus input and move cursor
    if (inputRef) {
      inputRef.focus();
      const newPos = before.length + suggestion.length + (needsSpace ? 1 : 0);
      setTimeout(() => inputRef.setSelectionRange(newPos, newPos), 0);
    }
  }

  function handleKeydown(event) {
    if (!showAutocomplete || suggestions.length === 0) {
      if (event.key === 'Enter') {
        event.preventDefault();
        submitSearch();
      }
      return;
    }

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, suggestions.length - 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, 0);
        break;
      case 'Tab':
      case 'Enter':
        event.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          selectSuggestion(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        showAutocomplete = false;
        selectedIndex = -1;
        break;
    }
  }

  function submitSearch() {
    if (value !== lastSearchedValue) {
      lastSearchedValue = value;
      onSearch(value);
    }
  }

  function handleFocus() {
    updateSuggestions();
    showAutocomplete = true;
  }

  function handleBlur() {
    // Small delay so clicking a suggestion doesn't trigger search before the click registers
    setTimeout(() => {
      submitSearch();
    }, 200);
  }

  function handleClickOutside(event) {
    if (containerRef && !containerRef.contains(event.target)) {
      showAutocomplete = false;
      showHelp = false;
    }
  }

  function toggleHelp() {
    showHelp = !showHelp;
    showAutocomplete = false;
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
    };
  });
</script>

<div class="search-container {variant}" bind:this={containerRef}>
  <div class="search-input-wrapper">
    <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
    <input
      type="text"
      bind:this={inputRef}
      value={value}
      oninput={handleInput}
      onkeydown={handleKeydown}
      onfocus={handleFocus}
      onblur={handleBlur}
      {placeholder}
      class="search-input"
    />
    <button type="button" class="help-button" onclick={toggleHelp} title="Search syntax help">
      ?
    </button>
  </div>

  {#if showAutocomplete && suggestions.length > 0}
    <div class="autocomplete-dropdown">
      {#each suggestions as suggestion, index}
        <button
          type="button"
          class="suggestion {index === selectedIndex ? 'selected' : ''}"
          onclick={() => selectSuggestion(suggestion)}
          onmouseenter={() => { selectedIndex = index; }}
        >
          {suggestion}
        </button>
      {/each}
    </div>
  {/if}

  {#if showHelp && variant === 'xp'}
    <div class="help-tooltip">
      <div class="help-header">XP Search</div>
      <div class="help-content">
        <div class="help-section">
          <div class="help-row"><code>type:ama</code><span>Community contribution type</span></div>
          <div class="help-row"><code>from:alice</code><span>Name, email, wallet, or Discord username</span></div>
          <div class="help-row"><code>include:genlayer</code><span>Title, notes, type, or evidence contains text</span></div>
          <div class="help-row"><code>exclude:duplicate</code><span>Hide matching title, notes, type, or evidence</span></div>
          <div class="help-row"><code>sort:-points</code><span>created, date, points, distributed, or their negative form</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Examples</div>
          <div class="help-example">from:alice include:thread sort:-date</div>
          <div class="help-example">type:community-call sort:-points</div>
          <div class="help-example">include:thread exclude:duplicate</div>
        </div>
        <div class="help-note">Untagged text searches contributor, Discord, title, notes, type, and evidence.</div>
      </div>
    </div>
  {:else if showHelp}
    <div class="help-tooltip">
      <div class="help-header">Submission Search</div>
      <div class="help-content">
        <div class="help-section">
          <div class="help-subtitle">Common</div>
          <div class="help-row"><code>https://x.com/...</code><span>Search submitter, title, notes, and evidence</span></div>
          <div class="help-row"><code>include:genlayer</code><span>Require matching title, notes, or evidence</span></div>
          <div class="help-row"><code>exclude:medium.com</code><span>Hide matching title, notes, or evidence</span></div>
          <div class="help-row"><code>type:blog-post</code><span>Contribution type</span></div>
          <div class="help-row"><code>category:builder</code><span>Category slug</span></div>
          <div class="help-row"><code>from:alice</code><span>Submitter name or address</span></div>
          <div class="help-row"><code>assigned:me</code><span>Assigned steward (me, unassigned, name)</span></div>
          <div class="help-row"><code>assigned:pavel-kolosov</code><span>Names can use spaces or hyphens</span></div>
          <div class="help-row"><code>reviewed:me</code><span>Steward who took the final review action</span></div>
          <div class="help-row"><code>mission:name</code><span>Mission name, ID, or none</span></div>
          <div class="help-row"><code>has:url</code><span>Only submissions with URL evidence</span></div>
          <div class="help-row"><code>no:url</code><span>Only submissions without URL evidence</span></div>
          <div class="help-row"><code>is:interesting</code><span>Flagged as interesting</span></div>
          <div class="help-row"><code>is:ai-reviewed</code><span>Has an AI review analysis</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Status and Sorting</div>
          <div class="help-row"><code>Status dropdown</code><span>Primary control for Pending, Accepted, Rejected, Canceled</span></div>
          <div class="help-row"><code>status:accepted</code><span>Typed status filter for combined queries</span></div>
          <div class="help-row"><code>sort:-reviewed</code><span>Latest reviewed or accepted first</span></div>
          <div class="help-row"><code>sort:-points</code><span>Highest accepted points first</span></div>
          <div class="help-row"><code>sort:-created</code><span>Newest submission first</span></div>
          <div class="help-row"><code>sort:-date</code><span>Newest submitted contribution date first</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Advanced</div>
          <div class="help-row"><code>has:proposal</code><span>Only submissions with an active proposal</span></div>
          <div class="help-row"><code>proposed-by:ai</code><span>Only active proposals from the AI reviewer</span></div>
          <div class="help-row"><code>proposal:reject</code><span>Proposed action (accept, reject, more-info)</span></div>
          <div class="help-row"><code>proposal-status:questioned</code><span>Proposals returned to reviewers for revision</span></div>
          <div class="help-row"><code>confidence:high</code><span>Proposal confidence</span></div>
          <div class="help-row"><code>template:spam</code><span>Proposal template</span></div>
          <div class="help-row"><code>has:appeal</code><span>Appealed by submitter</span></div>
          <div class="help-row"><code>min-contributions:3</code><span>Submitters with N+ accepted submissions</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Negation</div>
          <div class="help-row"><code>-type:blog-post</code><span>Exclude contribution type</span></div>
          <div class="help-row"><code>-assigned:unassigned,Joaquin</code><span>Exclude multiple assignments</span></div>
          <div class="help-row"><code>-assigned:unassigned -assigned:Joaquin</code><span>Repeated exclusions also work</span></div>
          <div class="help-row"><code>-proposed-by:ai</code><span>Exclude active AI proposals</span></div>
          <div class="help-row"><code>-mission:name</code><span>Exclude a mission while keeping other matches</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Examples</div>
          <div class="help-example">assigned:me exclude:medium.com has:url</div>
          <div class="help-example">status:accepted sort:-points</div>
          <div class="help-example">status:accepted reviewed:alice sort:-reviewed</div>
          <div class="help-example">assigned:Pavel Kolosov has:proposal</div>
          <div class="help-example">-assigned:unassigned,Joaquin has:url</div>
          <div class="help-example">https://x.com/user/status/123</div>
          <div class="help-example">type:bug-report -mission:wallet-login is:ai-reviewed</div>
        </div>
        <div class="help-note">Untagged text and URLs search submitter, title, notes, and evidence. Use quotes for values with spaces.</div>
      </div>
    </div>
  {/if}
</div>

<style>
  .search-container {
    position: relative;
    flex: 1;
  }

  .search-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 0.75rem;
    width: 1.25rem;
    height: 1.25rem;
    color: #9ca3af;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 0.625rem 2.5rem 0.625rem 2.5rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background-color: #f9fafb;
    transition: all 0.2s;
  }

  .search-input:focus {
    outline: none;
    border-color: #2563eb;
    background-color: white;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  }

  .search-container.xp .search-input:focus {
    border-color: #19a663;
    box-shadow: 0 0 0 3px rgba(25, 166, 99, 0.12);
  }

  .search-input::placeholder {
    color: #9ca3af;
    font-family: inherit;
  }

  .help-button {
    position: absolute;
    right: 0.5rem;
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 50%;
    border: 1px solid #d1d5db;
    background: white;
    color: #6b7280;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .help-button:hover {
    background: #f3f4f6;
    color: #374151;
  }

  .autocomplete-dropdown {
    position: absolute;
    top: calc(100% + 0.25rem);
    left: 0;
    right: 0;
    z-index: 50;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    max-height: 240px;
    overflow-y: auto;
  }

  .suggestion {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    text-align: left;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.875rem;
    color: #374151;
    background: none;
    border: none;
    cursor: pointer;
  }

  .suggestion:hover,
  .suggestion.selected {
    background: #f3f4f6;
  }

  .help-tooltip {
    position: absolute;
    top: calc(100% + 0.25rem);
    left: 0;
    right: 0;
    z-index: 50;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    padding: 1rem;
    max-height: 400px;
    overflow-y: auto;
  }

  .help-header {
    font-weight: 600;
    font-size: 0.875rem;
    color: #111827;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .help-content {
    font-size: 0.8125rem;
  }

  .help-section {
    margin-bottom: 0.75rem;
  }

  .help-subtitle {
    font-weight: 500;
    color: #374151;
    margin-bottom: 0.25rem;
  }

  .help-row {
    display: flex;
    gap: 0.75rem;
    padding: 0.25rem 0;
  }

  .help-row code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    background: #f3f4f6;
    padding: 0.125rem 0.375rem;
    border-radius: 0.25rem;
    color: #1f2937;
    white-space: nowrap;
    min-width: 140px;
  }

  .help-row span {
    color: #6b7280;
  }

  .help-example {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.75rem;
    background: #f9fafb;
    padding: 0.375rem 0.5rem;
    border-radius: 0.25rem;
    margin-top: 0.25rem;
    color: #4b5563;
  }

  .help-note {
    margin-top: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px solid #e5e7eb;
    font-size: 0.75rem;
    color: #9ca3af;
    font-style: italic;
  }
</style>
