import { describe, expect, it } from 'vitest';
import { submissionErrorMessage } from '../lib/submissionErrors.js';

describe('submissionErrorMessage', () => {
  it('reads nested DRF response and evidence errors', () => {
    expect(submissionErrorMessage({
      response: {
        data: {
          more_info_response: {
            request_id: ['Refresh and answer the latest request.']
          }
        }
      }
    }, 'Fallback')).toBe('Refresh and answer the latest request.');

    expect(submissionErrorMessage({
      response: {
        data: {
          evidence_items: [{ url: ['Use an accepted evidence URL.'] }]
        }
      }
    }, 'Fallback')).toBe('Use an accepted evidence URL.');
  });

  it('preserves plain errors and falls back for empty response objects', () => {
    expect(submissionErrorMessage(
      new Error('Submission is no longer visible.'),
      'Fallback'
    )).toBe('Submission is no longer visible.');

    expect(submissionErrorMessage({
      response: {
        data: {
          more_info_response: {},
          evidence_items: []
        }
      }
    }, 'Fallback')).toBe('Fallback');
  });
});
