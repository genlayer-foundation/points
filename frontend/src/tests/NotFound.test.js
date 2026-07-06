import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte/svelte5';
import NotFound from '../routes/NotFound.svelte';

describe('NotFound Page', () => {
  it('renders a 404 message', () => {
    render(NotFound);
    expect(screen.getByText(/error 404/i)).toBeDefined();
  });

  it('provides navigation back to homepage', () => {
    render(NotFound);
    const homeLink = screen.getByText(/back to home/i);
    expect(homeLink).toBeDefined();
    expect(homeLink.getAttribute('href')).toBe('/');
  });
});