<script>
  import { push } from 'svelte-spa-router';
  import { onMount } from 'svelte';
  import { usersAPI } from '../lib/api';
  import Avatar from './Avatar.svelte';

  let query = $state('');
  let results = $state([]);
  let isOpen = $state(false);
  let isLoading = $state(false);
  let selectedIndex = $state(-1);
  let debounceTimeout = $state(null);
  let containerRef = $state(null);

  function handleInput(event) {
    query = event.target.value;
    selectedIndex = -1;

    if (debounceTimeout) {
      clearTimeout(debounceTimeout);
    }

    if (query.trim().length < 2) {
      results = [];
      isOpen = false;
      return;
    }

    debounceTimeout = setTimeout(async () => {
      await performSearch();
    }, 300);
  }

  async function performSearch() {
    if (query.trim().length < 2) return;

    isLoading = true;
    try {
      const response = await usersAPI.searchUsers(query.trim());
      results = response.data;
      isOpen = results.length > 0;
    } catch (error) {
      results = [];
      isOpen = false;
    } finally {
      isLoading = false;
    }
  }

  function handleResultClick(user) {
    navigateToUser(user);
  }

  function navigateToUser(user) {
    query = '';
    results = [];
    isOpen = false;
    push(`/participant/${user.address}`);
  }

  function handleKeydown(event) {
    if (!isOpen || results.length === 0) return;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        break;
      case 'Enter':
        event.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          navigateToUser(results[selectedIndex]);
        }
        break;
      case 'Escape':
        isOpen = false;
        selectedIndex = -1;
        break;
    }
  }

  function handleClickOutside(event) {
    if (containerRef && !containerRef.contains(event.target)) {
      isOpen = false;
      selectedIndex = -1;
    }
  }

  function handleFocus() {
    if (results.length > 0) {
      isOpen = true;
    }
  }

  function formatAddress(addr) {
    if (!addr) return '';
    return `${addr.substring(0, 6)}...${addr.substring(addr.length - 4)}`;
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    return () => {
      document.removeEventListener('click', handleClickOutside);
      if (debounceTimeout) {
        clearTimeout(debounceTimeout);
      }
    };
  });
</script>

<div class="search-container" bind:this={containerRef}>
  <div class="search-input-wrapper">
    <svg
      class="search-icon"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
    <input
      type="text"
      placeholder="Search participants..."
      value={query}
      oninput={handleInput}
      onkeydown={handleKeydown}
      onfocus={handleFocus}
      class="search-input"
    />
    {#if isLoading}
      <div class="loading-spinner"></div>
    {/if}
  </div>

  {#if isOpen && results.length > 0}
    <div class="search-dropdown">
      {#each results as user, index}
        <button
          class="search-result {index === selectedIndex ? 'selected' : ''}"
          onclick={() => handleResultClick(user)}
          onmouseenter={() => { selectedIndex = index; }}
        >
          <Avatar {user} size="sm" />
          <div class="result-info">
            <span class="result-name">{user.name || 'Anonymous'}</span>
            <span class="result-address">{formatAddress(user.address)}</span>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .search-container {
    position: relative;
    width: 280px;
  }

  .search-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 0.75rem;
    width: 1rem;
    height: 1rem;
    color: #9ca3af;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 0.75rem 0.5rem 2.25rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    font-size: 0.875rem;
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
  }

  .loading-spinner {
    position: absolute;
    right: 0.75rem;
    width: 1rem;
    height: 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 50%;
    border-top-color: #2563eb;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .search-dropdown {
    position: absolute;
    top: calc(100% + 0.5rem);
    left: 0;
    right: 0;
    z-index: 50;
    background-color: white;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    border: 1px solid #e5e7eb;
    max-height: 320px;
    overflow-y: auto;
  }

  .search-result {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    padding: 0.75rem;
    text-align: left;
    background: none;
    border: none;
    cursor: pointer;
    transition: background-color 0.15s;
  }

  .search-result:hover,
  .search-result.selected {
    background-color: #f3f4f6;
  }

  .search-result:first-child {
    border-radius: 0.5rem 0.5rem 0 0;
  }

  .search-result:last-child {
    border-radius: 0 0 0.5rem 0.5rem;
  }

  .result-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .result-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: #111827;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-address {
    font-size: 0.75rem;
    color: #6b7280;
    font-family: monospace;
  }
</style>
