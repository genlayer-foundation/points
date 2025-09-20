<script>
  import { removeToast } from '../lib/toastStore';
  import { onMount } from 'svelte';

  // Props using Svelte 5 syntax
  let { id, type, message, duration = 5000 } = $props();

  // State for controlling visibility during exit animation
  let visible = $state(true);
  let isClosing = $state(false);

  // Auto-dismiss with animation
  onMount(() => {
    if (duration !== null && duration > 0) {
      setTimeout(() => {
        handleClose();
      }, duration);
    }
  });

  // Get colors and icon based on type
  let colors = $derived(
    type === 'success' ? {
      bg: 'bg-green-50',
      border: 'border-green-400',
      text: 'text-green-800',
      icon: 'text-green-400'
    } : type === 'warning' ? {
      bg: 'bg-yellow-50',
      border: 'border-yellow-400',
      text: 'text-yellow-800',
      icon: 'text-yellow-400'
    } : type === 'error' ? {
      bg: 'bg-red-50',
      border: 'border-red-400',
      text: 'text-red-800',
      icon: 'text-red-400'
    } : {
      bg: 'bg-gray-50',
      border: 'border-gray-400',
      text: 'text-gray-800',
      icon: 'text-gray-400'
    }
  );

  function handleClose() {
    isClosing = true;
    // Wait for animation to complete before removing from store
    setTimeout(() => {
      visible = false;
      removeToast(id);
    }, 300);
  }
</script>

{#if visible}
  <div
    class="toast max-w-md w-full {colors.bg} border-l-4 {colors.border} p-4 rounded-lg shadow-xl mb-4 cursor-pointer {isClosing ? 'toast-exit' : 'toast-enter'}"
    onclick={handleClose}
    role="alert"
    aria-live="polite"
  >
    <div class="flex">
      <div class="flex-shrink-0">
        {#if type === 'success'}
          <!-- Success icon (checkmark) -->
          <svg class="h-5 w-5 {colors.icon}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
        {:else if type === 'warning'}
          <!-- Warning icon (exclamation) -->
          <svg class="h-5 w-5 {colors.icon}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
        {:else if type === 'error'}
          <!-- Error icon (X circle) -->
          <svg class="h-5 w-5 {colors.icon}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        {/if}
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm {colors.text}">
          {message}
        </p>
      </div>
    </div>
  </div>
{/if}

<style>
  /* Slide in animation */
  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  /* Fade out animation */
  @keyframes fadeOut {
    from {
      transform: translateX(0);
      opacity: 1;
    }
    to {
      transform: translateX(100px);
      opacity: 0;
    }
  }

  .toast-enter {
    animation: slideIn 0.3s ease-out forwards;
  }

  .toast-exit {
    animation: fadeOut 0.3s ease-out forwards;
  }
</style>