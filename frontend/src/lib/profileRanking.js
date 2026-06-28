export const COMMUNITY_RANKING_MIN_POINTS = 2500;

/**
 * @typedef {object} RankingStats
 * @property {number | string | null | undefined} [submittableContributionCount]
 * @property {number | string | null | undefined} [acceptedSubmittableContributions]
 * @property {number | string | null | undefined} [totalPoints]
 */

/**
 * @typedef {object} RankingParticipant
 * @property {unknown} [validator]
 */

/**
 * @param {unknown} value
 */
function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

/**
 * @param {RankingStats | null | undefined} [stats]
 */
export function getAcceptedSubmittableCount(stats = {}) {
  const safeStats = stats || {};
  return toNumber(
    safeStats.submittableContributionCount ??
      safeStats.acceptedSubmittableContributions ??
      0,
  );
}

/**
 * @param {string | null | undefined} tab
 * @param {{
 *   participant?: RankingParticipant | null,
 *   builderStats?: RankingStats | null,
 *   communityStats?: RankingStats | null,
 * }} [options]
 */
export function getRankingRequirement(tab, {
  participant = null,
  builderStats = {},
  communityStats = {},
} = {}) {
  if (tab === "Builders") {
    const acceptedCount = getAcceptedSubmittableCount(builderStats);
    return {
      met: acceptedCount >= 1,
      current: acceptedCount,
      target: 1,
    };
  }

  if (tab === "Community") {
    const points = toNumber(communityStats?.totalPoints);
    return {
      met: points >= COMMUNITY_RANKING_MIN_POINTS,
      current: points,
      target: COMMUNITY_RANKING_MIN_POINTS,
    };
  }

  if (tab === "Validators") {
    return {
      met: Boolean(participant?.validator),
      current: participant?.validator ? 1 : 0,
      target: 1,
    };
  }

  return {
    met: true,
    current: 0,
    target: 0,
  };
}
