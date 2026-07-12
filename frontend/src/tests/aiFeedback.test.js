import { describe, expect, it } from 'vitest';
import {
  buildFeedbackPayload,
  initFeedbackState,
  validateFeedbackState
} from '../lib/aiFeedback.js';

const analysis = {
  id: 77,
  action: 'accept',
  sections: {
    genlayer_fit: { score: 3, reason: 'Fit reason' },
    engineering: { score: 2, reason: 'Engineering reason' }
  }
};

describe('AI review feedback helpers', () => {
  it('short-circuits untouched feedback to an explicit agreement', () => {
    const state = initFeedbackState(analysis);

    expect(buildFeedbackPayload(state)).toEqual({
      verdict: 'agree',
      review_proposal_id: 77
    });
  });

  it('derives correction and disagreement verdicts from explicit overrides', () => {
    const correction = initFeedbackState(analysis);
    correction.criteria.engineering = {
      overridden: true,
      min: 3,
      max: 4,
      reason: 'The implementation is stronger than scored.'
    };

    expect(buildFeedbackPayload(correction)).toEqual({
      verdict: 'agree_with_corrections',
      review_proposal_id: 77,
      criteria: {
        genlayer_fit: { agree: true },
        engineering: {
          range: [3, 4],
          reason: 'The implementation is stronger than scored.'
        }
      }
    });

    correction.decisionOverride = 'reject';
    correction.gateFailures = ['repo_does_not_build'];
    expect(buildFeedbackPayload(correction)).toMatchObject({
      verdict: 'disagree',
      correct_decision: 'reject',
      gate_failures: ['repo_does_not_build']
    });
  });

  it('does not classify unchanged AI values as human corrections', () => {
    const state = initFeedbackState(analysis);
    state.decisionOverride = 'accept';
    state.criteria.genlayer_fit = {
      overridden: true,
      min: 3,
      max: 3,
      reason: 'Same score'
    };

    expect(buildFeedbackPayload(state)).toEqual({
      verdict: 'agree',
      review_proposal_id: 77
    });
    expect(validateFeedbackState(state)).toContain('matches the AI score');

    state.criteria.genlayer_fit.max = 4;
    expect(buildFeedbackPayload(state)).toMatchObject({
      verdict: 'agree_with_corrections',
      criteria: {
        genlayer_fit: { range: [3, 4], reason: 'Same score' }
      }
    });
  });

  it('preserves previously stored same-value feedback when editing', () => {
    const state = initFeedbackState(analysis, {
      id: 9,
      review_proposal_id: 77,
      verdict: 'disagree',
      correct_decision: 'accept',
      criteria: {
        genlayer_fit: { range: [3, 3], reason: 'Previously stored' }
      }
    });

    expect(buildFeedbackPayload(state)).toMatchObject({
      verdict: 'disagree',
      correct_decision: 'accept',
      criteria: {
        genlayer_fit: { range: [3, 3], reason: 'Previously stored' }
      }
    });
    expect(validateFeedbackState(state)).toBeNull();
  });

  it('prunes empty claims and keeps populated claims anchored to their reasoning layer', () => {
    const state = initFeedbackState(analysis);
    state.errorClaims = [
      { clientId: 'empty', type: 'factual_error', text: '   ', evidenceRef: '', anchor: 'synthesis' },
      {
        clientId: 'claim',
        type: 'missed_issue',
        text: '  The analysis missed the authorization check.  ',
        evidenceRef: ' contracts/App.py:authorize ',
        anchor: 'engineering'
      }
    ];

    expect(buildFeedbackPayload(state).error_claims).toEqual([
      {
        type: 'missed_issue',
        text: 'The analysis missed the authorization check.',
        evidence_ref: 'contracts/App.py:authorize',
        anchor: 'engineering'
      }
    ]);
  });

  it('prunes a new blank claim from the payload but keeps it invalid in the editor', () => {
    const state = initFeedbackState(analysis);
    state.errorClaims = [{
      clientId: 'new-1',
      type: 'factual_error',
      text: '',
      evidenceRef: '',
      anchor: 'engineering'
    }];

    expect(buildFeedbackPayload(state)).toEqual({
      verdict: 'agree',
      review_proposal_id: 77
    });
    expect(validateFeedbackState(state)).toContain('Describe every flagged flaw');
  });

  it('hydrates and preserves API-valid feedback hidden from the AI analysis', () => {
    const state = initFeedbackState(analysis, {
      id: 8,
      review_proposal_id: 77,
      verdict: 'agree_with_corrections',
      criteria: {
        frontend_ux: { range: [1, 2], reason: 'Existing UI correction' }
      },
      error_claims: [
        { type: 'factual_error', text: 'Existing general claim' }
      ]
    });

    const payload = buildFeedbackPayload(state);
    expect(payload.criteria.frontend_ux).toEqual({
      range: [1, 2],
      reason: 'Existing UI correction'
    });
    expect(payload.error_claims[0]).toEqual({
      type: 'factual_error',
      text: 'Existing general claim'
    });
  });

  it('mirrors range, gate, claim, and anchor validation rules', () => {
    const state = initFeedbackState(analysis);
    state.criteria.genlayer_fit = { overridden: true, min: 4, max: 2, reason: '' };
    expect(validateFeedbackState(state)).toContain('GenLayer fit');

    state.criteria.genlayer_fit = { overridden: false, min: null, max: null, reason: '' };
    state.gateFailures = ['branding_only'];
    expect(validateFeedbackState(state)).toContain('overriding the decision to reject');

    state.gateFailures = [];
    state.errorClaims = [{ clientId: 'claim-1', type: 'not-a-type', text: 'A claim', evidenceRef: '', anchor: 'engineering' }];
    expect(validateFeedbackState(state)).toContain('flaw type');

    state.errorClaims = [{ clientId: 'claim-2', type: 'factual_error', text: 'A claim', evidenceRef: '', anchor: 'unknown' }];
    expect(validateFeedbackState(state)).toContain('reasoning section');

    state.errorClaims = [{ clientId: 'claim-3', type: 'factual_error', text: 'A claim', evidenceRef: '', anchor: 'synthesis' }];
    expect(validateFeedbackState(state)).toBeNull();
  });
});
