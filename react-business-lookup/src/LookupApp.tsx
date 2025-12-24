import { useEffect, useMemo, useState } from 'react';
import { Layout } from './components/Layout';
import { Tabs } from './components/Tabs';
import { BusinessLookupSinglePage } from './pages/BusinessLookupSinglePage';
import { BusinessLookupBulkPage } from './pages/BusinessLookupBulkPage';
import { useLanguage } from './contexts/LanguageContext';
import { t } from './lib/strings';

type LookupTab = 'single' | 'bulk';

interface LookupAppProps {
  initialTab?: LookupTab;
  activeNav?: 'dashboard' | 'business-lookup';
}

export function LookupApp({ initialTab = 'bulk', activeNav = 'business-lookup' }: LookupAppProps) {
  const [activeTab, setActiveTab] = useState<LookupTab>(initialTab);
  const { language } = useLanguage();

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const tabs = useMemo(
    () => [
      { id: 'single', label: t('lookup.tabs.single', language) },
      { id: 'bulk', label: t('lookup.tabs.bulkLong', language) },
    ],
    [language],
  );

  const handleTabChange = (tabId: string) => {
    setActiveTab(tabId as LookupTab);
  };

  return (
    <Layout activeNav={activeNav}>
      <div className="max-w-7xl">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white mb-2">{t('lookup.title', language)}</h1>
          <p className="text-(--color-text-secondary)">
            {t('lookup.subtitle', language)}
          </p>
        </div>

        <Tabs
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={handleTabChange}
        />

        {activeTab === 'single' ? (
          <BusinessLookupSinglePage hideTabs />
        ) : (
          <BusinessLookupBulkPage hideTabs />
        )}
      </div>
    </Layout>
  );
}
