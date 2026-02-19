import React from 'react';
import { Link } from 'react-router-dom';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen w-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4 sm:p-6 lg:p-8 overflow-hidden">
      {/* Animated Background Blobs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 right-10 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-20 left-10 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      <div className="w-full max-w-md relative z-10">
        {/* Header */}
        <div className="mb-10 text-center">
          <Link to="/" className="inline-flex items-center gap-3 mb-8 group">
            <div className="w-12 h-12 bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/30 group-hover:shadow-cyan-500/50 transition-all group-hover:scale-110">
              <span className="text-white font-bold text-xl">⚡</span>
            </div>
            <span className="font-bold text-2xl bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              AutoNode
            </span>
          </Link>
          <h1 className="text-4xl sm:text-3xl font-bold text-slate-100 mb-3 tracking-tight">{title}</h1>
          <p className="text-slate-400 text-base leading-relaxed">{subtitle}</p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/50 border border-slate-700/50 rounded-2xl shadow-2xl p-8 sm:p-10 backdrop-blur-xl transition-all duration-300 hover:shadow-cyan-500/10">
          {children}
        </div>

        {/* Footer */}
        <p className="text-center text-sm text-slate-500 mt-8 px-2 leading-relaxed">
          By continuing, you agree to our{" "}
          <Link to="#" className="text-cyan-400 hover:text-purple-400 transition-colors font-medium">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link to="#" className="text-cyan-400 hover:text-purple-400 transition-colors font-medium">
            Privacy Policy
          </Link>
        </p>
      </div>
    </div>
  );
};