// Test helpers for frontend tests
import { render, waitFor } from '@testing-library/svelte/svelte5';
import { testUtils } from './setupTests';

/**
 * Renders a component and flushes sync updates
 * @param {Object} Component - The Svelte component to render
 * @param {Object} options - Render options (props, etc.)
 * @returns {Object} The rendered component
 */
export function renderWithEffects(Component, options = {}) {
  const result = render(Component, options);
  testUtils.flush(); // Flush initial render
  return result;
}

/**
 * Waits for a component's API calls to complete and flushes updates
 * @param {Function} apiCall - The API function to check for being called
 * @param {Object} params - Optional params to check the API call with
 * @returns {Promise} A promise that resolves when the API call is detected
 */
export async function waitForApiCall(apiCall, params = null) {
  await waitFor(() => {
    if (params) {
      expect(apiCall).toHaveBeenCalledWith(params);
    } else {
      expect(apiCall).toHaveBeenCalled();
    }
  }, { timeout: 2000 });
  
  await testUtils.waitAndFlush(50); // Wait a bit and flush updates
}
