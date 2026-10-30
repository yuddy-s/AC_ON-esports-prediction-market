import { useEffect, useState } from "react";

// Minimal hash router (#/fixtures, #/fixtures/3). Hash URLs work on any static
// host, including Vercel, without rewrite rules.
export type Route =
  | { page: "markets" }
  | { page: "fixtures" }
  | { page: "fixture"; id: number }
  | { page: "not-found" };

export function parseRoute(hash: string): Route {
  const path = hash.replace(/^#/, "").replace(/\/+$/, "") || "/";
  if (path === "/" || path === "/markets") return { page: "markets" };
  if (path === "/fixtures") return { page: "fixtures" };
  const fixture = /^\/fixtures\/(\d+)$/.exec(path);
  if (fixture) return { page: "fixture", id: Number(fixture[1]) };
  return { page: "not-found" };
}

export function fixtureHref(id: number): string {
  return `#/fixtures/${id}`;
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
