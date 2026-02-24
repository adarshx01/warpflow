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
    const state = searchParams.get('state');
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

    if (!state) {
      setError('Missing OAuth state parameter.');
      setTimeout(() => navigate('/login'), 3000);
      return;
    }

    handleGoogleCallback(code, state)
      .then(() => navigate('/workflow'))
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Google authentication failed.');
        setTimeout(() => navigate('/login'), 3000);
      });
  }, [searchParams, handleGoogleCallback, navigate]);

  return (
    <div className="min-h-screen w-screen bg-[#0a0a0f] flex items-center justify-center overflow-hidden relative">
      {/* Ambient glow blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-cyan-500/[0.05] rounded-full blur-[100px]" />
        <div className="absolute top-1/3 left-1/3 w-[300px] h-[300px] bg-purple-500/[0.05] rounded-full blur-[80px]" />
      </div>

      <div className="glass-card rounded-3xl p-8 sm:p-10 relative overflow-hidden w-full max-w-sm mx-4 z-10">
        {/* Subtle top highlight */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

        {error ? (
          <div className="text-center space-y-5">
            <div className="w-14 h-14 mx-auto bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center shadow-lg shadow-red-500/10">
              <span className="text-red-400 text-2xl">✕</span>
            </div>
            <div className="space-y-2">
              <p className="text-red-400 text-sm font-medium">{error}</p>
              <p className="text-slate-500 text-xs">Redirecting to login...</p>
            </div>
          </div>
        ) : (
          <div className="text-center space-y-6">
            <div className="relative w-16 h-16 mx-auto">
              {/* Outer spinning ring */}
              <div className="absolute inset-0 border-2 border-slate-700/50 rounded-full" />
              <div className="absolute inset-0 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              {/* Inner logo/icon */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xl">⚡</span>
              </div>
            </div>
            <div className="space-y-2">
              <h2 className="text-lg font-semibold text-white tracking-tight">Authenticating</h2>
              <p className="text-slate-400 text-sm">Securely signing you in...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
