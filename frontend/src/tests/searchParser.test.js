import { describe, expect, it } from "vitest";
import { parseSearch } from "../lib/searchParser.js";
import { searchToParams } from "../lib/searchToParams.js";

function paramsFor(query) {
  return searchToParams(parseSearch(query));
}

describe("steward search negation", () => {
  it("normalizes negated presence filters to absence filters", () => {
    const { filters } = parseSearch("-has:proposal -has:url -has:appeal");

    expect(filters.has).toEqual([]);
    expect(filters.no).toEqual(["proposal", "url", "appeal"]);
    expect(paramsFor("-has:proposal")).toEqual({ has_proposal: false });
    expect(paramsFor("-has:url")).toEqual({ only_empty_evidence: true });
    expect(paramsFor("-has:appeal")).toEqual({ has_appeal: false });
  });

  it("normalizes negated flag filters to not filters", () => {
    const { filters } = parseSearch("-is:interesting -is:resubmitted");

    expect(filters.is).toEqual([]);
    expect(filters.not).toEqual(["interesting", "resubmitted"]);
    expect(paramsFor("-is:interesting")).toEqual({ is_interesting: false });
    expect(paramsFor("-is:resubmitted")).toEqual({ resubmitted_more_info: false });
  });

  it("supports NOT before multi-value filters", () => {
    expect(paramsFor("NOT has:proposal")).toEqual({ has_proposal: false });
    expect(paramsFor("NOT is:interesting")).toEqual({ is_interesting: false });
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
});
