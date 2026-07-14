import { describe, expect, it } from "vitest";
import { parseSearch } from "../lib/searchParser.js";
import { searchToParams } from "../lib/searchToParams.js";

const stewardOptions = {
  currentUserId: 7,
  stewardsList: [
    { user_id: 11, name: "Joaquin Bressan", address: "0xjoaquin" },
    { user_id: 12, name: "Pavel Kolosov", address: "0xpavel" },
  ],
};

function paramsFor(query, options = {}) {
  return searchToParams(parseSearch(query), options);
}

describe("steward search negation", () => {
  it("maps URL searches without dropping colon-like tokens", () => {
    expect(paramsFor("include:https://x.com/user/status/123?s=20")).toEqual({
      include_content: "https://x.com/user/status/123?s=20",
    });
    expect(paramsFor("include: https://x.com/user/status/123?s=20")).toEqual({
      include_content: "https://x.com/user/status/123?s=20",
    });
    expect(paramsFor("https://x.com/user/status/123?s=20")).toEqual({
      search: "https://x.com/user/status/123?s=20",
    });
  });

  it("maps reviewed and points sort aliases", () => {
    expect(paramsFor("sort:-reviewed")).toEqual({ ordering: "-reviewed_at" });
    expect(paramsFor("sort:-points")).toEqual({
      ordering: "-converted_contribution__frozen_global_points",
    });
  });

  it("does not merge a dangling tag with the next real filter", () => {
    expect(paramsFor("include: sort:-reviewed")).toEqual({
      ordering: "-reviewed_at",
    });
  });

  it("normalizes negated presence filters to absence filters", () => {
    const { filters } = parseSearch("-has:proposal -has:url -has:appeal");

    expect(filters.has).toEqual([]);
    expect(filters.no).toEqual(["proposal", "url", "appeal"]);
    expect(paramsFor("-has:proposal")).toEqual({ has_proposal: false });
    expect(paramsFor("-has:url")).toEqual({ only_empty_evidence: true });
    expect(paramsFor("-has:appeal")).toEqual({ has_appeal: false });
  });

  it("normalizes negated flag filters to not filters", () => {
    const { filters } = parseSearch("-is:interesting -is:ai-reviewed");

    expect(filters.is).toEqual([]);
    expect(filters.not).toEqual(["interesting", "ai-reviewed"]);
    expect(paramsFor("-is:interesting")).toEqual({ is_interesting: false });
    expect(paramsFor("-is:ai-reviewed")).toEqual({ has_ai_analysis: false });
  });

  it("maps durable more-info resubmission aliases and negation", () => {
    expect(paramsFor("is:more-info-resubmitted")).toEqual({
      is_more_info_resubmitted: true,
    });
    expect(paramsFor("is:resubmitted")).toEqual({
      is_more_info_resubmitted: true,
    });
    expect(paramsFor("not:more-info-resubmitted")).toEqual({
      is_more_info_resubmitted: false,
    });
    expect(paramsFor("-is:more-info-resubmitted")).toEqual({
      is_more_info_resubmitted: false,
    });
  });

  it("maps recorded more-info request presence and absence", () => {
    expect(paramsFor("status:pending has:more-info-request")).toEqual({
      state: "pending",
      has_more_info_request: true,
    });
    expect(paramsFor("no:more-info-request")).toEqual({
      has_more_info_request: false,
    });
    expect(paramsFor("-has:more-info-request")).toEqual({
      has_more_info_request: false,
    });
  });

  it("supports NOT before multi-value filters", () => {
    expect(paramsFor("NOT has:proposal")).toEqual({ has_proposal: false });
    expect(paramsFor("NOT is:interesting")).toEqual({ is_interesting: false });
  });

  it("resolves 'me' to the current user and never to a steward name match", () => {
    const withNameContainingMe = {
      currentUserId: 7,
      stewardsList: [{ user_id: 9, name: "James Medina", address: "0xjames" }],
    };
    expect(paramsFor("proposed-by:me", withNameContainingMe)).toEqual({ proposed_by: 7 });
    expect(paramsFor("assigned:me", withNameContainingMe)).toEqual({ assigned_to: 7 });
    expect(paramsFor("reviewed:me", withNameContainingMe)).toEqual({ reviewed_by: 7 });

    // Profile not loaded yet: "me" must resolve to nothing, not to
    // whichever steward's name happens to contain the substring "me".
    const userNotLoaded = { ...withNameContainingMe, currentUserId: undefined };
    expect(paramsFor("proposed-by:me proposal-status:questioned", userNotLoaded)).toEqual({
      proposal_review_status: "questioned",
    });
  });

  it("inverts explicit negative aliases when prefixed with a dash", () => {
    expect(paramsFor("-no:proposal")).toEqual({ has_proposal: true });
    expect(paramsFor("-not:interesting")).toEqual({ is_interesting: true });
  });

  it("normalizes negated include and exclude text filters", () => {
    const { filters } = parseSearch("-include:spam -exclude:genlayer");

    expect(filters.include).toEqual(["genlayer"]);
    expect(filters.exclude).toEqual(["spam"]);
    expect(paramsFor("-include:spam -exclude:genlayer")).toEqual({
      exclude_content: "spam",
      include_content: "genlayer",
    });
  });

  it("maps proposal creator filters", () => {
    expect(paramsFor("proposed-by:ai")).toEqual({ proposed_by: "ai" });
    expect(paramsFor("-proposed-by:ai")).toEqual({ exclude_proposed_by: "ai" });
    expect(paramsFor("proposed-by:none")).toEqual({ proposed_by: "none" });
  });

  it("maps proposal status filters", () => {
    expect(paramsFor("proposal-status:questioned")).toEqual({
      proposal_review_status: "questioned",
    });
    expect(paramsFor("proposal-status:pending")).toEqual({
      proposal_review_status: "pending_review",
    });
  });

  it("supports compound assigned exclusions with repeated or comma values", () => {
    expect(paramsFor("-assigned:unassigned -assigned:Joaquin", stewardOptions)).toEqual({
      exclude_assigned_to: "unassigned,11",
    });
    expect(paramsFor("-assigned:unassigned,Joaquin", stewardOptions)).toEqual({
      exclude_assigned_to: "unassigned,11",
    });
  });

  it("normalizes spaced and hyphenated steward names", () => {
    expect(paramsFor("assigned:Pavel Kolosov", stewardOptions)).toEqual({
      assigned_to: 12,
    });
    expect(paramsFor("assigned:Pavel kolosov", stewardOptions)).toEqual({
      assigned_to: 12,
    });
    expect(paramsFor("assigned: Pavel Kolosov", stewardOptions)).toEqual({
      assigned_to: 12,
    });
    expect(paramsFor("assigned:pavel-kolosov", stewardOptions)).toEqual({
      assigned_to: 12,
    });
    expect(paramsFor("proposed-by:pavel-kolosov", stewardOptions)).toEqual({
      proposed_by: 12,
    });
  });

  it("does not swallow free text after slug or simple-name filters", () => {
    expect(paramsFor("type:blog-post github repo", {
      contributionTypes: [{ id: 21, name: "Blog Post", slug: "blog-post" }],
    })).toEqual({
      contribution_type: 21,
      search: "github repo",
    });
    expect(paramsFor("from:alice github repo")).toEqual({
      username_search: "alice",
      search: "github repo",
    });
    expect(paramsFor("assigned:Pavel kolosov github repo", stewardOptions)).toEqual({
      assigned_to: 12,
      search: "github repo",
    });
    expect(paramsFor("assigned:Pavel,Joaquin github repo", stewardOptions)).toEqual({
      assigned_to: "12,11",
      search: "github repo",
    });
  });

  it("preserves separators in submitter searches", () => {
    expect(paramsFor("from:alice_xp")).toEqual({
      username_search: "alice_xp",
    });
    expect(paramsFor("-from:alice-xp")).toEqual({
      exclude_username: "alice-xp",
    });
  });

  it("keeps exact assignment aliases from consuming following free text", () => {
    expect(paramsFor("assigned:me github repo", stewardOptions)).toEqual({
      assigned_to: 7,
      search: "github repo",
    });
  });

  it("matches numeric steward ids exactly before fuzzy text fields", () => {
    const options = {
      stewardsList: [
        { user_id: 112, name: "First Steward", address: "0xfirst" },
        { user_id: 12, name: "Second Steward", address: "0xsecond" },
      ],
    };

    expect(paramsFor("assigned:12", options)).toEqual({ assigned_to: 12 });
    expect(paramsFor("reviewed:12", options)).toEqual({ reviewed_by: 12 });
    expect(paramsFor("proposed-by:12", options)).toEqual({ proposed_by: 12 });
  });
});
