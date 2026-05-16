<script>
  import { onError } from 'svelte';

  let error = $state(null);
  let errorInfo = $state('');

  export function resetError() {
    error = null;
    errorInfo = '';
  }

  onError((event) => {
    error = event.error;
    errorInfo = event.message || 'An unexpected error occurred';
    console.error('Error caught by boundary:', event.error);
  });
</script>

{#if error}
  <div class="error-boundary flex items-center justify-center min-h-screen bg-gray-50">
    <div class="error-container bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
      <div class="error-icon mb-4">
        <svg class="w-16 h-16 text-red-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      
      <h2 class="text-2xl font-bold text-gray-900 text-center mb-2">Oops! Something went wrong</h2>
      
      <p class="text-gray-600 text-center mb-4">
        We encountered an unexpected error. Please try refreshing the page or go back and try again.
      </p>

      {#if errorInfo}
        <div class="error-details bg-gray-50 rounded p-3 mb-6">
          <p class="text-sm text-gray-600 font-mono break-words">{errorInfo}</p>
        </div>
      {/if}

      <div class="flex gap-3">
        <button
          onclick={resetError}
          class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          Try Again
        </button>
        <button
          onclick={() => window.location.href = '/'}
          class="flex-1 px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition-colors font-medium"
        >
          Go Home
        </button>
      </div>
    </div>
  </div>
{:else}
  <slot />
{/if}

<style>
  .error-boundary {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
  }

  .error-container {
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
