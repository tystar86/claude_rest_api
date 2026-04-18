import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { vi } from "vitest";
import { fetchDashboard } from "../api/client";
import { NARROW_HEADER_QUERY } from "../hooks/useNarrowHeader";

vi.mock("../api/client", () => import("../test/mocks/client.js"));

function mockMatchMediaHeader(narrow) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: query === NARROW_HEADER_QUERY ? narrow : false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }));
}

const authStore = { user: null, logout: vi.fn() };

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ user: authStore.user, logout: authStore.logout }),
}));

import Navbar from "./Navbar";

function LocationEcho() {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const open = searchParams.get("create") === "1";
  return (
    <div>
      <div data-testid="echo-path">{pathname}</div>
      <div data-testid="echo-open-create">{open ? "yes" : "no"}</div>
    </div>
  );
}

afterEach(() => {
  vi.clearAllMocks();
  authStore.user = null;
});

describe("Navbar", () => {
  beforeEach(() => {
    mockMatchMediaHeader(false);
    authStore.user = { username: "alice", profile: { role: "user" } };
    vi.mocked(fetchDashboard).mockResolvedValue({
      stats: {
        total_posts: 1,
        authors: 1,
        active_tags: 1,
        comments: 0,
        average_depth_words: 100,
      },
    });
  });

  it("shows + New Post when the user is signed in", async () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "+ New Post" })).toBeInTheDocument(),
    );
  });

  it("the + New Post link href includes ?create=1", async () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    const link = await screen.findByRole("link", { name: "+ New Post" });
    expect(link).toHaveAttribute("href", "/posts?create=1");
  });

  it("does not show + New Post when logged out", async () => {
    authStore.user = null;
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link", { name: "+ New Post" })).toBeNull();
    await waitFor(() => expect(vi.mocked(fetchDashboard)).toHaveBeenCalled());
  });

  it("navigates to /posts with openCreate when + New Post is used from another page", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/tags"]}>
        <Routes>
          <Route
            path="/tags"
            element={
              <>
                <Navbar />
                <div>tags page</div>
              </>
            }
          />
          <Route
            path="/posts"
            element={
              <>
                <Navbar />
                <LocationEcho />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("link", { name: "+ New Post" }));

    await waitFor(() => expect(screen.getByTestId("echo-path")).toHaveTextContent("/posts"));
    expect(screen.getByTestId("echo-open-create")).toHaveTextContent("yes");
  });

  it("applies openCreate when + New Post is clicked while already on /posts", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/posts"]}>
        <Routes>
          <Route
            path="/posts"
            element={
              <>
                <Navbar />
                <LocationEcho />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("echo-open-create")).toHaveTextContent("no");

    await user.click(screen.getByRole("link", { name: "+ New Post" }));

    await waitFor(() => expect(screen.getByTestId("echo-open-create")).toHaveTextContent("yes"));
  });

  it("narrow header shows menu control instead of inline Posts link", async () => {
    mockMatchMediaHeader(true);
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchDashboard)).toHaveBeenCalled());
    expect(screen.queryByRole("navigation", { name: "Primary" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Open navigation menu" }),
    ).toBeInTheDocument();
  });

  it("opens mobile drawer with primary links", async () => {
    mockMatchMediaHeader(true);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchDashboard)).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    expect(screen.getByRole("link", { name: "Posts" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tags" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close navigation menu" })).toBeInTheDocument();
  });

  it("closes mobile menu on Escape", async () => {
    mockMatchMediaHeader(true);
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchDashboard)).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    expect(screen.getByRole("link", { name: "Posts" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("link", { name: "Posts" })).toBeNull();
  });
});
