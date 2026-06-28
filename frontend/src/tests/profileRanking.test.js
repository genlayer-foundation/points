import { describe, expect, it } from "vitest";
import {
  COMMUNITY_RANKING_MIN_POINTS,
  getRankingRequirement,
} from "../lib/profileRanking.js";

describe("profile ranking requirements", () => {
  it("requires builders to have an accepted submittable contribution", () => {
    expect(
      getRankingRequirement("Builders", {
        builderStats: {},
      }).met,
    ).toBe(false);

    expect(
      getRankingRequirement("Builders", {
        builderStats: { submittableContributionCount: 1 },
      }).met,
    ).toBe(true);
  });

  it("requires community users to reach 2,500 community points", () => {
    expect(
      getRankingRequirement("Community", {
        communityStats: { totalPoints: COMMUNITY_RANKING_MIN_POINTS - 1 },
      }).met,
    ).toBe(false);

    expect(
      getRankingRequirement("Community", {
        communityStats: { totalPoints: COMMUNITY_RANKING_MIN_POINTS },
      }).met,
    ).toBe(true);
  });

  it("requires validator ranking users to be validators", () => {
    expect(
      getRankingRequirement("Validators", {
        participant: {},
      }).met,
    ).toBe(false);

    expect(
      getRankingRequirement("Validators", {
        participant: { validator: {} },
      }).met,
    ).toBe(true);
  });
});
