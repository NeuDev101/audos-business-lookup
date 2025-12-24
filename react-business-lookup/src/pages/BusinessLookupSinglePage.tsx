import { useMemo, useState } from 'react';
import { Tabs } from '../components/Tabs';
import { BusinessLookupForm } from '../components/BusinessLookupForm';
import { RecentLookupsTable } from '../components/RecentLookupsTable';
import { LookupResultCard, type LookupResult } from '../components/LookupResultCard';
import { lookupSingle, type SingleLookupResult } from '../lib/api';
import { useLanguage, type Language } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

// Convert API response to component format
function mapApiResultToLookupResult(apiResult: SingleLookupResult, language: Language): LookupResult {
  const status: 'success' | 'warning' | 'error' = apiResult.error 
    ? 'error' 
    : (apiResult.registration_status === 'active' ? 'success' : 'warning');
  
  return {
    companyName: apiResult.name || t('common.notAvailable', language),
    corporateNumber: apiResult.business_id || t('common.notAvailable', language),
    address: apiResult.address || t('common.notAvailable', language),
    status,
    lastUpdated: apiResult.timestamp || new Date().toISOString(),
  };
}

interface BusinessLookupSinglePageProps {
  hideTabs?: boolean;
}

export function BusinessLookupSinglePage({ hideTabs = false }: BusinessLookupSinglePageProps) {
  const [result, setResult] = useState<LookupResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const { language } = useLanguage();

  const tabs = useMemo(
    () => [
      { id: 'single', label: t('lookup.tabs.single', language) },
      { id: 'bulk', label: t('lookup.tabs.bulk', language) },
    ],
    [language],
  );

  const handleLookupSubmit = async (data: { corporateNumber: string; invoiceRegistrationNumber: string }) => {
    const businessId = data.corporateNumber.trim();
    
    // Clear previous errors
    setError(null);
    setFormError(null);
    setResult(null);

    // Form validation should already be handled by BusinessLookupForm
    // But double-check here as well
    if (!businessId || !/^\d{13}$/.test(businessId)) {
      setFormError(t('validation.corporateNumberLength', language));
      return;
    }

    setLoading(true);

    try {
      const apiResult = await lookupSingle(businessId);
      const mappedResult = mapApiResultToLookupResult(apiResult, language);
      setResult(mappedResult);
      setError(null);
    } catch (err) {
      // Handle backend errors (400, 404, etc.)
      let errorMessage = t('lookup.lookupFailed', language);
      if (err instanceof Error) {
        errorMessage = err.message;
      }
      setError(errorMessage);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Tabs - only show if not hidden (for standalone use) */}
      {!hideTabs && (
        <Tabs tabs={tabs} activeTab="single" onTabChange={() => {}} />
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        {/* Left: Lookup Form */}
        <BusinessLookupForm onSubmit={handleLookupSubmit} />

        {/* Right: Recent Lookups Table - show empty state until real data is available */}
        <RecentLookupsTable lookups={[]} />
      </div>

      {/* Form Validation Error */}
      {formError && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-red-500/40 mb-6">
          <p className="text-red-500">{t('common.error', language)}: {formError}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border) mb-6">
          <p className="text-(--color-text-secondary)">{t('lookup.loading', language)}</p>
        </div>
      )}

      {/* Backend Error State */}
      {error && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-red-500/40 mb-6">
          <p className="text-red-500">{t('common.error', language)}: {error}</p>
        </div>
      )}

      {/* Result Card */}
      {result && <LookupResultCard result={result} />}
    </>
  );
}
