import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

// Check if demo mode is enabled (same logic as AuthContext)
const DEMO_MODE = 
  import.meta.env.VITE_DEMO_MODE === 'true' || 
  import.meta.env.VITE_DEMO_MODE === '1' ||
  import.meta.env.VITE_DISABLE_AUTH === 'true' ||
  import.meta.env.VITE_DISABLE_AUTH === '1';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const { language } = useLanguage();

  if (isLoading) {
    // Show loading state while checking auth
    return <div className="flex items-center justify-center min-h-screen">{t('common.loading', language)}</div>;
  }

  // In demo mode, always allow access
  if (DEMO_MODE) {
    return <>{children}</>;
  }

  if (!isAuthenticated) {
    // Redirect to login if not authenticated
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
