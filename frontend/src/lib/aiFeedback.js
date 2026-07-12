import { RUBRIC_GATE_FAILURES, RUBRIC_SECTIONS } from './rubricReview.js';

export const AI_REVIEW_DECISIONS = [
  { key: 'accept', label: 'Accept' },
  { key: 'reject', label: 'Reject' },
  { key: 'more_info', label: 'Request info' },
  { key: 'skip', label: 'Skip' }
];

export const AI_REVIEW_CLAIM_TYPES = [
  { key: 'factual_error', label: 'Factual error' },
  { key: 'missed_issue', label: 'Missed issue' },
  { key: 'missed_strength', label: 'Missed strength' },
  { key: 'wrong_weight', label: 'Wrong weight' },
  { key: 'access_error', label: 'Access error' }
];

export const AI_REVIEW_CLAIM_ANCHORS = [
  ...RUBRIC_SECTIONS.map(section => ({ key: section.key, label: section.label })),
  { key: 'synthesis', label: 'Synthesis' }
];

const DECISION_KEYS = new Set(AI_REVIEW_DECISIONS.map(decision => decision.key));
const CLAIM_TYPE_KEYS = new Set(AI_REVIEW_CLAIM_TYPES.map(claimType => claimType.key));
const CLAIM_ANCHOR_KEYS = new Set(AI_REVIEW_CLAIM_ANCHORS.map(anchor => anchor.key));
const CRITERION_KEYS = new Set(RUBRIC_SECTIONS.map(section => section.key));
const GATE_FAILURE_KEYS = new Set(RUBRIC_GATE_FAILURES.map(gate => gate.key));

/**
 * @typedef {{ score?: number, reason?: string }} AIAnalysisSection
 * @typedef {{ id?: string | number | null, action?: string, sections?: Record<string, AIAnalysisSection> }} AIAnalysis
 * @typedef {{ agree?: boolean, range?: [number, number], reason?: string }} SavedCriterion
 * @typedef {{ type?: string, text?: string, evidence_ref?: string, anchor?: string }} SavedClaim
 * @typedef {{
 *   id?: string | number,
 *   verdict?: 'agree' | 'agree_with_corrections' | 'disagree',
 *   review_proposal_id?: string | number | null,
 *   correct_decision?: string | null,
 *   gate_failures?: string[],
 *   criteria?: Record<string, SavedCriterion>,
 *   error_claims?: SavedClaim[]
 * }} ExistingFeedbackRecord
 * @typedef {{ overridden: boolean, min: number | null, max: number | null, reason: string, persisted?: boolean }} FeedbackCriterionState
 * @typedef {{ clientId: string, type: string, text: string, evidenceRef: string, anchor: string }} FeedbackClaimState
 * @typedef {{
 *   reviewProposalId: string | number | null,
 *   aiDecision: string,
 *   aiScores: Record<string, number>,
 *   persistedDecisionOverride: string,
 *   decisionOverride: string,
 *   gateFailures: string[],
 *   criteria: Record<string, FeedbackCriterionState>,
 *   errorClaims: FeedbackClaimState[]
 * }} FeedbackState
 * @typedef {{ agree: true } | { range: [number | null, number | null], reason: string }} FeedbackCriterionPayload
 * @typedef {{ type: string, text: string, evidence_ref?: string, anchor?: string }} FeedbackClaimPayload
 * @typedef {{
 *   verdict: 'agree' | 'agree_with_corrections' | 'disagree',
 *   review_proposal_id?: string | number,
 *   correct_decision?: string,
 *   gate_failures?: string[],
 *   criteria?: Record<string, FeedbackCriterionPayload>,
 *   error_claims?: FeedbackClaimPayload[]
 * }} FeedbackPayload
 */

/** @param {unknown} range @returns {[number | null, number | null]} */
function normalizeRange(range) {
  if (!Array.isArray(range) || range.length !== 2) return [null, null];
  return [Number.isInteger(range[0]) ? range[0] : null, Number.isInteger(range[1]) ? range[1] : null];
}

/** @param {Partial<FeedbackClaimState> & { evidence_ref?: string }} claim */
function isBlankClaim(claim) {
  return !claim?.text?.trim() && !claim?.evidenceRef?.trim() && !claim?.evidence_ref?.trim();
}

/**
 * Build editable feedback state without dropping criteria or claims that are
 * accepted by the API but omitted from the steward-facing AI analysis.
 * @param {AIAnalysis} [aiAnalysis]
 * @param {ExistingFeedbackRecord | null} [existingRecord]
 * @returns {FeedbackState}
 */
export function initFeedbackState(aiAnalysis = {}, existingRecord = null) {
  const aiScores = Object.fromEntries(
    Object.entries(aiAnalysis?.sections || {})
      .filter(([, section]) => Number.isInteger(section?.score))
      .map(([key, section]) => [key, Number(section.score)])
  );
  const sectionKeys = new Set([
    ...Object.keys(aiAnalysis?.sections || {}).filter(key => CRITERION_KEYS.has(key)),
    ...Object.keys(existingRecord?.criteria || {}).filter(key => CRITERION_KEYS.has(key))
  ]);

  /** @type {Record<string, FeedbackCriterionState>} */
  const criteria = {};
  for (const key of sectionKeys) {
    const saved = existingRecord?.criteria?.[key];
    const [min, max] = normalizeRange(saved?.range);
    criteria[key] = {
      overridden: Boolean(saved && !saved.agree),
      min,
      max,
      reason: saved?.reason || '',
      persisted: Boolean(saved && !saved.agree)
    };
  }

  return {
    reviewProposalId: aiAnalysis?.id ?? existingRecord?.review_proposal_id ?? null,
    aiDecision: aiAnalysis?.action || '',
    aiScores,
    persistedDecisionOverride: existingRecord?.correct_decision || '',
    decisionOverride: existingRecord?.correct_decision || '',
    gateFailures: Array.isArray(existingRecord?.gate_failures)
      ? [...existingRecord.gate_failures]
      : [],
    criteria,
    errorClaims: (existingRecord?.error_claims || []).map((claim, index) => ({
      clientId: `saved-${existingRecord?.id ?? 'feedback'}-${index}`,
      type: claim.type || '',
      text: claim.text || '',
      evidenceRef: claim.evidence_ref || '',
      anchor: claim.anchor || ''
    }))
  };
}

/**
 * Build the API payload and derive its verdict from explicit human changes.
 * @param {FeedbackState} state
 * @returns {FeedbackPayload}
 */
export function buildFeedbackPayload(state) {
  const reviewProposalId = state?.reviewProposalId ?? null;
  const claims = (state?.errorClaims || [])
    .filter(claim => !isBlankClaim(claim))
    .map(claim => ({
      type: claim.type || '',
      text: (claim.text || '').trim(),
      ...((claim.evidenceRef || '').trim()
        ? { evidence_ref: claim.evidenceRef.trim() }
        : {}),
      ...(claim.anchor ? { anchor: claim.anchor } : {})
    }));

  /** @type {Record<string, FeedbackCriterionPayload>} */
  const criteria = {};
  let hasScoreOverride = false;
  for (const [key, value] of Object.entries(state?.criteria || {})) {
    const matchesAIScore = (
      Number.isInteger(state.aiScores?.[key]) &&
      value?.min === state.aiScores[key] &&
      value?.max === state.aiScores[key]
    );
    if (value?.overridden && (!matchesAIScore || value.persisted)) {
      hasScoreOverride = true;
      criteria[key] = {
        range: [value.min, value.max],
        reason: (value.reason || '').trim()
      };
    } else {
      criteria[key] = { agree: true };
    }
  }

  const requestedDecisionOverride = state?.decisionOverride || '';
  const decisionOverride = (
    requestedDecisionOverride &&
    (
      requestedDecisionOverride !== state.aiDecision ||
      requestedDecisionOverride === state.persistedDecisionOverride
    )
  )
    ? requestedDecisionOverride
    : '';
  const verdict = decisionOverride
    ? 'disagree'
    : hasScoreOverride || claims.length > 0
      ? 'agree_with_corrections'
      : 'agree';
  /** @type {FeedbackPayload} */
  const payload = {
    verdict,
    ...(reviewProposalId !== null && reviewProposalId !== undefined
      ? { review_proposal_id: reviewProposalId }
      : {})
  };

  // Agreement is deliberately minimal so one click has unambiguous meaning.
  if (verdict === 'agree') return payload;

  if (Object.keys(criteria).length > 0) payload.criteria = criteria;
  if (claims.length > 0) payload.error_claims = claims;
  if (decisionOverride) {
    payload.correct_decision = decisionOverride;
    if (decisionOverride === 'reject' && (state?.gateFailures || []).length > 0) {
      payload.gate_failures = [...state.gateFailures];
    }
  }

  return payload;
}

/**
 * Return a reviewer-facing validation error, or null when the state is valid.
 * @param {FeedbackState} state
 * @returns {string | null}
 */
export function validateFeedbackState(state) {
  const payload = buildFeedbackPayload(state);

  if (payload.correct_decision && !DECISION_KEYS.has(payload.correct_decision)) {
    return 'Choose a valid decision override.';
  }

  const gateFailures = state?.gateFailures || [];
  if (gateFailures.some(key => !GATE_FAILURE_KEYS.has(key))) {
    return 'Choose only valid gate failures.';
  }
  if (gateFailures.length > 0 && payload.correct_decision !== 'reject') {
    return 'Gate failures can only be added when overriding the decision to reject.';
  }

  for (const [key, value] of Object.entries(state?.criteria || {})) {
    if (!CRITERION_KEYS.has(key)) return 'Choose only valid review criteria.';
    if (!value?.overridden) continue;

    const min = value.min;
    const max = value.max;
    const label = RUBRIC_SECTIONS.find(section => section.key === key)?.label || 'Criterion';
    if (
      typeof min !== 'number' ||
      typeof max !== 'number' ||
      !Number.isInteger(min) ||
      !Number.isInteger(max) ||
      min < 0 ||
      max > 5 ||
      min > max
    ) {
      return `${label} needs a score range from 0 to 5.`;
    }
    if (
      !value.persisted &&
      Number.isInteger(state.aiScores?.[key]) &&
      min === state.aiScores[key] &&
      max === state.aiScores[key]
    ) {
      return `${label} matches the AI score. Choose Agree or widen the range.`;
    }
    if ((value.reason || '').length > 500) {
      return 'Score correction reasons must be 500 characters or fewer.';
    }
  }

  for (const claim of state.errorClaims || []) {
    if (!CLAIM_TYPE_KEYS.has(claim.type)) return 'Choose a flaw type for every claim.';
    if (!claim.text?.trim()) return 'Describe every flagged flaw in one sentence.';
    if (claim.text.trim().length > 500) return 'Flagged flaws must be 500 characters or fewer.';
    if ((claim.evidenceRef || '').trim().length > 300) {
      return 'Evidence references must be 300 characters or fewer.';
    }
    if (claim.anchor && !CLAIM_ANCHOR_KEYS.has(claim.anchor)) {
      return 'Choose a valid reasoning section for every claim.';
    }
  }

  return null;
}
