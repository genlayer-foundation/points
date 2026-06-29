export const COMMUNITY_RANKING_MIN_POINTS = 2500;
export const CONTRIBUTION_RANKING_TABS = new Set(["Builders", "Community"]);

/**
 * @param {{
 *   isOwnProfile?: boolean,
 *   tab?: string | null,
 *   rankStatus?: string | null,
 * }} options
 */
export function shouldShowRankingPreviewCta({
  isOwnProfile = false,
  tab = null,
  rankStatus = null,
} = {}) {
  return Boolean(
    isOwnProfile &&
      CONTRIBUTION_RANKING_TABS.has(tab || "") &&
      rankStatus === "unranked",
  );
}
