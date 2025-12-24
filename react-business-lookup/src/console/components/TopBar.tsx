import { Search } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

export function TopBar() {
  const { language } = useLanguage();

  return (
    <header className="h-16 bg-dark-panel border-b border-dark-border flex items-center justify-between px-6">
      <h1 className="text-xl font-semibold text-white">{t('page.bulkValidation', language)}</h1>
      
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder={t('topbar.search', language)}
            aria-label={t('topbar.search', language)}
            className="w-64 pl-10 pr-4 py-2 bg-dark-bg border border-dark-border rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-primary"
          />
        </div>
        
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-orange-500" />
      </div>
    </header>
  );
}
