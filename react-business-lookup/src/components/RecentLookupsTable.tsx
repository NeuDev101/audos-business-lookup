import { StatusBadge } from './StatusBadge';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export interface RecentLookup {
  companyName: string;
  corporateNo: string;
  status: 'success' | 'warning' | 'error';
}

interface RecentLookupsTableProps {
  lookups: RecentLookup[];
}

export function RecentLookupsTable({ lookups }: RecentLookupsTableProps) {
  const { language } = useLanguage();

  return (
    <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border)">
      <h2 className="text-xl font-semibold text-white mb-6">{t('recentLookups.title', language)}</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-(--color-border)">
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.companyName', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.corporateNumberShort', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.status', language)}</th>
            </tr>
          </thead>
          <tbody>
            {lookups.map((lookup, index) => (
              <tr key={index} className="border-b border-(--color-border) hover:bg-(--color-bg-card-hover) transition-colors">
                <td className="py-3 px-4 text-sm text-(--color-text-primary)">{lookup.companyName}</td>
                <td className="py-3 px-4 text-sm text-(--color-text-primary)">{lookup.corporateNo}</td>
                <td className="py-3 px-4">
                  <StatusBadge status={lookup.status}>
                    {lookup.status === 'success'
                      ? t('status.success', language)
                      : lookup.status === 'warning'
                        ? t('status.warning', language)
                        : t('status.error', language)}
                  </StatusBadge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
