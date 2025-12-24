import { useCallback, useMemo, useState } from 'react';
import { StatCard } from '../components/StatCard';
import { FileDropzone } from '../components/FileDropzone';
import { InvoiceTable, type InvoiceResultRow } from '../components/InvoiceTable';
import { IssuesPanel } from '../components/IssuesPanel';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';
import { getAuthHeader } from '../../lib/auth';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

interface BatchSummary {
  batch_id: string;
  counts: {
    pass?: number;
    fail?: number;
    warn?: number;
  };
  invoices: InvoiceResultRow[];
  zip_path?: string | null;
}

export function BulkInvoiceValidationPage() {
  const { language } = useLanguage();
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFilesSelected = useCallback(async (files: File[]) => {
    if (!files.length) {
      return;
    }
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    formData.append('language', language);

    try {
      const headers: HeadersInit = {};
      const authHeader = getAuthHeader();
      if (authHeader) {
        headers['Authorization'] = authHeader;
      }

      const response = await fetch(`${API_BASE_URL}/validate-invoices`, {
        method: 'POST',
        headers,
        body: formData,
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        const message = errorPayload.error || t('console.invoiceValidationFailed', language);
        throw new Error(message);
      }

      const data = (await response.json()) as BatchSummary;
      setBatchSummary(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : t('console.uploadFailed', language);
      setUploadError(message);
    } finally {
      setIsUploading(false);
    }
  }, [language]);

  const counts = batchSummary?.counts ?? { pass: 0, fail: 0, warn: 0 };
  const invoices = batchSummary?.invoices ?? [];

  const issueMessages = useMemo(() => {
    return invoices
      .filter((invoice) => invoice.error || (typeof invoice.issues === 'number' && invoice.issues > 0) || !invoice.compliant)
      .map((invoice) => {
        if (invoice.error) {
          return `${invoice.invoice_number || t('common.unknown', language)}: ${invoice.error}`;
        }
        return `${invoice.invoice_number || t('common.unknown', language)}: ${t('console.issueCount', language).replace('{count}', (invoice.issues ?? 0).toString())}`;
      });
  }, [invoices, language]);

  return (
    <div className="space-y-6">
      <FileDropzone onFilesSelected={handleFilesSelected} isUploading={isUploading} />

      {uploadError && (
        <div className="rounded-lg border border-error/40 bg-error/10 px-4 py-3 text-sm text-error">
          {uploadError}
        </div>
      )}

      <div className="grid grid-cols-4 gap-6">
        <StatCard label={t('page.totalFiles', language)} value={invoices.length} />
        <StatCard label={t('page.compliant', language)} value={counts.pass ?? 0} variant="success" />
        <StatCard label={t('page.needsReview', language)} value={counts.warn ?? 0} variant="warning" />
        <StatCard label={t('page.failed', language)} value={counts.fail ?? 0} variant="error" />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-dark-panel rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">{t('page.validationResults', language)}</h3>
              {batchSummary?.batch_id && (
                <p className="text-sm text-gray-400">{t('page.batchId', language)}: {batchSummary.batch_id}</p>
              )}
            </div>
            {batchSummary?.zip_path && (
              <a
                href={batchSummary.zip_path}
                className="text-sm text-primary hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                {t('page.downloadZip', language)}
              </a>
            )}
          </div>
          <InvoiceTable invoices={invoices} isLoading={isUploading} />
        </div>
        <div>
          <IssuesPanel issues={issueMessages} isUploading={isUploading} />
        </div>
      </div>
    </div>
  );
}
