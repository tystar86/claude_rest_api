import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { GOOGLE_LOGIN_URL, registerUser } from '../api/client';

const mockNavigate = vi.fn();
const mockSetUser = vi.fn();

vi.mock('../api/client', () => import('../test/mocks/client.js'));
vi.mock('react-router-dom', () => ({
  Link: ({ children, to }) => React.createElement('a', { href: to }, children),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ setUser: mockSetUser }),
}));
vi.mock('../components/Navbar', () => ({
  default: () => React.createElement('div', { 'data-testid': 'navbar' }),
}));

import Register from './Register';

afterEach(() => {
  vi.clearAllMocks();
  mockNavigate.mockReset();
  mockSetUser.mockReset();
});

describe('Register page', () => {
  // ── Rendering ──────────────────────────────────────────────────────────

  it('renders email, username, and password fields', () => {
    render(<Register />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders a submit button', () => {
    render(<Register />);
    expect(screen.getByRole('button', { name: /register/i })).toBeInTheDocument();
  });

  it('renders a "Continue with Google" link', () => {
    render(<Register />);
    expect(screen.getByRole('link', { name: /continue with google/i })).toBeInTheDocument();
  });

  it('"Continue with Google" link points to the Google OAuth URL', () => {
    render(<Register />);
    const link = screen.getByRole('link', { name: /continue with google/i });
    expect(link).toHaveAttribute('href', GOOGLE_LOGIN_URL);
  });

  it('renders a link back to the login page', () => {
    render(<Register />);
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
  });

  // ── Form submission ────────────────────────────────────────────────────

  it('calls registerUser with entered values on submit', async () => {
    vi.mocked(registerUser).mockResolvedValue({ username: 'newuser', email: 'new@example.com' });
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'new@example.com');
    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/password/i), 'securepass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    expect(registerUser).toHaveBeenCalledWith('new@example.com', 'newuser', 'securepass');
  });

  it('sets the authenticated user and redirects on user payload response', async () => {
    vi.mocked(registerUser).mockResolvedValue({ username: 'newuser', email: 'new@example.com' });
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'new@example.com');
    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/password/i), 'securepass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() => expect(mockSetUser).toHaveBeenCalledWith({ username: 'newuser', email: 'new@example.com' }));
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
  });

  it('shows a loading spinner while the request is in flight', async () => {
    vi.mocked(registerUser).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'new@example.com');
    await user.type(screen.getByLabelText(/username/i), 'newuser');
    await user.type(screen.getByLabelText(/password/i), 'securepass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    expect(document.querySelector('.spinner-border')).not.toBeNull();
  });

  it('disables the submit button while loading', async () => {
    vi.mocked(registerUser).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/username/i), 'auser');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    expect(screen.getByRole('button', { name: /register/i })).toBeDisabled();
  });

  it('shows the server error message on failure', async () => {
    const err = { response: { data: { detail: 'Registration failed.' } } };
    vi.mocked(registerUser).mockRejectedValue(err);
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'dup@example.com');
    await user.type(screen.getByLabelText(/username/i), 'dupuser');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() =>
      expect(screen.getByText('Registration failed.')).toBeInTheDocument()
    );
  });

  it('falls back to a generic error message when the response has no detail', async () => {
    vi.mocked(registerUser).mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/username/i), 'auser');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() =>
      expect(screen.getByText('Registration failed.')).toBeInTheDocument()
    );
  });

  it('clears a previous error before a new submission', async () => {
    const err = { response: { data: { detail: 'Registration failed.' } } };
    vi.mocked(registerUser).mockRejectedValueOnce(err).mockResolvedValue({ username: 'newuser' });
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/username/i), 'auser');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(screen.getByText('Registration failed.')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /register/i }));
    await waitFor(() => expect(screen.queryByText('Registration failed.')).toBeNull());
  });

  it('shows a verification success message and does not assume auth when no user payload is returned', async () => {
    vi.mocked(registerUser).mockResolvedValue({
      detail: 'Registration successful. Please check your email to verify your account.',
    });
    const user = userEvent.setup();

    render(<Register />);

    await user.type(screen.getByLabelText(/email/i), 'verify@example.com');
    await user.type(screen.getByLabelText(/username/i), 'verifyuser');
    await user.type(screen.getByLabelText(/password/i), 'securepass');
    await user.click(screen.getByRole('button', { name: /register/i }));

    await waitFor(() =>
      expect(
        screen.getByText('Registration successful. Please check your email to verify your account.')
      ).toBeInTheDocument()
    );
    expect(mockSetUser).not.toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
