interface StatCardProps {
  label: string;
  value: number;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

export function StatCard({ label, value, variant = 'default' }: StatCardProps) {
  const colorMap = {
    default: 'text-white',
    success: 'text-success',
    warning: 'text-warning',
    error: 'text-error',
  };

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm text-gray-400">{label}</span>
      <span className={`text-3xl font-semibold ${colorMap[variant]}`}>
        {value}
      </span>
    </div>
  );
}