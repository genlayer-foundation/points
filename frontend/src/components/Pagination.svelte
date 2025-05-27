<script>
  import { createEventDispatcher } from 'svelte';
  
  const { page = 1, limit = 10, totalCount = 0 } = $props();
  
  // Calculate total pages
  let totalPages = $derived(Math.ceil(totalCount / limit));
  
  // Create an event dispatcher to notify parent components of page changes
  const dispatch = createEventDispatcher();
  
  function changePage(newPage) {
    dispatch('pageChange', newPage);
  }
</script>

{#if totalPages > 1}
  <div class="bg-white px-4 py-3 border-t border-gray-200">
    <div class="flex justify-between items-center">
      <div class="text-sm text-gray-500">
        Showing {Math.min((page - 1) * limit + 1, totalCount)} - {Math.min(page * limit, totalCount)} of {totalCount} items
      </div>
      <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
        <button
          class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          disabled={page === 1}
          onclick={(e) => {
            e.preventDefault();
            changePage(page - 1);
          }}
        >
          <span class="sr-only">Previous</span>
          <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
        
        {#each Array(Math.min(5, totalPages)) as _, i}
          {@const pageNum = i + 1}
          <button
            class={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${page === pageNum ? 'z-10 bg-primary-50 border-primary-500 text-primary-600' : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'}`}
            onclick={(e) => {
              e.preventDefault();
              changePage(pageNum);
            }}
          >
            {pageNum}
          </button>
        {/each}
        
        {#if totalPages > 5}
          <span class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">
            ...
          </span>
          <button
            class={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${page === totalPages ? 'z-10 bg-primary-50 border-primary-500 text-primary-600' : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'}`}
            onclick={(e) => {
              e.preventDefault();
              changePage(totalPages);
            }}
          >
            {totalPages}
          </button>
        {/if}
        
        <button
          class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
          disabled={page === totalPages}
          onclick={(e) => {
            e.preventDefault();
            changePage(page + 1);
          }}
        >
          <span class="sr-only">Next</span>
          <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </nav>
    </div>
  </div>
{/if}