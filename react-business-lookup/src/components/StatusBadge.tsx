type StatusType = 'success' | 'warning' | 'error';

interface StatusBadgeProps {
  status: StatusType;
  children: React.ReactNode;
}

export function StatusBadge({ status, children }: StatusBadgeProps) {
  const statusStyles = {
    success: 'bg-green-500/10 text-green-500',
    warning: 'bg-amber-500/10 text-amber-500',
    error: 'bg-red-500/10 text-red-500',
  };

  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${statusStyles[status]}`}>
      {children}
    </span>
  );
}