<script>
  import { onMount } from 'svelte';

  let {
    value = $bindable(''),
    contributionTypes = [],
    stewardsList = [],
    placeholder = 'type:blog-post assigned:me exclude:medium.com...',
    onSearch = () => {}
  } = $props();

  let inputRef = $state(null);
  let containerRef = $state(null);
  let showAutocomplete = $state(false);
  let showHelp = $state(false);
  let suggestions = $state([]);
  let selectedIndex = $state(-1);
  let debounceTimeout = null;

  const TAGS = [
    { name: 'type', description: 'Filter by contribution type', values: () => contributionTypes.map(t => t.name.toLowerCase().replace(/\s+/g, '-')) },
    { name: 'from', description: 'Search by user name/email/address', values: () => [] },
    { name: 'assigned', description: 'Filter by assignment', values: () => ['me', 'unassigned', ...stewardsList.map(s => s.name || s.address?.slice(0, 10))] },
    { name: 'exclude', description: 'Exclude submissions containing text', values: () => ['medium.com'] },
    { name: 'include', description: 'Only show submissions containing text', values: () => [] },
    { name: 'has', description: 'Filter by presence', values: () => ['url', 'evidence', 'proposal'] },
    { name: 'no', description: 'Filter by absence', values: () => ['url', 'evidence', 'proposal'] },
    { name: 'min-contributions', description: 'Min accepted contributions', values: () => ['1', '2', '3', '4', '5'] },
    { name: 'sort', description: 'Sort order', values: () => ['created', '-created', 'date', '-date'] }
  ];

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

    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      onSearch(value);
    }, 500);
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

    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      onSearch(value);
    }, 500);
  }

  function handleKeydown(event) {
    if (!showAutocomplete || suggestions.length === 0) {
      if (event.key === 'Enter') {
        event.preventDefault();
        onSearch(value);
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

  function handleFocus() {
    updateSuggestions();
    showAutocomplete = true;
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
      if (debounceTimeout) clearTimeout(debounceTimeout);
    };
  });
</script>

<div class="search-container" bind:this={containerRef}>
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

  {#if showHelp}
    <div class="help-tooltip">
      <div class="help-header">Search Syntax</div>
      <div class="help-content">
        <div class="help-section">
          <div class="help-row"><code>type:blog-post</code><span>Filter by contribution type</span></div>
          <div class="help-row"><code>from:username</code><span>Search by user name/email/address</span></div>
          <div class="help-row"><code>assigned:me</code><span>Filter by assignment (me, unassigned, name)</span></div>
          <div class="help-row"><code>exclude:medium.com</code><span>Exclude submissions containing text</span></div>
          <div class="help-row"><code>include:genlayer</code><span>Only show submissions containing text</span></div>
          <div class="help-row"><code>has:url</code><span>Only submissions with URLs</span></div>
          <div class="help-row"><code>has:proposal</code><span>Only submissions with a proposal</span></div>
          <div class="help-row"><code>no:url</code><span>Only submissions without URLs</span></div>
          <div class="help-row"><code>min-contributions:3</code><span>Users with N+ accepted contributions</span></div>
          <div class="help-row"><code>sort:-created</code><span>Sort order (created, -created, date, -date)</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Negation</div>
          <div class="help-row"><code>-type:blog-post</code><span>Exclude contribution type</span></div>
        </div>
        <div class="help-section">
          <div class="help-subtitle">Examples</div>
          <div class="help-example">assigned:me exclude:medium.com has:url</div>
          <div class="help-example">from:alice -type:referral min-contributions:2</div>
        </div>
        <div class="help-note">All terms must use tags. Unrecognized text is ignored.</div>
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
