export const PROJECT_REVIEW_FLOWS = new Set(['builder_project']);

export const RUBRIC_SECTIONS = [
  {
    key: 'genlayer_fit',
    label: 'GenLayer fit',
    help: 'Trustless adjudication must matter. No stakes or contested outcome caps this low.'
  },
  {
    key: 'contract_quality',
    label: 'Contract quality',
    help: 'Look for real state, needed non-determinism, and a validator that checks the meaningful result.'
  },
  {
    key: 'engineering',
    label: 'Engineering',
    help: 'Original structure, builds, sensible complexity, real history, and useful docs or tests.'
  },
  {
    key: 'frontend_ux',
    label: 'Frontend / UX',
    help: 'A real app wired to the contract. Contract-only projects can score 0 here.'
  }
];

export const RUBRIC_GATE_FAILURES = [
  {
    key: 'no_real_genlayer_contract',
    label: 'No real GenLayer contract',
    templateLabel: 'Reject: Project Has No Real GenLayer Contract'
  },
  {
    key: 'branding_only',
    label: 'Branding only',
    templateLabel: 'Reject: GenLayer Is Branding Only'
  },
  {
    key: 'repo_does_not_build',
    label: 'Repo does not build or work',
    templateLabel: 'Reject: Project Does Not Build'
  },
  {
    key: 'empty_fork_or_boilerplate',
    label: 'Empty fork or renamed boilerplate',
    templateLabel: 'Reject: Empty Fork or Boilerplate'
  }
];

export const RUBRIC_EXTRAS = [
  { key: 'live_deployment', label: 'Live deployment' },
  { key: 'demo_video', label: 'Demo video' },
  { key: 'public_post', label: 'Public post' }
];

export const RUBRIC_EXTRA_POINTS = 50;

/**
 * @typedef {{ score: number, reason: string }} RubricSectionState
 * @typedef {{
 *   gateFailures?: string[],
 *   sections?: Record<string, RubricSectionState>,
 *   extras?: string[],
 *   overallReason?: string
 * }} RubricState
 * @typedef {{
 *   gate_failures?: string[],
 *   sections?: Record<string, RubricSectionState>,
 *   extras?: string[],
 *   overall_reason?: string
 * }} ApiRubricReview
 * @typedef {{
 *   gate_failures: string[],
 *   sections: Record<string, RubricSectionState>,
 *   extras: string[],
 *   overall_reason: string
 * }} ApiRubricPayload
 */

/** @param {string | null | undefined} reviewFlow */
export function isProjectReviewFlow(reviewFlow) {
  return PROJECT_REVIEW_FLOWS.has(reviewFlow);
}

/** @returns {Record<string, RubricSectionState>} */
export function defaultRubricSections() {
  return Object.fromEntries(
    RUBRIC_SECTIONS.map(section => [
      section.key,
      { score: 0, reason: '' }
    ])
  );
}

/** @param {ApiRubricReview | null | undefined} review */
export function hydrateRubricState(review) {
  const sections = defaultRubricSections();
  if (review?.sections) {
    for (const section of RUBRIC_SECTIONS) {
      const existing = review.sections[section.key];
      if (existing) {
        sections[section.key] = {
          score: Number.isFinite(Number(existing.score)) ? Number(existing.score) : 0,
          reason: existing.reason || ''
        };
      }
    }
  }

  return {
    gateFailures: Array.isArray(review?.gate_failures) ? [...review.gate_failures] : [],
    sections,
    extras: Array.isArray(review?.extras) ? [...review.extras] : [],
    overallReason: review?.overall_reason || ''
  };
}

/** @param {RubricState} state @returns {ApiRubricPayload} */
export function buildRubricReviewPayload(state) {
  const gateFailures = [...(state.gateFailures || [])];
  const extras = [...(state.extras || [])];
  const overallReason = (state.overallReason || '').trim();

  if (gateFailures.length > 0) {
    return {
      gate_failures: gateFailures,
      sections: {},
      extras,
      overall_reason: overallReason
    };
  }

  /** @type {Record<string, RubricSectionState>} */
  const sections = {};
  for (const section of RUBRIC_SECTIONS) {
    const value = state.sections?.[section.key] || { score: 0, reason: '' };
    sections[section.key] = {
      score: value.score,
      reason: (value.reason || '').trim()
    };
  }

  return {
    gate_failures: [],
    sections,
    extras,
    overall_reason: overallReason
  };
}

/** @param {RubricState} state @returns {number} */
export function calculateRubricPoints(state) {
  const sections = state.sections || {};
  const scoreFor = (key) => {
    const score = Number(sections[key]?.score);
    if (!Number.isFinite(score)) return 0;
    return Math.min(5, Math.max(0, Math.trunc(score)));
  };

  const fit = scoreFor('genlayer_fit');
  const contractQuality = scoreFor('contract_quality');
  const engineering = scoreFor('engineering');
  const frontendUx = scoreFor('frontend_ux');
  const quality = (fit / 5) * ((2 * contractQuality + 2 * engineering + frontendUx) / 25);
  const basePoints = Math.round(RUBRIC_EXTRA_POINTS * quality);
  const allowedExtras = new Set(RUBRIC_EXTRAS.map(extra => extra.key));
  const uniqueExtras = new Set(
    (state.extras || []).filter(extraKey => allowedExtras.has(extraKey))
  );
  const extraPoints = uniqueExtras.size * RUBRIC_EXTRA_POINTS;

  return basePoints + extraPoints;
}

/** @param {RubricState} state @param {string} proposedAction */
export function validateRubricReviewState(state, proposedAction) {
  const payload = buildRubricReviewPayload(state);

  if (!payload.overall_reason) {
    return 'Add an overall rubric reason before submitting the proposal.';
  }

  if (payload.gate_failures.length > 0) {
    if (proposedAction !== 'reject') {
      return 'Gate failures must be submitted as reject proposals.';
    }
    return null;
  }

  for (const section of RUBRIC_SECTIONS) {
    const value = payload.sections[section.key];
    if (!Number.isInteger(value.score) || value.score < 0 || value.score > 5) {
      return `${section.label} must have a score from 0 to 5.`;
    }
  }

  return null;
}
