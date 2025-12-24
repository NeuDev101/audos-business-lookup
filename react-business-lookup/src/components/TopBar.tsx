import { Search, User, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export function TopBar() {
  const authDisabled = true;
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { language, setLanguage } = useLanguage();

  const handleLogout = () => {
    logout();
    navigate('/dashboard');
  };

  return (
    <header className="bg-(--color-bg-card) border-b border-(--color-border) px-8 py-4">
      <div className="flex items-center justify-between">
        <div className="flex-1 max-w-xl">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-(--color-text-muted)" size={20} />
            <input
              type="text"
              placeholder={t('topbar.search', language)}
              className="w-full bg-(--color-bg-dark) border border-(--color-border) rounded-lg pl-10 pr-4 py-2 text-sm text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-primary)"
              aria-label={t('topbar.search', language)}
            />
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Language Toggle */}
          <div className="flex items-center gap-2 bg-(--color-bg-dark) rounded-lg p-1 border border-(--color-border)">
            <button
              onClick={() => setLanguage('en')}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                language === 'en'
                  ? 'bg-(--color-primary) text-white'
                  : 'text-(--color-text-secondary) hover:text-(--color-text-primary)'
              }`}
            >
              EN
            </button>
            <button
              onClick={() => setLanguage('ja')}
              className={`px-3 py-1 text-sm font-medium rounded transition-colors ${
                language === 'ja'
                  ? 'bg-(--color-primary) text-white'
                  : 'text-(--color-text-secondary) hover:text-(--color-text-primary)'
              }`}
            >
              JA
            </button>
          </div>
          
          {(user || authDisabled) && (
            <span className="text-sm text-gray-400">{user?.email || 'demo@audos.local'}</span>
          )}
          {!authDisabled && (
            <button
              onClick={handleLogout}
              className="ml-6 w-10 h-10 bg-(--color-primary) rounded-full flex items-center justify-center hover:bg-(--color-primary-dark) transition-colors"
              title="Logout"
            >
              <LogOut size={20} className="text-white" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
