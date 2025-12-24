import { StatusBadge } from './StatusBadge';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export interface LookupResult {
  companyName: string;
  corporateNumber: string;
  address: string;
  status: 'success' | 'warning' | 'error';
  lastUpdated: string;
}

interface LookupResultCardProps {
  result: LookupResult | null;
}

export function LookupResultCard({ result }: LookupResultCardProps) {
  const { language } = useLanguage();

  if (!result) {
    return null;
  }

  return (
    <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border)">
      <h2 className="text-xl font-semibold text-white mb-6">{t('lookup.result', language)}</h2>
      
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="text-sm text-(--color-text-secondary) mb-1">{t('common.companyName', language)}</p>
          <p className="text-base text-(--color-text-primary)">{result.companyName}</p>
        </div>
        
        <div>
          <p className="text-sm text-(--color-text-secondary) mb-1">{t('common.corporateNumber', language)}</p>
          <p className="text-base text-(--color-text-primary)">{result.corporateNumber}</p>
        </div>
        
        <div className="col-span-2">
          <p className="text-sm text-(--color-text-secondary) mb-1">{t('common.address', language)}</p>
          <p className="text-base text-(--color-text-primary)">{result.address}</p>
        </div>
        
        <div>
          <p className="text-sm text-(--color-text-secondary) mb-1">{t('common.status', language)}</p>
          <StatusBadge status={result.status}>
            {result.status === 'success'
              ? t('status.success', language)
              : result.status === 'warning'
                ? t('status.warning', language)
                : t('status.error', language)}
          </StatusBadge>
        </div>
        
        <div>
          <p className="text-sm text-(--color-text-secondary) mb-1">{t('lookup.lastUpdated', language)}</p>
          <p className="text-base text-(--color-text-primary)">{result.lastUpdated}</p>
        </div>
      </div>
    </div>
  );
}
