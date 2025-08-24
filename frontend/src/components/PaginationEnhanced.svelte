<script>
  import { createEventDispatcher } from 'svelte';
  
  const { 
    currentPage = 1, 
    totalItems = 0, 
    itemsPerPage = 10,
    pageSizeOptions = [10, 25, 50, 100],
    showPageSize = true,
    className = ''
  } = $props();
  
  // Calculate total pages
  let totalPages = $derived(Math.ceil(totalItems / itemsPerPage));
  
  // Calculate which pages to show
  let pageNumbers = $derived((() => {
    const pages = [];
    const maxVisible = 5; // Maximum number of page buttons to show
    
    if (totalPages <= maxVisible) {
      // Show all pages if total is small
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Complex pagination logic for many pages
      if (currentPage <= 3) {
        // Near the beginning
        for (let i = 1; i <= 4; i++) {
          pages.push(i);
        }
        pages.push('...');
      } else if (currentPage >= totalPages - 2) {
        // Near the end
        pages.push('...');
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        // In the middle
        pages.push('...');
        for (let i = currentPage - 1; i <= currentPage + 1; i++) {
          pages.push(i);
        }
        pages.push('...');
      }
    }
    
    return pages;
  })());
  
  // Calculate range text
  let rangeStart = $derived(Math.min((currentPage - 1) * itemsPerPage + 1, totalItems));
  let rangeEnd = $derived(Math.min(currentPage * itemsPerPage, totalItems));
  
  // Create event dispatcher
  const dispatch = createEventDispatcher();
  
  function changePage(newPage) {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      dispatch('pageChange', newPage);
    }
  }
  
  function changePageSize(newSize) {
    dispatch('pageSizeChange', parseInt(newSize));
    // Reset to first page when changing page size
    if (currentPage !== 1) {
      dispatch('pageChange', 1);
    }
  }
  
  function handleKeyPress(event) {
    if (event.key === 'ArrowLeft' && currentPage > 1) {
      changePage(currentPage - 1);
    } else if (event.key === 'ArrowRight' && currentPage < totalPages) {
      changePage(currentPage + 1);
    }
  }
</script>

<svelte:window on:keydown={handleKeyPress} />

{#if totalItems > 0}
  <div class="bg-white px-4 sm:px-6 py-4 border border-gray-200 rounded-xl shadow-sm {className}">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <!-- Left side: Results info and page size selector -->
      <div class="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
        <div class="text-sm text-gray-600 font-medium">
          <span class="text-gray-900 font-semibold">{rangeStart}-{rangeEnd}</span>
          <span class="text-gray-500 mx-1">of</span>
          <span class="text-gray-900 font-semibold">{totalItems}</span>
          <span class="text-gray-500 ml-1">results</span>
        </div>
        
        {#if showPageSize && pageSizeOptions.length > 1}
          <div class="flex items-center gap-2">
            <label for="page-size" class="text-sm text-gray-600 font-medium">Show:</label>
            <select
              id="page-size"
              value={itemsPerPage}
              onchange={(e) => changePageSize(e.target.value)}
              class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 bg-white hover:border-gray-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-colors"
            >
              {#each pageSizeOptions as size}
                <option value={size}>{size}</option>
              {/each}
            </select>
          </div>
        {/if}
      </div>
      
      <!-- Right side: Pagination controls -->
      <nav class="flex items-center" aria-label="Pagination">
        <div class="isolate inline-flex rounded-lg shadow-sm">
          <!-- First page button -->
          <button
            onclick={() => changePage(1)}
            disabled={currentPage === 1}
            class="relative inline-flex items-center rounded-l-lg px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-colors"
            aria-label="First page"
            title="First page"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M15.79 14.77a.75.75 0 01-1.06.02l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 111.04 1.08L11.832 10l3.938 3.71a.75.75 0 01.02 1.06zm-6 0a.75.75 0 01-1.06.02l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 111.04 1.08L5.832 10l3.938 3.71a.75.75 0 01.02 1.06z" clip-rule="evenodd" />
            </svg>
          </button>
          
          <!-- Previous button -->
          <button
            onclick={() => changePage(currentPage - 1)}
            disabled={currentPage === 1}
            class="relative inline-flex items-center px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-colors"
            aria-label="Previous page"
            title="Previous page"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
            </svg>
          </button>
          
          <!-- Page numbers -->
          <div class="hidden sm:flex">
            {#each pageNumbers as page}
              {#if page === '...'}
                <span class="relative inline-flex items-center px-4 py-2 text-sm font-semibold text-gray-700 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">
                  ...
                </span>
              {:else}
                <button
                  onclick={() => changePage(page)}
                  class="relative inline-flex items-center px-4 py-2 text-sm font-semibold ring-1 ring-inset ring-gray-300 focus:z-20 focus:outline-offset-0 transition-all
                         {currentPage === page
                           ? 'z-10 bg-primary-600 text-white hover:bg-primary-700'
                           : 'text-gray-900 hover:bg-gray-50'}"
                  aria-label="Go to page {page}"
                  aria-current={currentPage === page ? 'page' : undefined}
                >
                  {page}
                </button>
              {/if}
            {/each}
          </div>
          
          <!-- Mobile: Current page indicator -->
          <span class="relative inline-flex sm:hidden items-center px-4 py-2 text-sm font-semibold text-gray-900 ring-1 ring-inset ring-gray-300 focus:outline-offset-0">
            Page {currentPage} / {totalPages}
          </span>
          
          <!-- Next button -->
          <button
            onclick={() => changePage(currentPage + 1)}
            disabled={currentPage === totalPages}
            class="relative inline-flex items-center px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-colors"
            aria-label="Next page"
            title="Next page"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
            </svg>
          </button>
          
          <!-- Last page button -->
          <button
            onclick={() => changePage(totalPages)}
            disabled={currentPage === totalPages}
            class="relative inline-flex items-center rounded-r-lg px-2 py-2 text-gray-400 ring-1 ring-inset ring-gray-300 hover:bg-gray-50 focus:z-20 focus:outline-offset-0 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent transition-colors"
            aria-label="Last page"
            title="Last page"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4.21 5.23a.75.75 0 00.02 1.06L8.168 10l-3.938 3.71a.75.75 0 101.04 1.08l4.5-4.25a.75.75 0 000-1.08l-4.5-4.25a.75.75 0 00-1.06.02zm6 0a.75.75 0 00.02 1.06L14.168 10l-3.938 3.71a.75.75 0 101.04 1.08l4.5-4.25a.75.75 0 000-1.08l-4.5-4.25a.75.75 0 00-1.06.02z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </nav>
    </div>
  </div>
{/if}

<style>
  /* Smooth transitions */
  button {
    transition: all 0.15s ease;
  }
  
  /* Focus styles */
  button:focus-visible {
    outline: 2px solid transparent;
    outline-offset: 2px;
    box-shadow: 0 0 0 2px white, 0 0 0 4px rgb(99, 102, 241);
  }
  
  select:focus-visible {
    outline: 2px solid transparent;
    outline-offset: 2px;
  }
  
  /* Remove transform effects - keeping styles clean */
</style>