import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi, describe, it, beforeEach, afterEach, expect } from "vitest";
import App from "./App";
import { mockMobileViewport, mockDesktopViewport } from "./test/viewport";

vi.mock("./api/client", () => import("./test/mocks/client.js"));

import {
  fetchCurrentUser,
  fetchDashboard,
  fetchPosts,
  fetchTags,
} from "./api/client";

const DASHBOARD_PAYLOAD = {
  stats: {
    total_posts: 2,
    comments: 1,
    authors: 1,
    active_tags: 1,
    new_posts_7d: 1,
  },
  latest_posts: [
    {
      id: 1,
      slug: "alpha",
      title: "Alpha",
      author: "alice",
      created_at: "2026-01-01T00:00:00Z",
      status: "published",
    },
  ],
  most_commented_posts: [],
  most_liked_posts: [],
  most_used_tags: [{ id: 1, slug: "django", name: "django", post_count: 2 }],
  top_authors: [{ id: 1, username: "alice", post_count: 2 }],
  activity: {
    latest_post_title: "Alpha",
    latest_post_at: "2026-01-01T12:00:00Z",
  },
};

function renderAppAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App mobile layout (narrow viewport)", () => {
  beforeEach(() => {
    mockMobileViewport();
    vi.mocked(fetchCurrentUser).mockResolvedValue({
      username: "alice",
      profile: { role: "user" },
    });
    vi.mocked(fetchDashboard).mockResolvedValue(DASHBOARD_PAYLOAD);
    vi.mocked(fetchPosts).mockResolvedValue({
      results: [
        {
          id: 1,
          slug: "hello",
          title: "Hello",
          author: "alice",
          created_at: "2026-01-15T10:00:00Z",
          status: "published",
          tags: [],
          comment_count: 0,
        },
      ],
      count: 1,
      page: 1,
      total_pages: 1,
    });
    vi.mocked(fetchTags).mockResolvedValue({
      results: [{ id: 10, slug: "django", name: "django", post_count: 3 }],
      count: 1,
      page: 1,
      total_pages: 1,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    mockDesktopViewport();
  });

  it("dashboard: hamburger replaces desktop primary nav; stats and panels render", async () => {
    renderAppAt("/dashboard");

    await waitFor(() =>
      expect(vi.mocked(fetchCurrentUser)).toHaveBeenCalled(),
    );

    expect(
      screen.getByRole("button", { name: "Open navigation menu" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Primary" })).toBeNull();

    await waitFor(() => expect(screen.getByText("Posts")).toBeInTheDocument());
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(document.querySelector(".nb-dashboard-stats")).not.toBeNull();
    expect(document.querySelector(".nb-dashboard-posts-row")).not.toBeNull();
  });

  it("mobile drawer navigates to Tags and tag grid renders", async () => {
    const user = userEvent.setup();
    renderAppAt("/dashboard");

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Open navigation menu" }),
      ).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    await user.click(await screen.findByRole("link", { name: "Tags" }));

    await waitFor(() =>
      expect(screen.getByText("Tags Available")).toBeInTheDocument(),
    );
    const grid = document.querySelector(".nb-tag-grid");
    expect(grid).not.toBeNull();
    expect(within(grid).getByRole("link", { name: /django/i })).toBeInTheDocument();
  });

  it("post list: list layout and post title visible on narrow width", async () => {
    renderAppAt("/posts");

    await waitFor(() => expect(screen.getByText("Hello")).toBeInTheDocument());
    expect(document.querySelector(".app-shell")).not.toBeNull();
    expect(
      screen.getByRole("button", { name: "Open navigation menu" }),
    ).toBeInTheDocument();
  });

  it("login page: auth form renders within app shell", async () => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(null);
    renderAppAt("/login");

    await waitFor(() => expect(screen.getByLabelText(/email/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(document.querySelector(".nb-auth-header")?.textContent).toMatch(/login/i);
    expect(
      screen.getByRole("button", { name: "Open navigation menu" }),
    ).toBeInTheDocument();
  });

  it("register page: auth form renders within app shell", async () => {
    vi.mocked(fetchCurrentUser).mockResolvedValue(null);
    renderAppAt("/register");

    await waitFor(() => expect(screen.getByLabelText(/email/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(document.querySelector(".nb-auth-header")?.textContent).toMatch(/create account/i);
  });
});
