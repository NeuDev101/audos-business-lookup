import { useEffect, useMemo } from 'react';
import { matchPath, useLocation, useNavigate } from 'react-router-dom';
import { ManualInvoiceEntryPage } from './console/pages/ManualInvoiceEntryPage';
import { BulkInvoiceValidationPage } from './console/pages/BulkInvoiceValidationPage';
import { Layout } from './components/Layout';
import { Tabs } from './components/Tabs';
import { useLanguage } from './contexts/LanguageContext';
import { t } from './lib/strings';

type ConsoleView = 'manual' | 'bulk';

export function ConsoleApp() {
  const { language } = useLanguage();
  
  useEffect(() => {
    document.body.classList.add('console-body');
    return () => {
      document.body.classList.remove('console-body');
    };
  }, []);

  const location = useLocation();
  const navigate = useNavigate();
  const isBulkRoute = Boolean(matchPath('/console/bulk', location.pathname));
  const activeView: ConsoleView = isBulkRoute ? 'bulk' : 'manual';

  const tabs = useMemo(
    () => [
      { id: 'manual', label: t('tab.manual', language) },
      { id: 'bulk', label: t('tab.bulk', language) },
    ],
    [language],
  );

  const handleTabChange = (tabId: string) => {
    const nextView = tabId === 'bulk' ? 'bulk' : 'manual';
    if (nextView === activeView) {
      return;
    }
    navigate(nextView === 'bulk' ? '/console/bulk' : '/console/manual');
  };

  return (
    <Layout activeNav="invoices">
      <Tabs tabs={tabs} activeTab={activeView} onTabChange={handleTabChange} />
      {activeView === 'manual' ? <ManualInvoiceEntryPage /> : <BulkInvoiceValidationPage />}
    </Layout>
  );
}

