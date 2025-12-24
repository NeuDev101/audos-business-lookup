import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, Building2, History, Settings } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

interface NavItem {
  id: string;
  labelKey: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  path: string;
}

const navItems: NavItem[] = [
  { id: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, path: '/dashboard' },
  { id: 'invoices', labelKey: 'nav.invoices', icon: FileText, path: '/console' },
  { id: 'business-lookup', labelKey: 'nav.businessLookup', icon: Building2, path: '/bulk' },
  { id: 'history', labelKey: 'nav.history', icon: History, path: '/history' },
  { id: 'settings', labelKey: 'nav.settings', icon: Settings, path: '/settings' },
];

interface SidebarNavProps {
  activeItem?: string;
}

export function SidebarNav({ activeItem }: SidebarNavProps) {
  const { language } = useLanguage();
  
  return (
    <nav className="w-64 bg-(--color-bg-card) border-r border-(--color-border) h-screen flex flex-col">
      <div className="p-6 border-b border-(--color-border)">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 bg-(--color-primary) rounded-full"></div>
          <h1 className="text-xl font-semibold text-white">{t('nav.audosConsole', language)}</h1>
        </div>
      </div>
      
      <div className="flex-1 p-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => {
                const navIsActive = activeItem ? item.id === activeItem : isActive;
                return `w-full flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                  navIsActive
                    ? 'bg-(--color-primary) text-white'
                    : 'text-(--color-text-secondary) hover:bg-(--color-bg-card-hover)'
                }`;
              }}
              aria-current={activeItem && item.id === activeItem ? 'page' : undefined}
            >
              <Icon size={20} />
              <span className="font-medium">{t(item.labelKey, language)}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}