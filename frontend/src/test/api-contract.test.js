/**
 * Verify that the test mock module exports match the real API client exports.
 * This catches drift when endpoints are added/renamed during migration.
 *
 * We compare keys by reading the source file rather than importing the real
 * client, because importing it creates an Axios instance with interceptors
 * that causes side-effects in the jsdom test environment.
 */
import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { describe, expect, it } from "vitest";
import * as mockClient from "./mocks/client";

const thisDir = dirname(fileURLToPath(import.meta.url));
const clientSource = readFileSync(
  resolve(thisDir, "../api/client.js"),
  "utf-8",
);

const EXPORT_RE = /export\s+(?:const|function|class|let|var)\s+(\w+)/g;
function extractNamedExports(source) {
  const names = new Set();
  let m;
  while ((m = EXPORT_RE.exec(source)) !== null) {
    names.add(m[1]);
  }
  return names;
}

const realExports = extractNamedExports(clientSource);
const IGNORE = new Set(["default"]);

describe("API client mock contract", () => {
  it("mock exports every named export from the real client", () => {
    const mockExports = new Set(Object.keys(mockClient));
    const missing = [...realExports].filter(
      (k) => !IGNORE.has(k) && !mockExports.has(k),
    );
    expect(missing).toEqual([]);
  });

  it("mock does not export stale functions absent from the real client", () => {
    const mockExports = Object.keys(mockClient).filter((k) => !IGNORE.has(k));
    const stale = mockExports.filter((k) => !realExports.has(k));
    expect(stale).toEqual([]);
  });

  it("all mock named exports are vi.fn() stubs or string constants", () => {
    const mockExports = Object.keys(mockClient).filter((k) => !IGNORE.has(k));
    for (const name of mockExports) {
      const val = mockClient[name];
      const ok = typeof val === "function" || typeof val === "string";
      expect(ok, `${name} should be a function or string, got ${typeof val}`).toBe(true);
    }
  });
});
