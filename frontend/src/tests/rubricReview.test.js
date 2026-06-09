import { describe, expect, it } from 'vitest';
import {
  buildRubricReviewPayload,
  calculateRubricPoints,
  defaultRubricSections,
  hydrateRubricState,
  isProjectReviewFlow,
  validateRubricReviewState
} from '../lib/rubricReview.js';

function validState(overrides = {}) {
  const sections = defaultRubricSections();
  for (const key of Object.keys(sections)) {
    sections[key] = {
      score: 2,
      reason: `${key} reason`
    };
  }
  return {
    gateFailures: [],
    sections,
    extras: ['live_deployment'],
    overallReason: 'Overall reason',
    ...overrides
  };
}

describe('rubricReview helpers', () => {
  it('detects Project review flow only', () => {
    expect(isProjectReviewFlow('builder_project')).toBe(true);
    expect(isProjectReviewFlow('standard')).toBe(false);
  });

  it('builds a full rubric payload for passing gate reviews', () => {
    const payload = buildRubricReviewPayload(validState());

    expect(payload.gate_failures).toEqual([]);
    expect(payload.sections.genlayer_fit).toEqual({
      score: 2,
      reason: 'genlayer_fit reason'
    });
    expect(payload.extras).toEqual(['live_deployment']);
    expect(payload.overall_reason).toBe('Overall reason');
  });

  it('builds a gate-failure payload without section scores', () => {
    const payload = buildRubricReviewPayload(validState({
      gateFailures: ['repo_does_not_build']
    }));

    expect(payload.gate_failures).toEqual(['repo_does_not_build']);
    expect(payload.sections).toEqual({});
  });

  it('calculates rubric points from weighted criteria and verified extras', () => {
    const state = validState({
      sections: {
        genlayer_fit: { score: 4, reason: '' },
        contract_quality: { score: 3, reason: '' },
        engineering: { score: 4, reason: '' },
        frontend_ux: { score: 2, reason: '' }
      },
      extras: ['live_deployment', 'demo_video']
    });

    expect(calculateRubricPoints(state)).toBe(126);
  });

  it('rejects gate failures with non-reject actions', () => {
    const error = validateRubricReviewState(
      validState({ gateFailures: ['repo_does_not_build'] }),
      'accept'
    );

    expect(error).toContain('Gate failures');
  });

  it('allows blank section reasons when the gate passes', () => {
    const state = validState();
    state.sections.engineering.reason = '';

    const error = validateRubricReviewState(state, 'accept');

    expect(error).toBeNull();
  });

  it('requires an overall reason', () => {
    const error = validateRubricReviewState(
      validState({ overallReason: '   ' }),
      'accept'
    );

    expect(error).toBe('Add an overall rubric reason before submitting the proposal.');
  });

  it('rejects section scores outside 0-5', () => {
    const tooLow = validState();
    tooLow.sections.genlayer_fit.score = -1;
    expect(validateRubricReviewState(tooLow, 'accept')).toContain('GenLayer fit');

    const tooHigh = validState();
    tooHigh.sections.genlayer_fit.score = 6;
    expect(validateRubricReviewState(tooHigh, 'accept')).toContain('GenLayer fit');
  });

  it('rejects non-integer section scores', () => {
    const fractional = validState();
    fractional.sections.engineering.score = 2.5;
    expect(validateRubricReviewState(fractional, 'accept')).toContain('Engineering');

    const stringScore = validState();
    stringScore.sections.engineering.score = /** @type {any} */ ('3');
    expect(validateRubricReviewState(stringScore, 'accept')).toContain('Engineering');
  });

  it('accepts integer score boundaries', () => {
    const state = validState();
    state.sections.genlayer_fit.score = 0;
    state.sections.frontend_ux.score = 5;

    expect(validateRubricReviewState(state, 'accept')).toBeNull();
    expect(buildRubricReviewPayload(state).sections.genlayer_fit.score).toBe(0);
    expect(buildRubricReviewPayload(state).sections.frontend_ux.score).toBe(5);
  });

  it('hydrates existing review data into editable state', () => {
    const state = hydrateRubricState({
      gate_failures: [],
      sections: {
        genlayer_fit: { score: 4, reason: 'Strong fit' }
      },
      extras: ['demo_video'],
      overall_reason: 'Existing proposal'
    });

    expect(state.sections.genlayer_fit.score).toBe(4);
    expect(state.sections.genlayer_fit.reason).toBe('Strong fit');
    expect(state.sections.contract_quality.score).toBe(0);
    expect(state.extras).toEqual(['demo_video']);
    expect(state.overallReason).toBe('Existing proposal');
  });
});
