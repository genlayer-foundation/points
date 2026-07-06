import { describe, expect, it } from "vitest";
import { getTopRole } from "../lib/profileRole.js";

describe("getTopRole", () => {
  it("uses contribution count instead of summed points", () => {
    const result = getTopRole(
      { builder: true, creator: true },
      {
        builderStats: { totalContributions: 3, totalPoints: 30 },
        communityStats: { totalContributions: 8, totalPoints: 10 },
      },
    );

    expect(result).toMatchObject({
      label: "Community",
      category: "community",
      badges: [{ category: "community" }],
    });
  });

  it("returns Balanced when active roles tie on contributions", () => {
    const result = getTopRole(
      { builder: true, creator: true },
      {
        builderStats: { totalContributions: 4, totalPoints: 40 },
        communityStats: { totalContributions: 4, totalPoints: 20 },
      },
    );

    expect(result).toMatchObject({
      label: "Balanced",
      category: "genlayer",
      badges: [{ category: "builder" }, { category: "community" }],
    });
  });

  it("falls back to the only active role when there is no activity yet", () => {
    const result = getTopRole(
      { builder: true },
      {
        builderStats: { totalContributions: 0, totalPoints: 0 },
      },
    );

    expect(result).toMatchObject({
      label: "Builder",
      category: "builder",
      badges: [{ category: "builder" }],
    });
  });

  it("labels validator waitlist users distinctly", () => {
    const result = getTopRole(
      { has_validator_waitlist: true },
      {
        validatorStats: { totalContributions: 0, totalPoints: 5 },
      },
    );

    expect(result).toMatchObject({
      label: "Validator Waitlist",
      category: "validator",
      badges: [{ category: "validator" }],
    });
  });

  it("labels graduated validators as validators even when waitlist history remains", () => {
    const result = getTopRole(
      { validator: {}, has_validator_waitlist: true },
      {
        validatorStats: { totalContributions: 0, totalPoints: 0 },
      },
    );

    expect(result).toMatchObject({
      label: "Validator",
      category: "validator",
      badges: [{ category: "validator" }],
    });
  });
});
