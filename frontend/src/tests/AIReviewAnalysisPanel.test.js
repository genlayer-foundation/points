import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AIReviewAnalysisPanel from '../components/AIReviewAnalysisPanel.svelte';
import { stewardAPI } from '../lib/api.js';
import { toastStore } from '../lib/toastStore.js';

const analysis = {
  id: 77,
  action: 'accept',
  sections: {
    engineering: { score: 2, reason: 'The implementation is coherent.' }
  },
  gate_failures: [],
  extras: [],
  synthesis: 'The project meets the review bar.'
};

function feedbackRecord(overrides = {}) {
  return {
    id: 7,
    review_proposal_id: 77,
    reviewer_id: 22,
    verdict: 'agree_with_corrections',
    correct_decision: null,
    gate_failures: [],
    criteria: {
      engineering: { range: [3, 4], reason: 'Saved correction' }
    },
    error_claims: [],
    updated_at: '2026-07-12T12:00:00Z',
    ...overrides
  };
}

function renderPanel(props = {}) {
  return render(AIReviewAnalysisPanel, {
    props: {
      submission: { id: 42 },
      aiAnalysis: analysis,
      feedbackRecords: [feedbackRecord()],
      feedbackLoaded: true,
      canFileFeedback: true,
      currentUserId: 22,
      ...props
    }
  });
}

async function editEngineeringScore(value = '4') {
  await fireEvent.click(screen.getByRole('button', { name: 'Show AI review analysis' }));
  await fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
  await fireEvent.change(screen.getByLabelText('Override Engineering score'), {
    target: { value }
  });
}

describe('AIReviewAnalysisPanel save boundaries', () => {
  beforeEach(() => {
    stewardAPI.submitAIFeedback.mockReset();
    toastStore.clearAll();
  });

  it('reports a callback refresh failure without presenting the committed POST as failed', async () => {
    const savedRecord = feedbackRecord({
      criteria: {
        engineering: { range: [4, 4], reason: 'Saved correction' },
        frontend_ux: {
          range: [1, 2],
          reason: 'Server-normalized hidden correction'
        }
      },
      updated_at: '2026-07-12T12:05:00Z'
    });
    stewardAPI.submitAIFeedback.mockResolvedValueOnce({ data: savedRecord });
    const onSaved = vi.fn().mockRejectedValue(new Error('refresh failed'));
    renderPanel({ onSaved });

    await editEngineeringScore();
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(savedRecord));
    expect(stewardAPI.submitAIFeedback).toHaveBeenCalledWith(
      42,
      expect.objectContaining({
        expected_updated_at: '2026-07-12T12:00:00Z',
        criteria: expect.objectContaining({
          engineering: expect.objectContaining({ range: [4, 4] })
        })
      })
    );
    await waitFor(() => {
      expect(get(toastStore)).toEqual([
        expect.objectContaining({
          type: 'error',
          message: 'Feedback was saved, but the local view could not be refreshed.'
        })
      ]);
    });
    expect(screen.getByRole('button', { name: 'Edit' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Cancel edit' })).toBeNull();
    expect(screen.getByText('Server-normalized hidden correction')).toBeTruthy();
  });

  it('requires an explicit overwrite choice before rebasing a stale draft', async () => {
    const latestRecord = feedbackRecord({
      criteria: { engineering: { range: [2, 3], reason: 'Other session' } },
      updated_at: '2026-07-12T12:10:00Z'
    });
    const committedRecord = feedbackRecord({
      criteria: { engineering: { range: [4, 4], reason: 'Saved correction' } },
      updated_at: '2026-07-12T12:15:00Z'
    });
    stewardAPI.submitAIFeedback
      .mockRejectedValueOnce({
        response: { status: 409, data: { detail: 'Feedback changed.' } }
      })
      .mockResolvedValueOnce({ data: committedRecord });
    const onRequestFeedback = vi.fn().mockResolvedValue([latestRecord]);
    renderPanel({ onRequestFeedback, onSaved: vi.fn() });

    await editEngineeringScore();
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(onRequestFeedback).toHaveBeenCalledWith(true));
    expect(screen.getByLabelText('Override Engineering score').value).toBe('4');
    expect(get(toastStore)).toEqual([
      expect.objectContaining({
        message: 'Feedback changed in another session. Choose whether to load the latest feedback or keep your draft.'
      })
    ]);
    expect(screen.getByRole('button', { name: 'Save feedback' }).disabled).toBe(true);

    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));
    expect(stewardAPI.submitAIFeedback).toHaveBeenCalledTimes(1);

    toastStore.clearAll();
    await fireEvent.click(screen.getByRole('button', { name: 'Keep my draft' }));
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(stewardAPI.submitAIFeedback).toHaveBeenCalledTimes(2));
    expect(stewardAPI.submitAIFeedback.mock.calls[1][1]).toEqual(
      expect.objectContaining({
        expected_updated_at: latestRecord.updated_at,
        criteria: expect.objectContaining({
          engineering: expect.objectContaining({ range: [4, 4] })
        })
      })
    );
  });

  it('loads the latest feedback only after the reviewer chooses to discard the draft', async () => {
    const latestRecord = feedbackRecord({
      criteria: { engineering: { range: [2, 3], reason: 'Other session' } },
      updated_at: '2026-07-12T12:10:00Z'
    });
    stewardAPI.submitAIFeedback.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Feedback changed.' } }
    });
    const onRequestFeedback = vi.fn().mockResolvedValue([latestRecord]);
    renderPanel({ onRequestFeedback, onSaved: vi.fn() });

    await editEngineeringScore();
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Load latest' })).toBeTruthy());
    expect(screen.getByLabelText('Override Engineering score').value).toBe('4');

    await fireEvent.click(screen.getByRole('button', { name: 'Load latest' }));

    expect(screen.getByLabelText('Override Engineering score').value).toBe('2');
    expect(screen.getByLabelText('Maximum Engineering score').value).toBe('3');
    expect(screen.getByLabelText('Reason for Engineering score correction').value).toBe('Other session');
    expect(screen.queryByRole('button', { name: 'Keep my draft' })).toBeNull();
    expect(stewardAPI.submitAIFeedback).toHaveBeenCalledTimes(1);
  });

  it('preserves a first-save draft when the conflict refresh introduces a record', async () => {
    const latestRecord = feedbackRecord({
      criteria: { engineering: { range: [2, 3], reason: 'Other session' } },
      updated_at: '2026-07-12T12:10:00Z'
    });
    stewardAPI.submitAIFeedback.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Feedback changed.' } }
    });
    const onRequestFeedback = vi.fn();
    let releaseRefresh = () => {};
    const { rerender } = renderPanel({
      feedbackRecords: [],
      onRequestFeedback,
      onSaved: vi.fn()
    });
    onRequestFeedback.mockImplementation(async () => {
      await new Promise(resolve => {
        releaseRefresh = resolve;
      });
      await rerender({ feedbackRecords: [latestRecord] });
      return [latestRecord];
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Show AI review analysis' }));
    await fireEvent.change(screen.getByLabelText('Override Engineering score'), {
      target: { value: '4' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(onRequestFeedback).toHaveBeenCalledWith(true));
    await fireEvent.click(screen.getByRole('button', { name: 'Hide AI review analysis' }));
    expect(screen.getByRole('button', { name: 'Show AI review analysis' })).toBeTruthy();
    releaseRefresh();

    await waitFor(() => expect(screen.getByRole('button', { name: 'Keep my draft' })).toBeTruthy());
    expect(screen.getByRole('button', { name: 'Hide AI review analysis' })).toBeTruthy();
    await fireEvent.click(screen.getByRole('button', { name: 'Keep my draft' }));

    expect(screen.getByLabelText('Override Engineering score').value).toBe('4');
    expect(stewardAPI.submitAIFeedback).toHaveBeenCalledTimes(1);
  });
});
