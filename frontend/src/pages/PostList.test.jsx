import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { vi } from "vitest";
import { fetchPosts, fetchTags } from "../api/client";

vi.mock("../api/client", () => import("../test/mocks/client.js"));
vi.mock("../components/StatusBadge", () => ({
  default: ({ status }) => <span>{status}</span>,
}));

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { username: "alice", profile: { role: "user" } },
  }),
}));

import PostList from "./PostList";

const SAMPLE_POST = {
  id: 1,
  slug: "hello",
  title: "Hello",
  author: "alice",
  created_at: "2026-01-15T10:00:00Z",
  status: "published",
  tags: [],
  comment_count: 0,
};

function RouterStateEmpty() {
  const { state } = useLocation();
  const empty = !state || Object.keys(state).length === 0;
  return <span data-testid="router-state-empty">{empty ? "yes" : "no"}</span>;
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("PostList", () => {
  beforeEach(() => {
    vi.mocked(fetchPosts).mockResolvedValue({
      results: [SAMPLE_POST],
      count: 1,
      page: 1,
      total_pages: 1,
    });
    vi.mocked(fetchTags).mockResolvedValue({
      results: [{ id: 10, slug: "django", name: "django" }],
      total_pages: 1,
    });
  });

  it("keeps the create composer closed when there is no openCreate navigation state", async () => {
    render(
      <MemoryRouter initialEntries={["/posts"]}>
        <Routes>
          <Route path="/posts" element={<PostList />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.queryByText("Hello")).toBeInTheDocument());
    expect(screen.queryByPlaceholderText(/compelling title/i)).toBeNull();
  });

  it("opens the create composer and clears openCreate from history when requested via location state", async () => {
    render(
      <MemoryRouter
        initialEntries={[{ pathname: "/posts", state: { openCreate: true } }]}
      >
        <Routes>
          <Route
            path="/posts"
            element={
              <>
                <PostList />
                <RouterStateEmpty />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByPlaceholderText(/compelling title/i)).toBeInTheDocument(),
    );
    await waitFor(() => expect(screen.getByTestId("router-state-empty")).toHaveTextContent("yes"));
  });
});
