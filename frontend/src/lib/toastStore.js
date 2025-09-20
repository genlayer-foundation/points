/**
 * Global toast notification store for the application
 * Provides functions to show success, warning, and error messages
 */

import { writable } from 'svelte/store';

// Create the store with an empty array of toasts
function createToastStore() {
  const { subscribe, update } = writable([]);

  let nextId = 1;

  return {
    subscribe,

    /**
     * Add a new toast notification
     * @param {'success' | 'warning' | 'error'} type - Type of toast
     * @param {string} message - Message to display
     * @param {number|null} duration - Duration in ms (null = persistent)
     */
    addToast: (type, message, duration = 5000) => {
      const id = nextId++;
      const toast = {
        id,
        type,
        message,
        duration
      };

      // Add the toast to the store
      update(toasts => [...toasts, toast]);

      // Note: Auto-dismiss is now handled by the Toast component itself

      return id;
    },

    /**
     * Remove a specific toast by ID
     * @param {number} id - Toast ID to remove
     */
    removeToast: (id) => {
      update(toasts => toasts.filter(t => t.id !== id));
    },

    /**
     * Clear all toasts
     */
    clearAll: () => {
      update(() => []);
    }
  };
}

// Create and export the store instance
export const toastStore = createToastStore();

// Convenience functions for common use cases
export const addToast = toastStore.addToast;
export const removeToast = toastStore.removeToast;
export const clearToasts = toastStore.clearAll;

// Type-specific convenience functions
export const showSuccess = (message, duration) =>
  toastStore.addToast('success', message, duration);

export const showError = (message, duration) =>
  toastStore.addToast('error', message, duration);

export const showWarning = (message, duration) =>
  toastStore.addToast('warning', message, duration);