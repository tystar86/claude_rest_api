import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { GOOGLE_LOGIN_URL, loginUser } from '../api/client';
import { resendVerification } from '../api/client';

vi.mock('../api/client', () => import('../test/mocks/client.js'));
vi.mock('react-router-dom', () => ({
  Link: ({ children, to }) => React.createElement('a', { href: to }, children),
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ setUser: vi.fn() }),
}));
vi.mock('../components/Navbar', () => ({
  default: () => React.createElement('div', { 'data-testid': 'navbar' }),
}));

import Login from './Login';

afterEach(() => vi.clearAllMocks());

describe('Login page', () => {
  // ── Rendering ──────────────────────────────────────────────────────────

  it('renders email and password fields', () => {
    render(<Login />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('renders a submit button', () => {
    render(<Login />);
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('renders a "Continue with Google" link', () => {
    render(<Login />);
    expect(screen.getByRole('link', { name: /continue with google/i })).toBeInTheDocument();
  });

  it('"Continue with Google" link points to the Google OAuth URL', () => {
    render(<Login />);
    const link = screen.getByRole('link', { name: /continue with google/i });
    expect(link).toHaveAttribute('href', GOOGLE_LOGIN_URL);
  });

  it('renders a link to the register page', () => {
    render(<Login />);
    expect(screen.getByRole('link', { name: /register/i })).toBeInTheDocument();
  });

  // ── Credential form submission ─────────────────────────────────────────

  it('calls loginUser with entered credentials on submit', async () => {
    vi.mocked(loginUser).mockResolvedValue({ username: 'alice', email: 'alice@example.com' });
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/password/i), 'secret123');
    await user.click(screen.getByRole('button', { name: /login/i }));

    expect(loginUser).toHaveBeenCalledWith('alice@example.com', 'secret123');
  });

  it('shows a loading spinner while the request is in flight', async () => {
    vi.mocked(loginUser).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    await user.type(screen.getByLabelText(/password/i), 'secret123');
    await user.click(screen.getByRole('button', { name: /login/i }));

    expect(document.querySelector('.spinner-border')).not.toBeNull();
  });

  it('disables the submit button while loading', async () => {
    vi.mocked(loginUser).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /login/i }));

    expect(screen.getByRole('button', { name: /login/i })).toBeDisabled();
  });

  it('shows the server error message on failure', async () => {
    const err = { response: { data: { detail: 'Invalid credentials.' } } };
    vi.mocked(loginUser).mockRejectedValue(err);
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'bad@example.com');
    await user.type(screen.getByLabelText(/password/i), 'wrongpass');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByText('Invalid credentials.')).toBeInTheDocument()
    );
  });

  it('falls back to a generic error message when the response has no detail', async () => {
    vi.mocked(loginUser).mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByText('Login failed.')).toBeInTheDocument()
    );
  });

  it('clears a previous error before a new submission', async () => {
    const err = { response: { data: { detail: 'Invalid credentials.' } } };
    vi.mocked(loginUser).mockRejectedValueOnce(err).mockResolvedValue({ username: 'alice' });
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/password/i), 'bad');
    await user.click(screen.getByRole('button', { name: /login/i }));
    await waitFor(() => expect(screen.getByText('Invalid credentials.')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /login/i }));
    await waitFor(() => expect(screen.queryByText('Invalid credentials.')).not.toBeInTheDocument());
  });

  // ── Email verification flow ───────────────────────────────────────────

  it('shows a resend button when login fails with code email_not_verified', async () => {
    const err = {
      response: { status: 403, data: { detail: 'Email address is not verified.', code: 'email_not_verified' } },
    };
    vi.mocked(loginUser).mockRejectedValue(err);
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(screen.getByText('Email address is not verified.')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /resend verification email/i })).toBeInTheDocument();
    });
  });

  it('does not show resend button for non-verification 403 errors', async () => {
    const err = {
      response: { status: 403, data: { detail: 'Permission denied.' } },
    };
    vi.mocked(loginUser).mockRejectedValue(err);
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'a@a.com');
    await user.type(screen.getByLabelText(/password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() => {
      expect(screen.getByText('Permission denied.')).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /resend verification email/i })).not.toBeInTheDocument();
  });

  it('calls resendVerification with the entered email and shows success in a success alert', async () => {
    const err = {
      response: { status: 403, data: { detail: 'Email address is not verified.', code: 'email_not_verified' } },
    };
    vi.mocked(loginUser).mockRejectedValue(err);
    vi.mocked(resendVerification).mockResolvedValue({
      detail: 'Verification email sent. Please check your inbox.',
    });
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /resend verification email/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /resend verification email/i }));

    await waitFor(() => {
      const alert = screen.getByText('Verification email sent. Please check your inbox.');
      expect(alert).toBeInTheDocument();
      expect(alert.closest('.alert')).toHaveClass('alert-success');
    });
    expect(resendVerification).toHaveBeenCalledWith('unverified@example.com');
  });

  it('shows resend failure in a danger alert', async () => {
    const loginErr = {
      response: { status: 403, data: { detail: 'Not verified.', code: 'email_not_verified' } },
    };
    vi.mocked(loginUser).mockRejectedValue(loginErr);
    vi.mocked(resendVerification).mockRejectedValue({
      response: { data: { detail: 'Too many requests.' } },
    });
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /resend verification email/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /resend verification email/i }));

    await waitFor(() => {
      const alert = screen.getByText('Too many requests.');
      expect(alert).toBeInTheDocument();
      expect(alert.closest('.alert')).toHaveClass('alert-danger');
    });
  });

  it('falls back to generic message when resend fails without a detail field', async () => {
    const loginErr = {
      response: { status: 403, data: { detail: 'Not verified.', code: 'email_not_verified' } },
    };
    vi.mocked(loginUser).mockRejectedValue(loginErr);
    vi.mocked(resendVerification).mockRejectedValue(new Error('network'));
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /resend verification email/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /resend verification email/i }));

    await waitFor(() =>
      expect(screen.getByText('Failed to resend verification email.')).toBeInTheDocument()
    );
  });

  it('disables the resend button and shows spinner while resending', async () => {
    const loginErr = {
      response: { status: 403, data: { detail: 'Not verified.', code: 'email_not_verified' } },
    };
    vi.mocked(loginUser).mockRejectedValue(loginErr);
    vi.mocked(resendVerification).mockReturnValue(new Promise(() => {}));
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /resend verification email/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /resend verification email/i }));

    expect(screen.getByRole('button', { name: /resend verification email/i })).toBeDisabled();
    expect(document.querySelectorAll('.spinner-border').length).toBeGreaterThan(0);
  });

  it('uses fallback success message when resend response has no detail', async () => {
    const loginErr = {
      response: { status: 403, data: { detail: 'Not verified.', code: 'email_not_verified' } },
    };
    vi.mocked(loginUser).mockRejectedValue(loginErr);
    vi.mocked(resendVerification).mockResolvedValue({});
    const user = userEvent.setup();

    render(<Login />);

    await user.type(screen.getByLabelText(/email/i), 'unverified@example.com');
    await user.type(screen.getByLabelText(/password/i), 'password');
    await user.click(screen.getByRole('button', { name: /login/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /resend verification email/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /resend verification email/i }));

    await waitFor(() =>
      expect(screen.getByText('Verification email sent. Please check your inbox.')).toBeInTheDocument()
    );
  });
});
