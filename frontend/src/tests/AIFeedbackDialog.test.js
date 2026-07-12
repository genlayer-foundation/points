import { fireEvent, render, screen, waitFor } from '@testing-library/svelte/svelte5';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AIFeedbackDialog from '../components/AIFeedbackDialog.svelte';
import AIReviewSummary from '../components/AIReviewSummary.svelte';
import { stewardAPI } from '../lib/api.js';
import { toastStore } from '../lib/toastStore.js';

const submitAIFeedback = /** @type {any} */ (stewardAPI.submitAIFeedback);

const analysis = {
  id: 77,
  action: 'accept',
  confidence: 'high',
  sections: {
    engineering: { score: 2, reason: 'The implementation is coherent.' },
    frontend_ux: { score: 3, reason: 'The interface is usable.' }
  },
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
      engineering: { range: [3, 4], reason: 'Engineering needs a higher score.' },
      frontend_ux: { range: [4, 4], reason: 'Preserve this hidden correction.' }
    },
    error_claims: [
      { type: 'factual_error', text: 'First saved issue', anchor: 'engineering' },
      { type: 'missed_strength', text: 'Second saved issue', anchor: 'engineering' },
      { type: 'wrong_weight', text: 'Preserve the synthesis issue', anchor: 'synthesis' }
    ],
    updated_at: '2026-07-12T12:00:00Z',
    ...overrides
  };
}

function renderDialog(props = {}) {
  return render(AIFeedbackDialog, {
    props: {
      open: true,
      anchor: 'engineering',
      submission: { id: 42 },
      aiAnalysis: analysis,
      feedbackRecords: [feedbackRecord()],
      feedbackLoaded: true,
      canFileFeedback: true,
      currentUserId: 22,
      onRequestFeedback: vi.fn(),
      onSaved: vi.fn(),
      onClose: vi.fn(),
      ...props
    }
  });
}

describe('focused AI feedback components', () => {
  beforeEach(() => {
    submitAIFeedback.mockReset();
    toastStore.clearAll();
  });

  it('keeps the summary compact and opens only the requested feedback anchor', async () => {
    const onOpenFeedback = vi.fn();
    render(AIReviewSummary, {
      props: {
        submission: { id: 42 },
        aiAnalysis: analysis,
        feedbackRecords: [],
        feedbackLoaded: true,
        canFileFeedback: true,
        currentUserId: 22,
        onOpenFeedback
      }
    });

    expect(screen.queryByText(analysis.synthesis)).toBeNull();
    await fireEvent.click(screen.getByRole('button', { name: 'Show AI review synthesis' }));
    expect(screen.getByText(analysis.synthesis)).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: 'Flag synthesis issue' }));
    await fireEvent.change(screen.getByLabelText('Open AI feedback section'), {
      target: { value: 'decision' }
    });
    expect(onOpenFeedback).toHaveBeenNthCalledWith(1, 'synthesis');
    expect(onOpenFeedback).toHaveBeenNthCalledWith(2, 'decision');
  });

  it('uses the overall reason fallback and renders trusted synthesis markdown safely', async () => {
    render(AIReviewSummary, {
      props: {
        submission: { id: 42 },
        aiAnalysis: {
          ...analysis,
          synthesis: '',
          overall_reason: 'Fallback **analysis** with the benchmark result.'
        }
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Show AI review synthesis' }));
    expect(screen.getByText('analysis').tagName).toBe('STRONG');
    expect(screen.getByText(/Fallback/)).toBeTruthy();
  });

  it('marks the AI accurate after lazy-loading the current OCC token', async () => {
    const record = feedbackRecord();
    const saved = feedbackRecord({
      verdict: 'agree',
      criteria: {},
      error_claims: [],
      updated_at: '2026-07-12T12:05:00Z'
    });
    const onRequestFeedback = vi.fn().mockResolvedValue([record]);
    const onSaved = vi.fn();
    submitAIFeedback.mockResolvedValueOnce({ data: saved });
    render(AIReviewSummary, {
      props: {
        submission: { id: 42 },
        aiAnalysis: analysis,
        feedbackRecords: [],
        feedbackLoaded: false,
        canFileFeedback: true,
        currentUserId: 22,
        onRequestFeedback,
        onSaved
      }
    });

    await fireEvent.click(screen.getByRole('button', { name: 'Mark AI accurate' }));

    await waitFor(() => expect(submitAIFeedback).toHaveBeenCalledWith(42, {
      verdict: 'agree',
      review_proposal_id: 77,
      expected_updated_at: record.updated_at
    }));
    expect(onRequestFeedback).toHaveBeenCalledWith();
    expect(onSaved).toHaveBeenCalledWith(saved);
  });

  it('preserves other anchors while reducing a legacy duplicate on one criterion', async () => {
    const saved = feedbackRecord({
      criteria: {
        engineering: { range: [4, 4], reason: 'Engineering needs a higher score.' },
        frontend_ux: { range: [4, 4], reason: 'Preserve this hidden correction.' }
      },
      error_claims: [
        { type: 'missed_strength', text: 'Second saved issue', anchor: 'engineering' },
        { type: 'wrong_weight', text: 'Preserve the synthesis issue', anchor: 'synthesis' }
      ],
      updated_at: '2026-07-12T12:05:00Z'
    });
    const onClose = vi.fn();
    submitAIFeedback.mockResolvedValueOnce({ data: saved });
    renderDialog({ onClose });

    expect(await screen.findByText(/This saved feedback has 2 issues/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Add flagged issue' })).toBeNull();
    await fireEvent.change(screen.getByLabelText('Minimum Engineering score'), {
      target: { value: '4' }
    });
    await fireEvent.change(screen.getByLabelText('Maximum Engineering score'), {
      target: { value: '4' }
    });
    await fireEvent.click(screen.getAllByRole('button', { name: 'Remove flagged issue' })[0]);
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(submitAIFeedback).toHaveBeenCalledTimes(1));
    const payload = submitAIFeedback.mock.calls[0][1];
    expect(payload.expected_updated_at).toBe('2026-07-12T12:00:00Z');
    expect(payload.criteria.engineering.range).toEqual([4, 4]);
    expect(payload.criteria.frontend_ux).toEqual({
      range: [4, 4],
      reason: 'Preserve this hidden correction.'
    });
    expect(payload.error_claims).toEqual([
      expect.objectContaining({ text: 'Second saved issue', anchor: 'engineering' }),
      expect.objectContaining({ text: 'Preserve the synthesis issue', anchor: 'synthesis' })
    ]);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('allows one new issue for an empty anchor and no second issue', async () => {
    const onClose = vi.fn();
    const saved = feedbackRecord({
      criteria: {},
      error_claims: [
        { type: 'missed_issue', text: 'A specific synthesis problem', anchor: 'synthesis' }
      ]
    });
    submitAIFeedback.mockResolvedValueOnce({ data: saved });
    renderDialog({
      anchor: 'synthesis',
      feedbackRecords: [],
      onClose
    });

    const addButton = await screen.findByRole('button', { name: 'Add flagged issue' });
    await fireEvent.click(addButton);
    expect(screen.queryByRole('button', { name: 'Add flagged issue' })).toBeNull();
    await fireEvent.change(screen.getByLabelText('Issue type'), {
      target: { value: 'missed_issue' }
    });
    await fireEvent.input(screen.getByLabelText('What is wrong'), {
      target: { value: 'A specific synthesis problem' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(submitAIFeedback).toHaveBeenCalledWith(
      42,
      expect.objectContaining({
        verdict: 'agree_with_corrections',
        review_proposal_id: 77,
        error_claims: [{
          type: 'missed_issue',
          text: 'A specific synthesis problem',
          anchor: 'synthesis'
        }]
      })
    ));
  });

  it('requires an explicit choice before rebasing a stale dialog draft', async () => {
    const latest = feedbackRecord({
      criteria: {
        engineering: { range: [2, 3], reason: 'Changed elsewhere.' },
        frontend_ux: { range: [4, 4], reason: 'Preserve this hidden correction.' }
      },
      updated_at: '2026-07-12T12:10:00Z'
    });
    const committed = feedbackRecord({
      criteria: {
        engineering: { range: [5, 5], reason: 'Engineering needs a higher score.' },
        frontend_ux: { range: [4, 4], reason: 'Preserve this hidden correction.' }
      },
      updated_at: '2026-07-12T12:15:00Z'
    });
    submitAIFeedback
      .mockRejectedValueOnce({ response: { status: 409, data: { detail: 'Feedback changed.' } } })
      .mockResolvedValueOnce({ data: committed });
    const onRequestFeedback = vi.fn().mockResolvedValue([latest]);
    renderDialog({ onRequestFeedback });

    await fireEvent.change(await screen.findByLabelText('Minimum Engineering score'), {
      target: { value: '5' }
    });
    await fireEvent.change(screen.getByLabelText('Maximum Engineering score'), {
      target: { value: '5' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    expect(await screen.findByRole('button', { name: 'Keep my draft' })).toBeTruthy();
    expect(/** @type {HTMLButtonElement} */ (screen.getByRole('button', { name: 'Save feedback' })).disabled).toBe(true);
    await fireEvent.click(screen.getByRole('button', { name: 'Keep my draft' }));
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));

    await waitFor(() => expect(submitAIFeedback).toHaveBeenCalledTimes(2));
    expect(submitAIFeedback.mock.calls[1][1]).toEqual(
      expect.objectContaining({
        expected_updated_at: latest.updated_at,
        criteria: expect.objectContaining({
          engineering: expect.objectContaining({ range: [5, 5] })
        })
      })
    );
  });

  it('loads the latest record only when the reviewer discards the stale draft', async () => {
    const latest = feedbackRecord({
      criteria: {
        engineering: { range: [1, 3], reason: 'Latest saved reason.' },
        frontend_ux: { range: [4, 4], reason: 'Preserve this hidden correction.' }
      },
      updated_at: '2026-07-12T12:10:00Z'
    });
    submitAIFeedback.mockRejectedValueOnce({
      response: { status: 409, data: { detail: 'Feedback changed.' } }
    });
    const onRequestFeedback = vi.fn().mockResolvedValue([latest]);
    renderDialog({ onRequestFeedback });

    await fireEvent.change(await screen.findByLabelText('Minimum Engineering score'), {
      target: { value: '5' }
    });
    await fireEvent.change(screen.getByLabelText('Maximum Engineering score'), {
      target: { value: '5' }
    });
    await fireEvent.click(screen.getByRole('button', { name: 'Save feedback' }));
    await fireEvent.click(await screen.findByRole('button', { name: 'Load latest' }));

    expect(/** @type {HTMLSelectElement} */ (screen.getByLabelText('Minimum Engineering score')).value).toBe('1');
    expect(/** @type {HTMLSelectElement} */ (screen.getByLabelText('Maximum Engineering score')).value).toBe('3');
    expect(/** @type {HTMLTextAreaElement} */ (screen.getByLabelText('Reason for Engineering score correction')).value).toBe('Latest saved reason.');
    expect(screen.queryByRole('button', { name: 'Keep my draft' })).toBeNull();
  });
});
