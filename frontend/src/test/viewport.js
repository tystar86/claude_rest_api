import { vi } from "vitest";

/** Same breakpoint as `useNarrowHeader` / `theme.css` (.nb-header max-width: 900px). */
function isNarrowHeaderQuery(query) {
  const q = String(query).trim().toLowerCase().replace(/\s+/g, " ");
  return q.includes("max-width") && q.includes("900px");
}

function matchMediaImpl(narrow) {
  return (query) => ({
    matches: isNarrowHeaderQuery(query) ? narrow : false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  });
}

/** Phone-sized: narrow header / hamburger layout. */
export function mockMobileViewport() {
  window.matchMedia = vi.fn().mockImplementation(matchMediaImpl(true));
  Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 390 });
  Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 844 });
}

/** Desktop-sized: inline primary nav. */
export function mockDesktopViewport() {
  window.matchMedia = vi.fn().mockImplementation(matchMediaImpl(false));
  Object.defineProperty(window, "innerWidth", { writable: true, configurable: true, value: 1280 });
  Object.defineProperty(window, "innerHeight", { writable: true, configurable: true, value: 720 });
}
