/**
 * Shared test utilities for rendering components with required providers.
 */

import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { vi } from 'vitest';

// Mock apiClient with the COMPLETE surface so AuthProvider (and any rendered
// component) never crashes on a missing method. Tests needing custom return
// values should define their own vi.mock with createApiClientMock(overrides).
vi.mock('./utils/api', async () => {
  const { createApiClientMock } = await import('./test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

// Re-export the factory so test files can build their own customised mocks.
export { createApiClientMock } from './test/mockApiClient';

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
