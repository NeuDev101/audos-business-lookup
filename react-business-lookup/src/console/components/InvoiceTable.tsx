import { StatusBadge } from './StatusBadge';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

export interface InvoiceResultRow {
  invoice_number?: string;
  status?: string;
  compliant?: boolean;
  issues?: number;
  pdf_path?: string | null;
  pdf_sha256?: string | null;
  error?: string;
}

interface InvoiceTableProps {
  invoices: InvoiceResultRow[];
  isLoading?: boolean;
}

export function InvoiceTable({ invoices, isLoading = false }: InvoiceTableProps) {
  const { language } = useLanguage();

  const getStatusVariant = (
    invoice: InvoiceResultRow,
  ): { variant: 'success' | 'warning' | 'error'; label: string } => {
    if (invoice.error) {
      return { variant: 'error', label: t('common.error', language) };
    }
    if (invoice.status === 'warn') {
      return { variant: 'warning', label: t('console.review', language) };
    }
    if (invoice.status === 'pass' || invoice.compliant) {
      return { variant: 'success', label: t('page.compliant', language) };
    }
    return { variant: 'error', label: t('status.failed', language) };
  };

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-dark-border">
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">{t('console.invoiceNumberShort', language)}</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">{t('common.status', language)}</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">{t('history.issues', language)}</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">{t('history.link', language)}</th>
            <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">{t('console.notes', language)}</th>
          </tr>
        </thead>
        <tbody>
          {isLoading && (
            <tr>
              <td colSpan={5} className="py-6 px-4 text-center text-gray-400">
                {t('console.uploadingValidating', language)}
              </td>
            </tr>
          )}
          {!isLoading && invoices.length === 0 && (
            <tr>
              <td colSpan={5} className="py-6 px-4 text-center text-gray-500">
                {t('console.uploadInvoicesPrompt', language)}
              </td>
            </tr>
          )}
          {!isLoading &&
            invoices.map((invoice, index) => {
              const { variant, label } = getStatusVariant(invoice);
              const rowKey = invoice.invoice_number || invoice.pdf_sha256 || `invoice-${index}`;
              return (
                <tr key={rowKey} className="border-b border-dark-border hover:bg-dark-panel/50">
                  <td className="py-3 px-4 text-sm text-white">{invoice.invoice_number || t('common.unknown', language)}</td>
                  <td className="py-3 px-4 text-sm">
                    <StatusBadge status={variant} label={label} />
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-300">
                    {typeof invoice.issues === 'number'
                      ? t('console.issueCount', language).replace('{count}', invoice.issues.toString())
                      : '—'}
                  </td>
                  <td className="py-3 px-4 text-sm">
                    {invoice.pdf_path ? (
                      <a href={invoice.pdf_path} className="text-primary hover:underline" target="_blank" rel="noreferrer">
                        {t('history.viewPdf', language)}
                      </a>
                    ) : (
                      <span className="text-gray-500">{t('console.pending', language)}</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-sm text-gray-300">
                    {invoice.error
                      ? invoice.error
                      : invoice.compliant
                        ? t('console.readyForExport', language)
                        : t('page.needsReview', language)}
                  </td>
                </tr>
              );
            })}
        </tbody>
      </table>
    </div>
  );
}
