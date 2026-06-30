import { describe, expect, it } from "vitest";

import {
  buildFilterQuery,
  escapeIlikePattern,
  parseItemFilters,
  tokenizeTitleSearch,
} from "./filters";

describe("tokenizeTitleSearch", () => {
  it("splits on whitespace and trims", () => {
    expect(tokenizeTitleSearch("  rl   smoothing  ")).toEqual([
      "rl",
      "smoothing",
    ]);
  });

  it("returns empty for blank input", () => {
    expect(tokenizeTitleSearch("   ")).toEqual([]);
  });
});

describe("escapeIlikePattern", () => {
  it("escapes ilike metacharacters", () => {
    expect(escapeIlikePattern("100%_done\\")).toBe("100\\%\\_done\\\\");
  });
});

describe("buildFilterQuery", () => {
  it("includes q when set", () => {
    expect(buildFilterQuery({ q: "openai gpt" })).toBe("q=openai%20gpt");
  });

  it("omits empty q", () => {
    expect(buildFilterQuery({ q: "   " })).toBe("");
  });
});

describe("parseItemFilters", () => {
  it("parses title search only", () => {
    expect(parseItemFilters({ q: "molmo motion" })).toEqual({
      q: "molmo motion",
    });
  });

  it("trims q", () => {
    expect(parseItemFilters({ q: "  bert  " })).toEqual({ q: "bert" });
  });
});
