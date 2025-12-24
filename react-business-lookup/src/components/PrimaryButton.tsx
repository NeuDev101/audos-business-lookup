import type { ButtonHTMLAttributes } from 'react';

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

export function PrimaryButton({ children, className = '', ...props }: PrimaryButtonProps) {
  return (
    <button
      className={`bg-(--color-primary) hover:bg-(--color-primary-dark) text-white font-medium py-3 px-6 rounded-lg transition-colors ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}