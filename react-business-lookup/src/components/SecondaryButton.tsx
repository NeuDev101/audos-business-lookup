import type { ButtonHTMLAttributes } from 'react';

interface SecondaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

export function SecondaryButton({ children, className = '', ...props }: SecondaryButtonProps) {
  return (
    <button
      className={`px-6 py-2.5 border border-(--color-border) text-(--color-text-primary) rounded-lg font-medium hover:bg-(--color-bg-card-hover) transition-colors ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}