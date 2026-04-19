import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation, useSearchParams } from "react-router-dom";
import { vi } from "vitest";
import { fetchActivity } from "../api/client";
import { mockDesktopViewport, mockMobileViewport } from "../test/viewport";
vi.mock("../api/client", () => import("../test/mocks/client.js"));

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
    mockDesktopViewport();
    authStore.user = { username: "alice", profile: { role: "user" } };
    vi.mocked(fetchActivity).mockResolvedValue({
      latest_post_title: "Hello",
      latest_post_at: "2026-04-01T12:00:00.000Z",
    });
  });

  it("ticker shows news-style lines from activity endpoint", async () => {
    vi.mocked(fetchActivity).mockResolvedValue({
      latest_post_title: "Alpha Post",
      latest_post_at: "2026-04-10T08:00:00.000Z",
      latest_comment_author: "bob",
      latest_comment_at: "2026-04-11T09:00:00.000Z",
      latest_comment_post_title: "Beta Thread",
      latest_user_username: "carol",
      latest_user_joined_at: "2026-04-12T10:00:00.000Z",
    });
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => {
      const posts = screen.getAllByText(/Latest post "Alpha Post" published on/);
      expect(posts.length).toBeGreaterThanOrEqual(1);
    });
    expect(
      screen.getAllByText(/Latest comment by @bob on "Beta Thread" on/).length,
    ).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/New member @carol joined on/).length).toBeGreaterThanOrEqual(1);
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

  it("desktop primary nav exposes Posts, Tags, Users, and Comments with correct hrefs", async () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchActivity)).toHaveBeenCalled());

    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(within(nav).getByRole("link", { name: "Posts" })).toHaveAttribute("href", "/posts");
    expect(within(nav).getByRole("link", { name: "Tags" })).toHaveAttribute("href", "/tags");
    expect(within(nav).getByRole("link", { name: "Users" })).toHaveAttribute("href", "/users");
    expect(within(nav).getByRole("link", { name: "Comments" })).toHaveAttribute("href", "/comments");
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
    await waitFor(() => expect(vi.mocked(fetchActivity)).toHaveBeenCalled());
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
    mockMobileViewport();
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchActivity)).toHaveBeenCalled());
    expect(screen.queryByRole("navigation", { name: "Primary" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Open navigation menu" }),
    ).toBeInTheDocument();
  });

  it("opens mobile drawer with primary links", async () => {
    mockMobileViewport();
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchActivity)).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    expect(await screen.findByRole("link", { name: "Posts" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tags" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close navigation menu" })).toBeInTheDocument();
  });

  it("closes mobile menu on Escape", async () => {
    mockMobileViewport();
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    await waitFor(() => expect(vi.mocked(fetchActivity)).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    expect(await screen.findByRole("link", { name: "Posts" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("link", { name: "Posts" })).toBeNull();
  });
});
