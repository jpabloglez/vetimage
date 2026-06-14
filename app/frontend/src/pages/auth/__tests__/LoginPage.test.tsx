import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import LoginPage from '../LoginPage';
import { AuthProvider } from '../../../contexts/AuthContext';
import { apiClient } from '../../../utils/api';

// Mock the API client with the complete surface so AuthProvider mounts cleanly.
vi.mock('../../../utils/api', async () => {
  const { createApiClientMock } = await import('../../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

// Mock react-router-dom navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const renderLoginPage = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getProfile as any).mockRejectedValue(
      new Error('No active session')
    );
  });

  it('should render login form', async () => {
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Sign In/i })
    ).toBeInTheDocument();
  });

  it('should show validation errors for empty fields', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /Sign In/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    });
  });

  it('should login successfully and navigate to /tools', async () => {
    const user = userEvent.setup();
    const mockResponse = {
      access: 'mock-token',
      refresh: 'mock-refresh-token',
      user: {
        id: 1,
        email: 'test@example.com',
        role: 1,
      },
    };

    (apiClient.login as any).mockResolvedValueOnce(mockResponse);

    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    const emailInput = screen.getByLabelText(/Email Address/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /Sign In/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'password123');
    await user.click(submitButton);

    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(mockNavigate).toHaveBeenCalledWith('/models');
    });
  });

  it('should show error message on login failure', async () => {
    const user = userEvent.setup();

    (apiClient.login as any).mockRejectedValueOnce(
      new Error('Invalid credentials')
    );

    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    const emailInput = screen.getByLabelText(/Email Address/i);
    const passwordInput = screen.getByLabelText(/Password/i);
    const submitButton = screen.getByRole('button', { name: /Sign In/i });

    await user.type(emailInput, 'test@example.com');
    await user.type(passwordInput, 'wrongpassword');
    await user.click(submitButton);

    await waitFor(() => {
      expect(apiClient.login).toHaveBeenCalled();
    });
  });

  it('should toggle password visibility', async () => {
    const user = userEvent.setup();
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    const passwordInput = screen.getByLabelText(/Password/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Find and click the eye icon button
    const toggleButtons = screen.getAllByRole('button');
    const toggleButton = toggleButtons.find(
      (btn) =>
        btn !== screen.getByRole('button', { name: /Sign In/i }) &&
        btn.querySelector('svg')
    );

    if (toggleButton) {
      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'text');

      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    }
  });

  it('should have link to register page', async () => {
    renderLoginPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
    });

    const signUpLink = screen.getByText(/Sign up/i);
    expect(signUpLink).toBeInTheDocument();
    expect(signUpLink.closest('a')).toHaveAttribute('href', '/auth/register');
  });
});
