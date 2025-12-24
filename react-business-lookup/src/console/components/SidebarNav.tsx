import { Home, FileText, Search, Clock, Settings } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

const navItems = [
  { icon: Home, labelKey: 'nav.dashboard', active: false },
  { icon: FileText, labelKey: 'nav.invoices', active: true },
  { icon: Search, labelKey: 'nav.businessLookup', active: false },
  { icon: Clock, labelKey: 'nav.history', active: false },
  { icon: Settings, labelKey: 'nav.settings', active: false },
];

export function SidebarNav() {
  const { language } = useLanguage();

  return (
    <nav className="w-52 bg-dark-panel border-r border-dark-border flex flex-col">
      <div className="p-6 border-b border-dark-border">
        <div className="flex items-center gap-2">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-primary">
            <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2"/>
            <circle cx="12" cy="5" r="1.5" fill="currentColor"/>
            <circle cx="12" cy="19" r="1.5" fill="currentColor"/>
            <circle cx="5" cy="12" r="1.5" fill="currentColor"/>
            <circle cx="19" cy="12" r="1.5" fill="currentColor"/>
          </svg>
          <span className="text-lg font-semibold text-white">{t('nav.audosConsole', language)}</span>
        </div>
      </div>
      
      <div className="flex-1 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.labelKey}
              className={`w-full flex items-center gap-3 px-6 py-3 text-sm transition-colors ${
                item.active
                  ? 'bg-primary text-white'
                  : 'text-gray-400 hover:text-white hover:bg-dark-border'
              }`}
            >
              <Icon size={18} />
              <span>{t(item.labelKey, language)}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
