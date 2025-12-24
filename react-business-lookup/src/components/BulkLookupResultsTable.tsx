import { MoreHorizontal } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export interface BulkLookupResult {
  corporateNo: string;
  companyName: string;
  status: 'success' | 'warning' | 'error';
  lastChecked: string;
  error: string;
}

interface BulkLookupResultsTableProps {
  results: BulkLookupResult[];
}

export function BulkLookupResultsTable({ results }: BulkLookupResultsTableProps) {
  const { language } = useLanguage();

  const getStatusLabel = (status: 'success' | 'warning' | 'error') => {
    switch (status) {
      case 'success':
        return t('status.verified', language);
      case 'warning':
        return t('status.warning', language);
      case 'error':
        return t('status.error', language);
    }
  };

  return (
    <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border)">
      <h2 className="text-xl font-semibold text-white mb-6">{t('bulk.resultsTitle', language)}</h2>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-(--color-border)">
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.corporateNumberShort', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.companyName', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.status', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('bulk.lastChecked', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.error', language)}</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-(--color-text-secondary)">{t('common.actions', language)}</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result, index) => (
              <tr key={index} className="border-b border-(--color-border) hover:bg-(--color-bg-card-hover) transition-colors">
                <td className="py-3 px-4 text-sm text-(--color-text-primary)">{result.corporateNo}</td>
                <td className="py-3 px-4 text-sm text-(--color-text-primary)">{result.companyName}</td>
                <td className="py-3 px-4">
                  <StatusBadge status={result.status}>
                    {getStatusLabel(result.status)}
                  </StatusBadge>
                </td>
                <td className="py-3 px-4 text-sm text-(--color-text-primary)">{result.lastChecked}</td>
                <td className="py-3 px-4 text-sm text-(--color-text-muted)">{result.error}</td>
                <td className="py-3 px-4">
                  <button className="text-(--color-text-muted) hover:text-(--color-text-primary) transition-colors">
                    <MoreHorizontal size={20} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
