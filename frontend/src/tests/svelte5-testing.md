# Svelte 5 Testing Guide

This guide explains the current approach for testing Svelte 5 components with Vitest and Testing Library.

## Known Issues

When testing Svelte 5 components, particularly those with `onMount` and `$effect` hooks, you may encounter the following issues:

1. API calls in `onMount` not being detected in tests
2. `$effect` callbacks causing "Cannot read properties of undefined (reading 'unsubscribe')" errors
3. Reactive state updates not being properly reflected in tests
4. Router parameter subscriptions failing in test environment

## Current Workarounds

### For Components Using `onMount` for API Calls

To test components that make API calls in `onMount`:

1. Use `mockImplementation` instead of `mockResolvedValue` to ensure the mock is properly tracked:

```javascript
// Instead of this:
apiFunction.mockResolvedValue(mockData);

// Do this:
apiFunction.mockImplementation(() => Promise.resolve(mockData));
```

2. Use `await waitFor` with a longer timeout to ensure the component has time to render and update:

```javascript
await waitFor(() => {
  expect(screen.queryByText('Expected Text')).not.toBeNull();
}, { timeout: 2000 });
```

3. For assertions on API calls, use `waitFor` instead of immediate assertions:

```javascript
// Instead of this:
expect(apiFunction).toHaveBeenCalled();

// Do this:
await waitFor(() => {
  expect(apiFunction).toHaveBeenCalled();
}, { timeout: 2000 });
```

### For Components Using `$effect` with Subscriptions

For components that use `$effect` with subscriptions (like router params):

1. Skip these tests until a better solution is found
2. Consider creating wrapper components specifically for testing that don't rely on subscriptions
3. Mock subscriptions completely in setupTests.js

```javascript
// In setupTests.js
global.createTestSubscription = (value) => {
  return {
    subscribe: vi.fn(fn => {
      fn(value);
      return { 
        unsubscribe: vi.fn() 
      };
    })
  };
};

// Mock svelte-spa-router with proper subscription pattern
vi.mock('svelte-spa-router', () => {
  return {
    default: vi.fn(),
    push: vi.fn(),
    pop: vi.fn(),
    location: vi.fn(),
    querystring: vi.fn(),
    params: createTestSubscription({ address: '0x123' }) // Always provide an address parameter
  };
});
```

### Testing with Loading Indicators

When testing components with loading indicators:

```javascript
it('shows loading indicators initially', () => {
  render(Component);
  
  // Use queryAllByText since there might be multiple loading indicators
  const loadingIndicators = screen.queryAllByText(/\.\.\.|\u2026|loading/i);
  expect(loadingIndicators.length).toBeGreaterThan(0);
});
```

## Our Testing Solution

Our current solution involves:

1. **Simple Test Assertions**: Focus on testing that components render correctly rather than testing complex interactions or lifecycles.

2. **Component Props Testing**: Testing components by providing props directly rather than relying on API calls.

3. **Mock Setup**: Setting up comprehensive mocks in setupTests.js:
   - API functions with immediate resolved values
   - Router params with proper subscribe/unsubscribe pattern

4. **Utility Functions**: We've created utility functions in testHelpers.js for common testing patterns:
   - `renderWithEffects`: Renders a component and ensures state is flushed
   - `waitForApiCall`: Waits for an API call to be made with specific parameters
   - `waitForRender`: Waits for a component to fully render

5. **State Flushing**: Using `flushSync` from Svelte to ensure reactive updates are processed.

## Best Practices for Testing Svelte 5 Components

1. Use `queryByText` instead of `getByText` to avoid exceptions when elements aren't found
2. Always use `waitFor` with a generous timeout (1000-2000ms) when testing async behavior
3. Clear mocks before each test with `apiFunction.mockClear()`
4. Use `mockImplementationOnce` for specific test cases to avoid affecting other tests
5. When testing error states, use `mockRejectedValueOnce` to ensure it only affects that test
6. For multiple elements with the same text, use `queryAllByText` instead of `queryByText`

## Future Improvements

Once the Svelte 5 testing ecosystem matures, we should revisit the following:

1. Create proper utility functions for testing components with `$effect` hooks
2. Investigate better ways to mock router subscriptions
3. Consider using Svelte's testing utilities directly when they become available
4. Develop custom test renderers that better handle Svelte 5's reactivity model

## References

- [Testing Library documentation](https://testing-library.com/docs/)
- [Vitest documentation](https://vitest.dev/guide/)
- [Svelte 5 documentation](https://svelte.dev/docs)