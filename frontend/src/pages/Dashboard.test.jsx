import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { fetchDashboard } from '../api/client';
import Dashboard from './Dashboard';

vi.mock('../api/client', () => import('../test/mocks/client.js'));
vi.mock('../components/Navbar', () => ({
  default: () => <div data-testid="navbar" />,
}));
vi.mock('../components/StatusBadge', () => ({
  default: ({ status }) => <span>{status}</span>,
}));
vi.mock('react-router-dom', () => ({
  Link: ({ children, to }) => React.createElement('a', { href: to }, children),
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
  MemoryRouter: ({ children }) => children,
}));

afterEach(() => vi.clearAllMocks());

const FULL_PAYLOAD = {
  stats: {
    total_posts: 42,
    comments: 17,
    authors: 5,
    active_tags: 8,
  },
  latest_posts: [
    {
      id: 1,
      slug: 'first-post',
      title: 'First Post',
      author: 'alice',
      created_at: '2026-01-15T10:00:00Z',
      status: 'published',
    },
    {
      id: 2,
      slug: 'second-post',
      title: 'Second Post',
      author: 'bob',
      created_at: '2026-01-14T09:00:00Z',
      status: 'draft',
    },
  ],
  most_commented_posts: [
    {
      id: 1,
      slug: 'first-post',
      title: 'First Post',
      author: 'alice',
      created_at: '2026-01-15T10:00:00Z',
      comment_count: 9,
    },
  ],
  most_used_tags: [
    { id: 10, slug: 'django', name: 'django', post_count: 12 },
    { id: 11, slug: 'react', name: 'react', post_count: 7 },
  ],
  top_authors: [
    { id: 1, username: 'alice', post_count: 20 },
    { id: 2, username: 'bob', post_count: 15 },
  ],
};

const EMPTY_PAYLOAD = {
  stats: {
    total_posts: 0,
    comments: 0,
    authors: 0,
    active_tags: 0,
  },
  latest_posts: [],
  most_commented_posts: [],
  most_used_tags: [],
  top_authors: [],
};

describe('Dashboard', () => {
  it('shows loading spinner before data arrives', () => {
    vi.mocked(fetchDashboard).mockReturnValue(new Promise(() => {}));

    render(<Dashboard />);

    expect(document.querySelector('.spinner-border')).not.toBeNull();
  });

  it('renders stat cards after successful fetch', async () => {
    vi.mocked(fetchDashboard).mockResolvedValue(FULL_PAYLOAD);

    render(<Dashboard />);

    await waitFor(() =>
      expect(document.querySelector('.spinner-border')).toBeNull()
    );

    expect(screen.getByText('Total Posts')).toBeInTheDocument();
    expect(screen.getByText('Comments')).toBeInTheDocument();
    expect(screen.getByText('Authors')).toBeInTheDocument();
    expect(screen.getByText('Active Tags')).toBeInTheDocument();
    expect(screen.queryByText('Avg Words')).toBeNull();

    // Stat values rendered as plain numbers
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('17')).toBeInTheDocument();

    // Posts and authors appear in cards (First Post appears in both Latest and Most Commented)
    expect(screen.getAllByText('First Post').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('alice').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('django')).toBeInTheDocument();
  });

  it('renders empty state cards when lists are empty', async () => {
    vi.mocked(fetchDashboard).mockResolvedValue(EMPTY_PAYLOAD);

    render(<Dashboard />);

    await waitFor(() =>
      expect(document.querySelector('.spinner-border')).toBeNull()
    );

    const noPostsMessages = screen.getAllByText('No posts yet.');
    expect(noPostsMessages.length).toBeGreaterThanOrEqual(2);

    expect(screen.getByText('No tags yet.')).toBeInTheDocument();
    expect(screen.getByText('No authors yet.')).toBeInTheDocument();

    // Zero stats render without crashing
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(1);
  });

  it('does not crash when fetchDashboard rejects', async () => {
    vi.mocked(fetchDashboard).mockRejectedValue(new Error('Network error'));

    render(<Dashboard />);

    // Spinner disappears once the error handler fires
    await waitFor(() =>
      expect(document.querySelector('.spinner-border')).toBeNull()
    );

    // Component is still mounted — empty-state text should be visible
    const noPostsMessages = screen.getAllByText('No posts yet.');
    expect(noPostsMessages.length).toBeGreaterThanOrEqual(1);
  });

  it('error state renders empty arrays without crashing', async () => {
    vi.mocked(fetchDashboard).mockRejectedValue(new Error('Server unavailable'));

    render(<Dashboard />);

    await waitFor(() =>
      expect(document.querySelector('.spinner-border')).toBeNull()
    );

    // All four empty-state messages appear, confirming no .length crash occurred
    const noPostsMessages = screen.getAllByText('No posts yet.');
    expect(noPostsMessages.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('No tags yet.')).toBeInTheDocument();
    expect(screen.getByText('No authors yet.')).toBeInTheDocument();

    // Stat cards still render with 0
    const zeroStats = screen.getAllByText('0');
    expect(zeroStats.length).toBeGreaterThanOrEqual(4);
  });
});
