import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { apiClient } from '../../utils/api';

// Mock the API client with the complete surface (getAccessToken, refreshToken,
// etc.) so the provider's mount-time session restore never crashes.
vi.mock('../../utils/api', async () => {
  const { createApiClientMock } = await import('../../test/mockApiClient');
  return { apiClient: createApiClientMock() };
});

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset stateful implementations (persist across clearAllMocks) to a clean
    // logged-out baseline so tests don't leak into one another.
    (apiClient.getAccessToken as any).mockReset().mockReturnValue(null);
    (apiClient.refreshToken as any).mockReset().mockRejectedValue(new Error('No token'));
    (apiClient.getProfile as any).mockReset().mockRejectedValue(new Error('No active session'));
  });

  it('should initialize with null user and loading state', async () => {
    (apiClient.getProfile as any).mockRejectedValueOnce(
      new Error('No active session')
    );

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.user).toBe(null);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should load user profile on mount if session exists', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      role: 1,
    };

    // Simulate an existing access token so initAuth skips refresh and loads the profile.
    (apiClient.getAccessToken as any).mockReturnValue('existing-token');
    (apiClient.getProfile as any).mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
      expect(result.current.user).toEqual(mockUser);
      expect(result.current.isAuthenticated).toBe(true);
    });
  });

  it('should login and update user state', async () => {
    (apiClient.getProfile as any).mockRejectedValueOnce(
      new Error('No session')
    );

    const mockResponse = {
      access: 'mock-token',
      user: {
        id: 1,
        email: 'test@example.com',
        role: 1,
      },
    };

    (apiClient.login as any).mockResolvedValueOnce(mockResponse);

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.login('test@example.com', 'password123');
    });

    expect(result.current.user).toEqual(mockResponse.user);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should register and update user state', async () => {
    (apiClient.getProfile as any).mockRejectedValueOnce(
      new Error('No session')
    );

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

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.register(
        'newuser@example.com',
        'password123',
        'password123'
      );
    });

    expect(result.current.user).toEqual(mockResponse.user);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should logout and clear user state', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      role: 1,
    };

    (apiClient.getAccessToken as any).mockReturnValue('existing-token');
    (apiClient.getProfile as any).mockResolvedValue(mockUser);
    (apiClient.logout as any).mockResolvedValueOnce({
      message: 'Logout successful',
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBe(null);
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should throw error on login failure', async () => {
    (apiClient.getProfile as any).mockRejectedValueOnce(
      new Error('No session')
    );

    (apiClient.login as any).mockRejectedValueOnce(
      new Error('Invalid credentials')
    );

    const { result } = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await expect(
      act(async () => {
        await result.current.login('test@example.com', 'wrong-password');
      })
    ).rejects.toThrow('Invalid credentials');

    expect(result.current.user).toBe(null);
  });
});
