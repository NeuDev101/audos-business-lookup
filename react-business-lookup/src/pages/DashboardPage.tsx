import { Link } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { StatCard } from '../components/StatCard';
import { StatusBadge } from '../components/StatusBadge';
import { PrimaryButton } from '../components/PrimaryButton';
import { SecondaryButton } from '../components/SecondaryButton';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

// TODO: Replace with real data from backend API
const stats = [
  { labelKey: 'dashboard.totalLookups', value: 0 },
  { labelKey: 'dashboard.successRate', value: 0, variant: 'success' as const },
  { labelKey: 'dashboard.recentValidations', value: 0 },
  { labelKey: 'dashboard.errors', value: 0, variant: 'error' as const },
];

// TODO: Replace with real data from backend API
const recentActivity: any[] = [];

export function DashboardPage() {
  const { language } = useLanguage();

  return (
    <Layout activeNav="dashboard">
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">{t('dashboard.title', language)}</h1>
            <p className="text-(--color-text-secondary)">{t('dashboard.subtitle', language)}</p>
          </div>
          <div className="flex gap-3">
            <Link to="/console/bulk">
              <PrimaryButton>{t('dashboard.startBulk', language)}</PrimaryButton>
            </Link>
            <Link to="/single">
              <SecondaryButton>{t('lookup.tabs.single', language)}</SecondaryButton>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-6">
          {stats.map((stat) => (
            <div key={stat.labelKey} className="bg-(--color-bg-card) rounded-xl p-6 border border-(--color-border)/40">
              <StatCard label={t(stat.labelKey, language)} value={stat.value} variant={stat.variant} />
            </div>
          ))}
        </div>

        <section className="bg-(--color-bg-card) rounded-xl border border-(--color-border)/40">
          <div className="flex items-center justify-between px-6 py-4 border-b border-(--color-border)/40">
            <h2 className="text-lg font-semibold text-white">{t('dashboard.recentActivity', language)}</h2>
            <SecondaryButton className="text-sm px-4 py-2">{t('dashboard.viewAll', language)}</SecondaryButton>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-400">
                  <th className="py-3 px-6 font-medium">{t('dashboard.time', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('dashboard.type', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('dashboard.identifier', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('common.status', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('common.action', language)}</th>
                </tr>
              </thead>
              <tbody>
                {recentActivity.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-6 text-center text-gray-400">
                      {t('dashboard.noData', language)}
                    </td>
                  </tr>
                ) : (
                  recentActivity.map((activity) => (
                    <tr key={activity.identifier} className="border-t border-(--color-border)/30">
                      <td className="px-6 py-4 text-sm text-white">{activity.timestamp}</td>
                      <td className="px-6 py-4 text-sm text-gray-300">{activity.type}</td>
                      <td className="px-6 py-4 text-sm text-gray-300">{activity.identifier}</td>
                      <td className="px-6 py-4 text-sm">
                        <StatusBadge status={activity.status === 'error' ? 'error' : 'success'}>
                          {activity.status === 'error' ? t('status.failed', language) : t('status.success', language)}
                        </StatusBadge>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <button className="text-(--color-primary) hover:underline" type="button">
                          {t('dashboard.viewDetails', language)}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="bg-(--color-bg-card) rounded-xl border border-(--color-border)/40 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">{t('dashboard.quickActions', language)}</h2>
          <div className="grid grid-cols-3 gap-4">
            <Link to="/single" className="bg-(--color-bg-card-hover) rounded-lg p-4 border border-(--color-border)/30 hover:border-(--color-primary)">
              <h3 className="text-white font-medium mb-1">{t('lookup.tabs.single', language)}</h3>
              <p className="text-sm text-gray-400">{t('dashboard.quickSingle', language)}</p>
            </Link>
            <Link to="/bulk" className="bg-(--color-bg-card-hover) rounded-lg p-4 border border-(--color-border)/30 hover:border-(--color-primary)">
              <h3 className="text-white font-medium mb-1">{t('lookup.tabs.bulk', language)}</h3>
              <p className="text-sm text-gray-400">{t('dashboard.quickBulk', language)}</p>
            </Link>
            <Link to="/console/bulk" className="bg-(--color-bg-card-hover) rounded-lg p-4 border border-(--color-border)/30 hover:border-(--color-primary)">
              <h3 className="text-white font-medium mb-1">{t('dashboard.quickConsole', language)}</h3>
              <p className="text-sm text-gray-400">{t('dashboard.quickConsoleDetail', language)}</p>
            </Link>
          </div>
        </section>
      </div>
    </Layout>
  );
}
