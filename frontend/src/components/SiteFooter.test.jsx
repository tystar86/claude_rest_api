import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SiteFooter from "./SiteFooter";

describe("SiteFooter", () => {
  it("shows attribution and site creation year", () => {
    render(<SiteFooter />);
    expect(screen.getByRole("contentinfo", { name: /site footer/i })).toHaveTextContent(
      "Created by tystar · 2026",
    );
  });
});
