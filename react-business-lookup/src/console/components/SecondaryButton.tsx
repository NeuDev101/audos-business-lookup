import type { ReactNode, ButtonHTMLAttributes } from 'react';

interface SecondaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
}

export function SecondaryButton({ children, className = '', ...props }: SecondaryButtonProps) {
  return (
    <button
      className={`px-6 py-2.5 border border-dark-border text-gray-300 hover:bg-dark-border font-medium rounded-lg transition-colors ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}