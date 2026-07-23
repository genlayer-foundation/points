import { fireEvent, render, screen } from '@testing-library/svelte/svelte5';
import { describe, expect, it } from 'vitest';
import StewardSearchBar from '../components/StewardSearchBar.svelte';


describe('StewardSearchBar lifecycle autocomplete', () => {
  it('suggests the recorded more-info request filter used by pending queues', async () => {
    render(StewardSearchBar);
    const input = screen.getByRole('combobox');

    await fireEvent.input(input, { target: { value: 'has:more' } });

    expect(screen.getByRole('option', {
      name: 'has:more-info-request',
    })).toBeTruthy();
  });

  it('suggests and inserts the more-info resubmission filter', async () => {
    render(StewardSearchBar);
    const input = screen.getByRole('combobox');

    await fireEvent.input(input, { target: { value: 'is:more' } });

    expect(input.getAttribute('aria-expanded')).toBe('true');
    const suggestion = screen.getByRole('option', {
      name: 'is:more-info-resubmitted',
    });
    expect(suggestion.getAttribute('aria-selected')).toBe('true');

    await fireEvent.click(suggestion);

    expect(input.value).toBe('is:more-info-resubmitted ');
    expect(input.getAttribute('aria-expanded')).toBe('false');
  });

  it('offers the negated lifecycle filter through not:', async () => {
    render(StewardSearchBar);
    const input = screen.getByRole('combobox');

    await fireEvent.input(input, { target: { value: 'not:more' } });

    expect(screen.getByRole('option', {
      name: 'not:more-info-resubmitted',
    })).toBeTruthy();

    await fireEvent.keyDown(input, { key: 'Enter' });

    expect(input.value).toBe('not:more-info-resubmitted ');
    expect(input.getAttribute('aria-expanded')).toBe('false');
  });

  it('suggests escalated queue filters and their negation', async () => {
    render(StewardSearchBar);
    const input = screen.getByRole('combobox');

    await fireEvent.input(input, { target: { value: 'is:esc' } });
    expect(screen.getByRole('option', { name: 'is:escalated' })).toBeTruthy();

    await fireEvent.input(input, { target: { value: 'not:esc' } });
    expect(screen.getByRole('option', { name: 'not:escalated' })).toBeTruthy();
  });
});
