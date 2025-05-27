# Tally Frontend Tests

This directory contains high-level tests for the Tally frontend application. The tests are designed to verify that:

1. All pages load correctly without errors
2. API fetch operations are called with correct parameters
3. Fetched data is properly displayed in the UI

## Test Structure

- `setupTests.js` - Test environment configuration and global mocks
- `testHelpers.js` - Utility functions and mock data generators
- `routes.test.js` - Tests for all application routes and pages
- `api.test.js` - Tests for API integrations and data display
- `NotFound.test.js` - Simple test for the NotFound page

## Running Tests

To run all tests:

```bash
npm test
```

To run tests in watch mode:

```bash
npm run test:watch
```

To get test coverage report:

```bash
npm run test:coverage
```

## Test Architecture

These tests use:

- **Vitest** - Test runner compatible with Vite
- **Testing Library** - For rendering and querying Svelte components
- **JSDOM** - For browser-like environment

## Mocking Strategy

The tests mock all external API calls to ensure tests are fast, reliable, and don't depend on external services. The mocking approach:

1. Mock all API functions in `lib/api.js`
2. Provide realistic mock data for common API responses
3. Test both success and error states

## Adding New Tests

When adding new features or components:

1. Add component-specific tests in new files if needed
2. For new routes, add tests to `routes.test.js`
3. For new API calls, add tests to `api.test.js`
4. Update `testHelpers.js` with any new mock data factories

## Best Practices

- Test both success and error states
- Verify loading indicators appear during API calls
- Check that error messages are displayed when APIs fail
- Ensure all data fetched from APIs is properly displayed
- Test pagination and filtering functionality where applicable

## Svelte 5 Compatibility Note

Some tests are currently skipped (using `it.skip()`) due to compatibility issues with Svelte 5's reactivity system, particularly:

1. Tests for the ParticipantProfile component - Issues with the reactive `$effect` and router parameters
2. Tests for API calls in Dashboard and Contributions components - Timing issues with component lifecycle

These tests need to be updated once we have a better understanding of how to properly test Svelte 5 components with Testing Library. The main issues are:

- The timing of API calls in the `onMount` lifecycle hook
- The `$effect` function and its interaction with reactive state
- Router parameter subscriptions and proper cleanup in tests

When updating these tests, consider:
- Using more robust waiting mechanisms for reactive updates
- Providing proper mocks for Svelte's reactivity system
- Refactoring components to make them more testable with the new Svelte 5 patterns