import React from 'react';

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  children: React.ReactNode;
  className?: string;
}

export const Label: React.FC<LabelProps> = ({ children, className = '', ...props }) => {
  return (
    <label className={`block text-sm font-semibold text-slate-300 mb-2 ${className}`} {...props}>
      {children}
    </label>
  );
};