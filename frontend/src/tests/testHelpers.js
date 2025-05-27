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

/**
 * A utility for testing reactive component rendering
 * @param {Function} renderFn - Function that renders the component
 * @param {Function} checkFn - Function to check the rendered output
 * @param {number} timeout - Timeout for the check
 * @returns {Promise} A promise that resolves when the check passes
 */
export async function waitForRender(renderFn, checkFn, timeout = 2000) {
  const result = renderFn();
  await waitFor(checkFn, { timeout });
  await testUtils.waitAndFlush();
  return result;
}

// Mock data factory functions
export const createMockLeaderboardEntry = (rank, name, points) => ({
  rank,
  user: {
    name,
    email: `${name.toLowerCase().replace(' ', '.')}@example.com`
  },
  total_points: points,
  user_details: {
    name,
    email: `${name.toLowerCase().replace(' ', '.')}@example.com`
  }
});

export const createMockContribution = (id, userName, type, date, points, globalPoints, hasEvidence = true) => ({
  id,
  user: {
    name: userName,
    email: `${userName.toLowerCase().replace(' ', '.')}@example.com`
  },
  contribution_type_name: type,
  contribution_type: id,
  contribution_date: date,
  points,
  frozen_global_points: globalPoints,
  multiplier_at_creation: globalPoints / points,
  evidence_items: hasEvidence 
    ? [{ description: 'PR Link', url: `https://github.com/example/repo/pull/${id}` }] 
    : []
});

// Mock response generators
export const generateMockLeaderboardResponse = (count = 3) => {
  const results = [];
  for (let i = 1; i <= count; i++) {
    results.push(createMockLeaderboardEntry(i, `User ${i}`, 100 - (i - 1) * 10));
  }
  
  return {
    data: {
      results,
      count
    }
  };
};

export const generateMockContributionsResponse = (count = 3) => {
  const results = [];
  for (let i = 1; i <= count; i++) {
    const type = i % 2 === 0 ? 'Documentation' : 'Code';
    const points = i % 2 === 0 ? 5 : 10;
    const globalPoints = points * 2;
    const date = `2023-01-${String(i).padStart(2, '0')}`;
    
    results.push(createMockContribution(i, `User ${i}`, type, date, points, globalPoints, i % 3 !== 0));
  }
  
  return {
    data: {
      results,
      count
    }
  };
};

// Test utilities for working with components and API mocks
export const mockApiSuccess = (apiMock, data) => {
  apiMock.mockResolvedValue(data);
};

export const mockApiFailure = (apiMock, errorMessage = 'API Error') => {
  apiMock.mockRejectedValue(new Error(errorMessage));
};

export const mockApiDelay = (apiMock, data, delayMs = 200) => {
  apiMock.mockImplementation(() => 
    new Promise(resolve => setTimeout(() => resolve(data), delayMs))
  );
};

// Data matchers for API calls
export const matchesLeaderboardParams = (params = {}) => {
  return expect.objectContaining(params);
};

export const matchesContributionsParams = (params = {}) => {
  return expect.objectContaining({
    page: expect.any(Number),
    limit: expect.any(Number),
    ...params
  });
};