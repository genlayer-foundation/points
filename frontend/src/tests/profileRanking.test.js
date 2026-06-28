import { describe, expect, it } from "vitest";
import { shouldShowRankingPreviewCta } from "../lib/profileRanking.js";

describe("profile ranking CTA", () => {
  it("does not show the ranking CTA for users with a real rank", () => {
    expect(
      shouldShowRankingPreviewCta({
        isOwnProfile: true,
        tab: "Community",
        statsLoaded: true,
        rankStatus: "ranked",
      }),
    ).toBe(false);

    expect(
      shouldShowRankingPreviewCta({
        isOwnProfile: true,
        tab: "Community",
        rankStatus: "unranked",
      }),
    ).toBe(true);
  });

  it("only shows the ranking CTA for own builder and community profiles", () => {
    expect(
      shouldShowRankingPreviewCta({
        isOwnProfile: false,
        tab: "Community",
        rankStatus: "unranked",
      }),
    ).toBe(false);

    expect(
      shouldShowRankingPreviewCta({
        isOwnProfile: true,
        tab: "Validators",
        rankStatus: "unranked",
      }),
    ).toBe(false);
  });
});
