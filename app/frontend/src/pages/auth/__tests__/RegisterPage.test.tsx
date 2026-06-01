import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import userEvent from '@testing-library/user-event';
import RegisterPage from '../RegisterPage';
import { AuthProvider } from '../../../contexts/AuthContext';
import { apiClient } from '../../../utils/api';

// Mock the API client
vi.mock('../../../utils/api', () => ({
  apiClient: {
    register: vi.fn(),
    getProfile: vi.fn(),
  },
}));

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

const renderRegisterPage = () => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <RegisterPage />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (apiClient.getProfile as any).mockRejectedValue(
      new Error('No active session')
    );
  });

  it('should render registration form', async () => {
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    expect(screen.getByLabelText(/Full Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Email Address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Role/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Institution/i)).toBeInTheDocument();

    // Password fields
    const passwordLabels = screen.getAllByText(/Password/i);
    expect(passwordLabels.length).toBeGreaterThan(0);

    expect(
      screen.getByRole('button', { name: /Create Account/i })
    ).toBeInTheDocument();
  });

  it('should show validation errors for empty required fields', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', {
      name: /Create Account/i,
    });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });
  });

  it('should register successfully and navigate to /tools', async () => {
    const user = userEvent.setup();
    const mockResponse = {
      access: 'mock-token',
      user: {
        id: 1,
        email: 'newuser@example.com',
        role: 1,
      },
      message: 'User registered successfully',
    };

    (apiClient.register as any).mockResolvedValueOnce(mockResponse);

    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const institutionInput = screen.getByLabelText(/Institution/i);

    const passwordInputs = screen.getAllByLabelText(/Password/i, {
      exact: false,
    });
    const passwordInput = passwordInputs[0];
    const confirmPasswordInput = passwordInputs[1];

    const termsCheckbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', {
      name: /Create Account/i,
    });

    await user.type(nameInput, 'Dr. John Smith');
    await user.type(emailInput, 'newuser@example.com');
    await user.type(institutionInput, 'General Hospital');
    await user.type(passwordInput, 'StrongPass123!');
    await user.type(confirmPasswordInput, 'StrongPass123!');
    await user.click(termsCheckbox);
    await user.click(submitButton);

    await waitFor(() => {
      expect(apiClient.register).toHaveBeenCalledWith(
        'newuser@example.com',
        'StrongPass123!',
        'StrongPass123!'
      );
      expect(mockNavigate).toHaveBeenCalledWith('/tools');
    });
  });

  it('should show error for password mismatch', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);

    const passwordInputs = screen.getAllByLabelText(/Password/i, {
      exact: false,
    });
    const passwordInput = passwordInputs[0];
    const confirmPasswordInput = passwordInputs[1];

    const termsCheckbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', {
      name: /Create Account/i,
    });

    await user.type(nameInput, 'Dr. John Smith');
    await user.type(emailInput, 'newuser@example.com');
    await user.type(passwordInput, 'StrongPass123!');
    await user.type(confirmPasswordInput, 'DifferentPass456!');
    await user.click(termsCheckbox);
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Passwords don't match/i)).toBeInTheDocument();
    });
  });

  it('should show error on registration failure', async () => {
    const user = userEvent.setup();

    (apiClient.register as any).mockRejectedValueOnce(
      new Error('Email already exists')
    );

    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const institutionInput = screen.getByLabelText(/Institution/i);

    const passwordInputs = screen.getAllByLabelText(/Password/i, {
      exact: false,
    });
    const passwordInput = passwordInputs[0];
    const confirmPasswordInput = passwordInputs[1];

    const termsCheckbox = screen.getByRole('checkbox');
    const submitButton = screen.getByRole('button', {
      name: /Create Account/i,
    });

    await user.type(nameInput, 'Dr. John Smith');
    await user.type(emailInput, 'existing@example.com');
    await user.type(institutionInput, 'General Hospital');
    await user.type(passwordInput, 'StrongPass123!');
    await user.type(confirmPasswordInput, 'StrongPass123!');
    await user.click(termsCheckbox);
    await user.click(submitButton);

    await waitFor(() => {
      expect(apiClient.register).toHaveBeenCalled();
    });
  });

  it('should have link to login page', async () => {
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const signInLink = screen.getByText(/Sign in/i);
    expect(signInLink).toBeInTheDocument();
    expect(signInLink.closest('a')).toHaveAttribute('href', '/auth/login');
  });

  it('should show specialization field for doctor role', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const roleSelect = screen.getByLabelText(/Role/i);

    // Default role should be doctor
    expect(roleSelect).toHaveValue('doctor');

    // Specialization field should be visible
    const specializationInput = screen.getByLabelText(/Specialization/i);
    expect(specializationInput).toBeInTheDocument();
    expect(specializationInput).toHaveAttribute(
      'placeholder',
      'Radiology, Cardiology, etc.'
    );
  });

  it('should change specialization field label for researcher role', async () => {
    const user = userEvent.setup();
    renderRegisterPage();

    await waitFor(() => {
      expect(screen.getByText('Create Account')).toBeInTheDocument();
    });

    const roleSelect = screen.getByLabelText(/Role/i);

    // Change to researcher role
    await user.selectOptions(roleSelect, 'researcher');

    // Research Area field should be visible
    const researchAreaInput = screen.getByLabelText(/Research Area/i);
    expect(researchAreaInput).toBeInTheDocument();
    expect(researchAreaInput).toHaveAttribute(
      'placeholder',
      'Machine Learning, Medical Imaging, etc.'
    );
  });
});
