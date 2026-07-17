import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  push: vi.fn(),
  showError: vi.fn(),
}));

vi.mock('svelte-spa-router', () => ({
  push: mocks.push,
}));

vi.mock('../lib/api.js', () => ({
  poapsAPI: {
    list: mocks.list,
  },
}));

vi.mock('../lib/toastStore.js', () => ({
  showError: mocks.showError,
}));

import CommunityPoaps from '../routes/CommunityPoaps.svelte';

const poap = (id, title) => ({
  id,
  slug: `poap-${id}`,
  title,
  event_start_at: '2026-07-01T12:00:00Z',
});

const page = (results, { count = results.length, next = null } = {}) => ({
  data: { results, count, next },
});

const apiError = (message) => ({
  response: { data: { error: message } },
});

describe('Community POAP recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.list.mockReset();
  });

  it('shows an initial error instead of an empty state and retries', async () => {
    mocks.list
      .mockRejectedValueOnce(apiError('POAP service unavailable'))
      .mockResolvedValueOnce(page([poap(1, 'Recovered POAP')]));

    render(CommunityPoaps);

    expect(await screen.findByText("Couldn't load POAPs")).toBeTruthy();
    expect(screen.queryByText('No POAPs found')).toBeNull();

    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    expect(await screen.findByRole('button', { name: 'Open Recovered POAP' })).toBeTruthy();
    expect(mocks.list).toHaveBeenNthCalledWith(2, {
      page: 1,
      page_size: 48,
      ordering: '-event_start_at',
    });
  });

  it('keeps a failed filter request recoverable with the submitted filter', async () => {
    mocks.list
      .mockResolvedValueOnce(page([poap(1, 'Original POAP')]))
      .mockRejectedValueOnce(apiError('Search unavailable'))
      .mockResolvedValueOnce(page([poap(2, 'Filtered POAP')]));

    render(CommunityPoaps);
    expect(await screen.findByRole('button', { name: 'Open Original POAP' })).toBeTruthy();

    await fireEvent.input(screen.getByRole('textbox', { name: 'Search POAPs' }), { target: { value: 'filtered' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Search POAPs' }));

    expect(await screen.findByText("Couldn't load POAPs")).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));

    expect(await screen.findByRole('button', { name: 'Open Filtered POAP' })).toBeTruthy();
    expect(mocks.list).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 48,
      ordering: '-event_start_at',
      search: 'filtered',
    });
  });

  it('preserves loaded POAPs when load more fails and retries the same page', async () => {
    mocks.list
      .mockResolvedValueOnce(page([poap(1, 'First POAP')], { count: 2, next: '/poaps/?page=2' }))
      .mockRejectedValueOnce(apiError('Next page unavailable'))
      .mockResolvedValueOnce(page([poap(2, 'Second POAP')], { count: 2 }));

    render(CommunityPoaps);
    expect(await screen.findByRole('button', { name: 'Open First POAP' })).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: /Load more POAPs/ }));

    expect(await screen.findByRole('button', { name: 'Retry loading more' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Open First POAP' })).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: 'Retry loading more' }));

    expect(await screen.findByRole('button', { name: 'Open Second POAP' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Open First POAP' })).toBeTruthy();
    expect(mocks.list).toHaveBeenNthCalledWith(3, {
      page: 2,
      page_size: 48,
      ordering: '-event_start_at',
    });
  });

  it('ignores a stale response after a newer filter request succeeds', async () => {
    let resolveInitial;
    mocks.list
      .mockImplementationOnce(() => new Promise((resolve) => {
        resolveInitial = resolve;
      }))
      .mockResolvedValueOnce(page([poap(2, 'Newest POAP')]));

    render(CommunityPoaps);
    await waitFor(() => expect(mocks.list).toHaveBeenCalledTimes(1));

    await fireEvent.input(screen.getByRole('textbox', { name: 'Search POAPs' }), { target: { value: 'newest' } });
    await fireEvent.click(screen.getByRole('button', { name: 'Search POAPs' }));

    expect(await screen.findByRole('button', { name: 'Open Newest POAP' })).toBeTruthy();
    resolveInitial(page([poap(1, 'Stale POAP')]));
    await Promise.resolve();

    expect(screen.queryByRole('button', { name: 'Open Stale POAP' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Open Newest POAP' })).toBeTruthy();
  });

  it('ignores a pending request failure after the route unmounts', async () => {
    let rejectRequest;
    mocks.list.mockImplementationOnce(() => new Promise((_, reject) => {
      rejectRequest = reject;
    }));

    const { unmount } = render(CommunityPoaps);
    await waitFor(() => expect(mocks.list).toHaveBeenCalledTimes(1));
    unmount();

    rejectRequest(apiError('Late failure'));
    await Promise.resolve();
    await Promise.resolve();

    expect(mocks.showError).not.toHaveBeenCalled();
  });
});
