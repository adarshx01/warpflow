import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  className?: string;
}

export const Input: React.FC<InputProps> = ({ className = '', ...props }) => {
  return (
    <input
      className={`w-full px-4 py-2.5 glass-input rounded-xl text-slate-200 text-sm placeholder-slate-500 focus:outline-none transition-all ${className}`}
      {...props}
    />
  );
};