/**
 * Shared test utilities for rendering components with required providers.
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { vi } from 'vitest';

// Mock apiClient by default so AuthProvider doesn't make real requests
vi.mock('./utils/api', () => ({
  apiClient: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    getProfile: vi.fn().mockRejectedValue(new Error('No session')),
    refreshToken: vi.fn().mockRejectedValue(new Error('No token')),
    getAccessToken: vi.fn().mockReturnValue(null),
    createAnalysisTask: vi.fn(),
  },
}));

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

/**
 * Render a component wrapped in BrowserRouter + AuthProvider.
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <BrowserRouter>
        <AuthProvider>{children}</AuthProvider>
      </BrowserRouter>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}
