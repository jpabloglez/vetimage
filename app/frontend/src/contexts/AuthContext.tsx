import React, { createContext, useState, useContext, useEffect, useCallback, ReactNode } from 'react';
import { apiClient, type User } from '../utils/api';
import i18n from '../i18n';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, passwordConfirm: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (uid: string, token: string, newPassword: string, newPasswordConfirm: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Update global token for WebSocket authentication
   *
   * Ensures window.__auth_token__ is synchronized with apiClient token
   */
  const updateGlobalToken = useCallback(() => {
    const token = apiClient.getAccessToken();
    if (token) {
      (window as any).__auth_token__ = token;
    } else {
      delete (window as any).__auth_token__;
    }
  }, []);

  /**
   * Listen for token refresh events from apiClient
   */
  useEffect(() => {
    const handleTokenRefresh = () => {
      updateGlobalToken();
    };

    window.addEventListener('auth:token-refreshed', handleTokenRefresh);

    return () => {
      window.removeEventListener('auth:token-refreshed', handleTokenRefresh);
    };
  }, [updateGlobalToken]);

  /**
   * Initialize auth state on mount - attempt to refresh token
   */
  useEffect(() => {
    const initAuth = async () => {
      try {
        // Check if we already have an access token (e.g., just logged in)
        const currentAccessToken = apiClient.getAccessToken();

        if (!currentAccessToken) {
          // No access token in memory - try to refresh from cookie
          // This happens on page refresh or when opening the app
          const refreshSuccess = await apiClient.refreshToken();

          if (!refreshSuccess) {
            // No valid refresh token - user not logged in
            // This is normal when visiting the app for the first time or after session expired
            setUser(null);
            setIsLoading(false);
            return;
          }
        }

        // Now get user profile with the access token (existing or refreshed)
        const profile = await apiClient.getProfile();
        setUser(profile);

        // Sync language from user profile
        if (profile.language && ['en', 'es', 'pt'].includes(profile.language)) {
          i18n.changeLanguage(profile.language);
        }

        // ALWAYS expose access token globally for WebSocket authentication
        // This ensures token is available after refresh, not just after login
        updateGlobalToken();
      } catch (error) {
        console.error('Failed to get user profile:', error);
        setUser(null);
        // Clear stale token on error
        delete (window as any).__auth_token__;
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();

    // Listen for token expiration events
    const handleTokenExpired = () => {
      console.log('Token expired event received');
      setUser(null);
      // Only redirect if not already on an auth page (avoid loops); flag the
      // reason so the login page can show a friendly "session expired" message.
      if (!window.location.pathname.startsWith('/auth/')) {
        window.location.href = '/auth/login?session=expired';
      }
    };

    window.addEventListener('auth:token-expired', handleTokenExpired);

    return () => {
      window.removeEventListener('auth:token-expired', handleTokenExpired);
    };
  }, [updateGlobalToken]);

  /**
   * Login user
   */
  const login = async (email: string, password: string) => {
    try {
      const response = await apiClient.login({ email, password });
      setUser(response.user);

      // Sync language from user profile
      if (response.user.language && ['en', 'es', 'pt'].includes(response.user.language)) {
        i18n.changeLanguage(response.user.language);
      }

      // Expose access token globally for WebSocket authentication
      updateGlobalToken();
    } catch (error: any) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  /**
   * Register new user
   */
  const register = async (email: string, password: string, passwordConfirm: string) => {
    try {
      const response = await apiClient.register({
        email,
        password,
        password_confirm: passwordConfirm,
        role: 1, // Default user role
      });
      setUser(response.user);
    } catch (error: any) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  /**
   * Logout user
   */
  const logout = async () => {
    try {
      await apiClient.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
      // Clear global token for WebSocket
      delete (window as any).__auth_token__;
    }
  };

  /**
   * Request password reset email
   */
  const forgotPassword = async (email: string) => {
    await apiClient.forgotPassword(email);
  };

  /**
   * Reset password with token
   */
  const resetPassword = async (uid: string, token: string, newPassword: string, newPasswordConfirm: string) => {
    await apiClient.resetPassword(uid, token, newPassword, newPasswordConfirm);
  };

  /**
   * Refresh user profile data
   */
  const refreshUser = async () => {
    try {
      const profile = await apiClient.getProfile();
      setUser(profile);

      // Ensure token is synchronized after profile refresh
      updateGlobalToken();
    } catch (error) {
      console.error('Failed to refresh user:', error);
      setUser(null);
      delete (window as any).__auth_token__;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
        forgotPassword,
        resetPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
