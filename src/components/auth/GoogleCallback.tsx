import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export const GoogleCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { handleGoogleCallback } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const calledRef = useRef(false);

  useEffect(() => {
    // Guard: Google auth codes are single-use. React StrictMode double-fires
    // effects in dev, so the second call would always get "invalid_grant".
    if (calledRef.current) return;
    calledRef.current = true;

    const code = searchParams.get('code');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError('Google authentication was cancelled or failed.');
      setTimeout(() => navigate('/login'), 3000);
      return;
    }

    if (!code) {
      setError('No authorization code received from Google.');
      setTimeout(() => navigate('/login'), 3000);
      return;
    }

    handleGoogleCallback(code)
      .then(() => navigate('/workflow'))
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Google authentication failed.');
        setTimeout(() => navigate('/login'), 3000);
      });
  }, [searchParams, handleGoogleCallback, navigate]);

  return (
    <div className="min-h-screen w-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      {error ? (
        <div className="text-center space-y-4">
          <div className="w-12 h-12 mx-auto bg-red-500/20 rounded-full flex items-center justify-center">
            <span className="text-red-400 text-xl">✕</span>
          </div>
          <p className="text-red-400 text-sm">{error}</p>
          <p className="text-slate-500 text-xs">Redirecting to login...</p>
        </div>
      ) : (
        <div className="text-center space-y-4">
          <div className="w-8 h-8 mx-auto border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">Completing Google sign-in...</p>
        </div>
      )}
    </div>
  );
};
