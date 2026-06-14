import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import RegisterPage from '../RegisterPage';
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
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const renderRegisterPage = () => render(
  <BrowserRouter>
    <AuthProvider>
      <RegisterPage />
    </AuthProvider>
  </BrowserRouter>
);

const submitBtn = () => screen.getByRole('button', { name: /Create Account/i });

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getProfile as any).mockRejectedValue(new Error('No active session'));
  });

  it('renders the registration form with key fields', async () => {
    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Role/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Institution/i)).toBeInTheDocument();
    expect(screen.getAllByLabelText(/Password/i).length).toBeGreaterThan(0);
  });

  it('blocks submission and shows validation errors when empty', async () => {
    const user = userEvent.setup();
    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    await user.click(submitBtn());

    // Zod validation prevents the API call and surfaces a field error.
    await waitFor(() => {
      expect(screen.getByText(/Name must be at least/i)).toBeInTheDocument();
    });
    expect(apiClient.register).not.toHaveBeenCalled();
  });

  it('registers successfully and navigates to /models', async () => {
    const user = userEvent.setup();
    (apiClient.register as any).mockResolvedValueOnce({
      access: 'mock-token', user: { id: 1, email: 'newuser@example.com', role: 1 },
    });

    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Full Name/i), 'Jane Vet');
    await user.type(screen.getByLabelText(/Email Address/i), 'newuser@example.com');
    await user.type(screen.getByLabelText(/Institution/i), 'City Animal Clinic');
    const pws = screen.getAllByLabelText(/Password/i, { exact: false });
    await user.type(pws[0], 'StrongPass123!');
    await user.type(pws[1], 'StrongPass123!');
    await user.click(screen.getByRole('checkbox'));
    await user.click(submitBtn());

    await waitFor(() => {
      // AuthContext.register → apiClient.register({ email, password, password_confirm, role })
      expect(apiClient.register).toHaveBeenCalledWith(
        expect.objectContaining({
          email: 'newuser@example.com',
          password: 'StrongPass123!',
          password_confirm: 'StrongPass123!',
        }),
      );
      expect(mockNavigate).toHaveBeenCalledWith('/models');
    });
  });

  it('shows an error and does not submit on password mismatch', async () => {
    const user = userEvent.setup();
    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Full Name/i), 'Jane Vet');
    await user.type(screen.getByLabelText(/Email Address/i), 'newuser@example.com');
    const pws = screen.getAllByLabelText(/Password/i, { exact: false });
    await user.type(pws[0], 'StrongPass123!');
    await user.type(pws[1], 'DifferentPass456!');
    await user.click(screen.getByRole('checkbox'));
    await user.click(submitBtn());

    await waitFor(() => {
      expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
    });
    expect(apiClient.register).not.toHaveBeenCalled();
  });

  it('calls register when the API rejects (error path)', async () => {
    const user = userEvent.setup();
    (apiClient.register as any).mockRejectedValueOnce(new Error('Email already exists'));

    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    await user.type(screen.getByLabelText(/Full Name/i), 'Jane Vet');
    await user.type(screen.getByLabelText(/Email Address/i), 'existing@example.com');
    const pws = screen.getAllByLabelText(/Password/i, { exact: false });
    await user.type(pws[0], 'StrongPass123!');
    await user.type(pws[1], 'StrongPass123!');
    await user.click(screen.getByRole('checkbox'));
    await user.click(submitBtn());

    await waitFor(() => expect(apiClient.register).toHaveBeenCalled());
  });

  it('defaults to the Veterinarian role and shows the Specialization field', async () => {
    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    const roleSelect = screen.getByLabelText(/Role/i);
    expect(roleSelect).toHaveValue('doctor'); // internal value; label is "Veterinarian"
    expect(screen.getByLabelText(/Specialization/i)).toBeInTheDocument();
  });

  it('switches to the Research Area field for the researcher role', async () => {
    const user = userEvent.setup();
    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    await user.selectOptions(screen.getByLabelText(/Role/i), 'researcher');
    await waitFor(() => {
      expect(screen.getByLabelText(/Research Area/i)).toBeInTheDocument();
    });
  });

  it('links to the login page', async () => {
    renderRegisterPage();
    await waitFor(() => expect(submitBtn()).toBeInTheDocument());

    const signIn = screen.getByText(/Sign in/i);
    expect(signIn.closest('a')).toHaveAttribute('href', '/auth/login');
  });
});
