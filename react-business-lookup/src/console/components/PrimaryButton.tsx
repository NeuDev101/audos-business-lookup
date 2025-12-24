import type { ReactNode, ButtonHTMLAttributes } from 'react';

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export function PrimaryButton({ children, className = '', ...props }: PrimaryButtonProps) {
  return (
    <button
      className={`px-6 py-2.5 bg-primary hover:bg-primary-hover text-white font-medium rounded-lg transition-colors ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}