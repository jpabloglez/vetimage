import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient } from '../api';

// Mock fetch
global.fetch = vi.fn();

describe('ApiClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should login successfully and store access token', async () => {
      const mockResponse = {
        access: 'mock-access-token',
        refresh: 'mock-refresh-token',
        user: {
          id: 1,
          email: 'test@example.com',
          role: 1,
        },
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/users/auth/login/'),
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
          }),
        })
      );
    });

    it('should throw error on login failure', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ message: 'Invalid credentials' }),
      });

      await expect(
        apiClient.login({
          email: 'test@example.com',
          password: 'wrong-password',
        })
      ).rejects.toThrow();
    });
  });

  describe('register', () => {
    it('should register successfully', async () => {
      const mockResponse = {
        access: 'mock-access-token',
        user: {
          id: 1,
          email: 'newuser@example.com',
          role: 1,
        },
        message: 'User registered successfully',
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.register({
        email: 'newuser@example.com',
        password: 'password123',
        password_confirm: 'password123',
        role: 1,
      });

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/users/auth/register/'),
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
        })
      );
    });
  });

  describe('logout', () => {
    it('should logout successfully', async () => {
      const mockResponse = {
        message: 'Logout successful',
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await apiClient.logout();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/users/auth/logout/'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('getProfile', () => {
    it('should get user profile when authenticated', async () => {
      const mockProfile = {
        id: 1,
        email: 'test@example.com',
        role: 1,
      };

      // Mock login first to set access token
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: {
          get: vi.fn().mockReturnValue('application/json'),
        },
        json: async () => ({
          access: 'mock-access-token',
          user: mockProfile,
        }),
      });

      await apiClient.login({
        email: 'test@example.com',
        password: 'password123',
      });

      // Now mock profile request
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: {
          get: vi.fn().mockReturnValue('application/json'),
        },
        json: async () => mockProfile,
      });

      const result = await apiClient.getProfile();

      expect(result).toEqual(mockProfile);
      expect(global.fetch).toHaveBeenLastCalledWith(
        expect.stringContaining('/users/auth/profile/'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer mock-access-token',
          }),
        })
      );
    });
  });

  describe('token refresh', () => {
    it('should refresh token on 401 and retry request', async () => {
      const mockProfile = {
        id: 1,
        email: 'test@example.com',
        role: 1,
      };

      // Mock login to set initial access token
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: {
          get: vi.fn().mockReturnValue('application/json'),
        },
        json: async () => ({
          access: 'old-access-token',
          user: mockProfile,
        }),
      });

      await apiClient.login({
        email: 'test@example.com',
        password: 'password123',
      });

      // Mock 401 response on profile request
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 401,
        headers: {
          get: vi.fn().mockReturnValue('application/json'),
        },
        json: async () => ({ detail: 'Token expired' }),
      });

      // Mock successful token refresh
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: {
          get: vi.fn().mockReturnValue('application/json'),
        },
        json: async () => ({ access: 'new-access-token' }),
      });

      // Mock successful retry with new token
      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        headers: {
          get: vi.fn().mockReturnValue('application/json'),
        },
        json: async () => mockProfile,
      });

      const result = await apiClient.getProfile();

      expect(result).toEqual(mockProfile);
      // Should have called refresh endpoint
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/users/auth/refresh/'),
        expect.any(Object)
      );
    });
  });
});
