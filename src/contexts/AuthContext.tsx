import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

interface User {
  id: string;
  name: string;
  email: string;
  auth_provider: string;
  avatar_url?: string | null;
}

interface AuthResponse {
  user: User;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  handleGoogleCallback: (code: string, state: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (window.location.pathname === '/auth/google/callback') {
      setIsLoading(false);
      return;
    }
    api<User>('/api/auth/me', { skipAuthRedirect: true })
      .then((userData) => {
        setUser(userData);
      })
      .catch(() => {
        // if No valid cookie / session expired
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const data = await api<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    setUser(data.user);
  };

  const signup = async (name: string, email: string, password: string) => {
    const data = await api<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: { name, email, password },
    });
    setUser(data.user);
  };

  const loginWithGoogle = async () => {
    const data = await api<{ url: string; state: string }>('/api/auth/google');
    sessionStorage.setItem('oauth_state', data.state);
    window.location.href = data.url;
  };

  const handleGoogleCallback = useCallback(async (code: string, state: string) => {
    const savedState = sessionStorage.getItem('oauth_state');
    sessionStorage.removeItem('oauth_state');
    if (!state || state !== savedState) {
      throw new Error('OAuth state mismatch. Please try again.');
    }
    const data = await api<AuthResponse>('/api/auth/google/callback', {
      method: 'POST',
      body: { code, state },
    });
    setUser(data.user);
  }, []);

  const logout = async () => {
    try {
      await api('/api/auth/logout', { method: 'POST' });
    } catch {
      // Ignore errors — cookie may already be gone --- need to add
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        signup,
        loginWithGoogle,
        handleGoogleCallback,
        logout,
        isAuthenticated: !!user,
        isLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};