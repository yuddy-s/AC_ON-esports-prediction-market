import { describe, expect, it } from "vitest";
import { fixtureHref, marketHref, parseRoute } from "./router";

describe("parseRoute", () => {
  it("opens the markets page by default", () => {
    expect(parseRoute("")).toEqual({ page: "markets" });
    expect(parseRoute("#/")).toEqual({ page: "markets" });
    expect(parseRoute("#/markets")).toEqual({ page: "markets" });
  });

  it("parses a market page", () => {
    expect(parseRoute("#/markets/3")).toEqual({ page: "market", id: 3n });
    expect(parseRoute(marketHref(12n))).toEqual({ page: "market", id: 12n });
  });

  it("parses the fixture catalog and a fixture detail page", () => {
    expect(parseRoute("#/fixtures")).toEqual({ page: "fixtures" });
    expect(parseRoute("#/fixtures/")).toEqual({ page: "fixtures" });
    expect(parseRoute("#/fixtures/12")).toEqual({ page: "fixture", id: 12 });
  });

  it("round-trips fixture links", () => {
    expect(parseRoute(fixtureHref(7))).toEqual({ page: "fixture", id: 7 });
  });

  it("rejects unknown and malformed paths", () => {
    expect(parseRoute("#/fixtures/abc")).toEqual({ page: "not-found" });
    expect(parseRoute("#/nope")).toEqual({ page: "not-found" });
  });
});
