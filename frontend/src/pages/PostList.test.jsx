import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";
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

function CreateParamEcho() {
  const [searchParams] = useSearchParams();
  return <span data-testid="create-param">{searchParams.get("create") ?? "none"}</span>;
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

  it("opens the create composer and clears the create param from the URL when requested via search param", async () => {
    render(
      <MemoryRouter initialEntries={["/posts?create=1"]}>
        <Routes>
          <Route
            path="/posts"
            element={
              <>
                <PostList />
                <CreateParamEcho />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByPlaceholderText(/compelling title/i)).toBeInTheDocument(),
    );
    await waitFor(() => expect(screen.getByTestId("create-param")).toHaveTextContent("none"));
  });

  it("closes the composer when the Cancel button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/posts?create=1"]}>
        <Routes>
          <Route path="/posts" element={<PostList />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByPlaceholderText(/compelling title/i)).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByPlaceholderText(/compelling title/i)).toBeNull();
  });

  it("opens the composer via the inline toggle button without a URL param", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/posts"]}>
        <Routes>
          <Route path="/posts" element={<PostList />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.queryByText("Hello")).toBeInTheDocument());
    expect(screen.queryByPlaceholderText(/compelling title/i)).toBeNull();

    await user.click(screen.getAllByRole("button", { name: "+ New Post" })[0]);

    expect(screen.getByPlaceholderText(/compelling title/i)).toBeInTheDocument();
  });
});
