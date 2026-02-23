import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';

interface User {
  id: string;
  name: string;
  email: string;
  auth_provider: string;
  avatar_url?: string | null;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  handleGoogleCallback: (code: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      api<User>('/api/auth/me', { token: storedToken })
        .then((userData) => {
          setUser(userData);
        })
        .catch(() => {
          // Token expired or invalid
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setToken(null);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const persistSession = (data: TokenResponse) => {
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
  };

  const login = async (email: string, password: string) => {
    const data = await api<TokenResponse>('/api/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    persistSession(data);
  };

  const signup = async (name: string, email: string, password: string) => {
    const data = await api<TokenResponse>('/api/auth/register', {
      method: 'POST',
      body: { name, email, password },
    });
    persistSession(data);
  };

  const loginWithGoogle = async () => {
    const data = await api<{ url: string }>('/api/auth/google');
    window.location.href = data.url;
  };

  const handleGoogleCallback = useCallback(async (code: string) => {
    const data = await api<TokenResponse>('/api/auth/google/callback', {
      method: 'POST',
      body: { code },
    });
    persistSession(data);
  }, []);

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
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