interface StatCardProps {
  label: string;
  value: number;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

export function StatCard({ label, value, variant = 'default' }: StatCardProps) {
  const variantStyles = {
    default: 'text-(--color-text-primary)',
    success: 'text-green-500',
    warning: 'text-amber-500',
    error: 'text-red-500',
  };

  return (
    <div className="flex flex-col">
      <span className="text-sm text-(--color-text-secondary) mb-2">{label}</span>
      <span className={`text-3xl font-semibold ${variantStyles[variant]}`}>
        {value}
      </span>
    </div>
  );
}