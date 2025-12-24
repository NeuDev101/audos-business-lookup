import { useMemo, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { Tabs } from '../components/Tabs';
import { FileDropzone } from '../components/FileDropzone';
import { StatCard } from '../components/StatCard';
import { SecondaryButton } from '../components/SecondaryButton';
import { BulkLookupResultsTable, type BulkLookupResult } from '../components/BulkLookupResultsTable';
import { lookupCsv, type BulkLookupResult as ApiBulkResult } from '../lib/api';
import { useLanguage, type Language } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

// Convert API response to component format
function mapApiResultsToBulkResults(apiResults: ApiBulkResult[], language: Language): BulkLookupResult[] {
  return apiResults.map((apiResult) => {
    const status: 'success' | 'warning' | 'error' = apiResult.error 
      ? 'error' 
      : (apiResult.registration_status === 'active' ? 'success' : 'warning');
    
    return {
      corporateNo: apiResult.business_id || t('common.notAvailable', language),
      companyName: apiResult.name || t('common.notAvailable', language),
      status,
      lastChecked: apiResult.timestamp || new Date().toISOString(),
      error: apiResult.error || '',
    };
  });
}

interface BusinessLookupBulkPageProps {
  hideTabs?: boolean;
}

export function BusinessLookupBulkPage({ hideTabs = false }: BusinessLookupBulkPageProps) {
  const [results, setResults] = useState<BulkLookupResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const { language } = useLanguage();

  const tabs = useMemo(
    () => [
      { id: 'single', label: t('lookup.tabs.single', language) },
      { id: 'bulk', label: t('lookup.tabs.bulk', language) },
    ],
    [language],
  );

  const handleFileError = (message: string) => {
    if (message) {
      setFileError(message);
    } else {
      setFileError(null);
    }
  };

  const handleFileSelect = async (file: File) => {
    // Prevent upload if there's a file validation error
    if (fileError) {
      return;
    }

    // Clear previous errors
    setError(null);
    setFileError(null);
    setResults([]);

    setLoading(true);

    try {
      const response = await lookupCsv(file);
      const mappedResults = mapApiResultsToBulkResults(response.results, language);
      setResults(mappedResults);
      setError(null);
      
      // Show validation errors if present
      if (response.errors && response.errors.length > 0) {
        const errorMessages = response.errors.map(
          (e) =>
            `${t('bulk.rowLabel', language)} ${e.row || '?'}: ${e.business_id || t('common.notAvailable', language)} - ${e.error}`,
        );
        setError(`${t('bulk.validationErrorsFound', language)}: ${errorMessages.join('; ')}`);
      }
    } catch (err) {
      let errorMessage = t('bulk.csvProcessingFailed', language);
      if (err instanceof Error) {
        errorMessage = err.message;
      }
      setError(errorMessage);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = async () => {
    if (results.length === 0) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/download/results.csv`);
      if (!response.ok) {
        if (response.status === 404) {
          setError(t('bulk.noResultsToDownload', language));
        } else {
          setError(`${t('common.downloadFailed', language)}: ${response.statusText}`);
        }
        return;
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'results.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Download failed';
      setError(errorMessage);
    }
  };

  const handleDownloadPDFs = async () => {
    if (results.length === 0) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/download/zip`);
      if (!response.ok) {
        if (response.status === 404) {
          setError(t('bulk.noResultsToDownload', language));
        } else {
          setError(`${t('common.downloadFailed', language)}: ${response.statusText}`);
        }
        return;
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'audos_lookup_results.zip';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : t('common.downloadFailed', language);
      setError(errorMessage);
    }
  };

  const hasResults = results.length > 0;

  return (
    <>
      {/* Tabs - only show if not hidden (for standalone use) */}
      {!hideTabs && (
        <Tabs tabs={tabs} activeTab="bulk" onTabChange={() => {}} />
      )}

      {/* File Upload Section */}
      <div className="mb-6">
        <FileDropzone onFileSelect={handleFileSelect} onError={handleFileError} />
      </div>

      {/* File Validation Error */}
      {fileError && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-red-500/40 mb-6">
          <p className="text-red-500">{t('common.error', language)}: {fileError}</p>
        </div>
      )}

      {/* Stats and Download Buttons */}
      {hasResults && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border) mb-6">
          <div className="grid grid-cols-4 gap-8 mb-6">
            <StatCard label={t('bulk.totalRows', language)} value={results.length} />
            <StatCard 
              label={t('bulk.verified', language)} 
              value={results.filter(r => r.status === 'success').length} 
              variant="success" 
            />
            <StatCard 
              label={t('bulk.warnings', language)} 
              value={results.filter(r => r.status === 'warning').length} 
              variant="warning" 
            />
            <StatCard 
              label={t('bulk.errors', language)} 
              value={results.filter(r => r.status === 'error').length} 
              variant="error" 
            />
          </div>

          <div className="flex gap-4">
            <SecondaryButton onClick={handleDownloadCSV} disabled={!hasResults}>
              {t('bulk.downloadResultCsv', language)}
            </SecondaryButton>
            <SecondaryButton 
              onClick={handleDownloadPDFs} 
              className="flex items-center gap-2"
              disabled={!hasResults}
            >
              {t('bulk.downloadPdfs', language)}
              <ChevronRight size={16} />
            </SecondaryButton>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border) mb-6">
          <p className="text-(--color-text-secondary)">{t('bulk.processingCsv', language)}</p>
        </div>
      )}

      {/* Backend Error State */}
      {error && (
        <div className="bg-(--color-bg-card) rounded-lg p-6 border border-red-500/40 mb-6">
          <p className="text-red-500">{t('common.error', language)}: {error}</p>
        </div>
      )}

      {/* Results Table */}
      {hasResults && <BulkLookupResultsTable results={results} />}
    </>
  );
}
