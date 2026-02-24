import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { LoginForm } from '../components/auth/LoginForm';
import { SignupForm } from '../components/auth/SignupForm';

const AuthPage: React.FC = () => {
  const location = useLocation();
  const [mode, setMode] = useState<'login' | 'signup'>(
    location.pathname === '/signup' ? 'signup' : 'login'
  );

  return (
    <div className="min-h-screen w-screen bg-[#0a0a0f] flex overflow-hidden relative">
      {/* Ambient glow blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-cyan-500/[0.07] rounded-full blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] bg-purple-500/[0.07] rounded-full blur-[120px]" />
        <div className="absolute top-1/2 left-1/3 w-[400px] h-[400px] bg-blue-500/[0.04] rounded-full blur-[100px]" />
      </div>

      {/* ── Left Panel: Brand + GIF ── */}
      <div className="hidden lg:flex lg:w-[55%] xl:w-[58%] relative flex-col p-8 xl:p-12">
        {/* Logo */}
        <div className="flex items-center gap-3 z-10">
          {/* <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/25">
            <span className="text-white font-bold text-lg">⚡</span>
          </div>
          <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
            WarpFlow
          </span> */}
          <img src="/warpflow-logo-small.png" alt="WarpFlow Logo" className="h-96 filter invert" />
        </div>

        {/* GIF showcase */}
        <div className="flex-1 flex items-center justify-center z-10">
          <div className="relative w-full max-w-2xl">
            {/* Frosted glass frame around the GIF */}
            <div className="glass-card-strong rounded-2xl p-2 shadow-2xl shadow-black/40">
              <img
                src="/workflow.gif"
                alt="WarpFlow workflow automation"
                className="w-full rounded-xl"
                draggable={false}
              />
            </div>
            {/* Glow beneath the GIF */}
            <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 w-3/4 h-16 bg-cyan-500/10 rounded-full blur-2xl" />
          </div>
        </div>

        {/* Tagline at the bottom-left */}
        <div className="z-10">
          <p className="text-slate-500 text-sm font-medium">
            Intelligent workflow automation — built for speed.
          </p>
        </div>
      </div>

      {/* ── Right Panel: Auth Form ── */}
      <div className="w-full lg:w-[45%] xl:w-[42%] flex items-center justify-center p-6 sm:p-8 relative z-10">
        <div className="w-full max-w-md">
          {/* Mobile-only logo */}
          <div className="flex lg:hidden items-center gap-3 mb-10 justify-center">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/25">
              <span className="text-white font-bold text-lg">⚡</span>
            </div>
            <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              WarpFlow
            </span>
          </div>

          {/* Frosted glass card */}
          <div className="glass-card rounded-3xl p-8 sm:p-10 relative overflow-hidden">
            {/* Subtle top highlight */}
            <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

            {/* Header */}
            <div className="mb-8">
              <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                {mode === 'login' ? 'Welcome back' : 'Create account'}
              </h1>
              <p className="text-slate-400 text-sm mt-2 leading-relaxed">
                {mode === 'login'
                  ? 'Sign in to continue to your workflows'
                  : 'Start automating your workflows in minutes'}
              </p>
            </div>

            {/* Form area with crossfade */}
            <div className="relative">
              <div
                className={`transition-all duration-300 ease-out ${
                  mode === 'login'
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 translate-y-2 pointer-events-none absolute inset-0'
                }`}
              >
                <LoginForm onToggle={() => setMode('signup')} />
              </div>
              <div
                className={`transition-all duration-300 ease-out ${
                  mode === 'signup'
                    ? 'opacity-100 translate-y-0'
                    : 'opacity-0 translate-y-2 pointer-events-none absolute inset-0'
                }`}
              >
                <SignupForm onToggle={() => setMode('login')} />
              </div>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-slate-600 mt-6 px-2 leading-relaxed">
            By continuing, you agree to our{' '}
            <a href="#" className="text-slate-500 hover:text-cyan-400 transition-colors">
              Terms
            </a>{' '}
            and{' '}
            <a href="#" className="text-slate-500 hover:text-cyan-400 transition-colors">
              Privacy Policy
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
