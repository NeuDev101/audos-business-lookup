import { useMemo, useState, useEffect } from 'react';
import { Layout } from '../components/Layout';
import { StatusBadge } from '../components/StatusBadge';
import { SecondaryButton } from '../components/SecondaryButton';
import { getHistory, type InvoiceHistoryItem } from '../lib/historyApi';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export function HistoryPage() {
  const [statusFilter, setStatusFilter] = useState<'all' | 'pass' | 'fail'>('all');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [invoices, setInvoices] = useState<InvoiceHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const { language } = useLanguage();

  useEffect(() => {
    const fetchHistory = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const filters: any = {
          page,
          per_page: 50,
        };
        if (statusFilter !== 'all') {
          filters.status = statusFilter;
        }
        if (startDate) {
          filters.start_date = startDate;
        }
        if (endDate) {
          filters.end_date = endDate;
        }
        const response = await getHistory(filters);
        setInvoices(response.invoices);
        setTotalPages(response.pagination.pages);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load history');
      } finally {
        setIsLoading(false);
      }
    };
    fetchHistory();
  }, [statusFilter, startDate, endDate, page]);

  return (
    <Layout activeNav="history">
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{t('history.title', language)}</h1>
          <p className="text-(--color-text-secondary)">{t('history.subtitle', language)}</p>
        </div>

        <section className="bg-(--color-bg-card) rounded-xl border border-(--color-border)/40 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-white">{t('history.filters', language)}</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">{t('common.status', language)}</label>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="w-full bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-3 py-2 text-sm text-white"
              >
                <option value="all">{t('common.all', language)}</option>
                <option value="pass">{t('status.pass', language)}</option>
                <option value="fail">{t('status.fail', language)}</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">{t('history.dateRange', language)}</label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="flex-1 bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-3 py-2 text-sm text-white"
                />
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="flex-1 bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-3 py-2 text-sm text-white"
                />
              </div>
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <SecondaryButton
              className="text-sm"
              onClick={() => {
                setStatusFilter('all');
                setStartDate('');
                setEndDate('');
                setPage(1);
              }}
            >
              {t('common.reset', language)}
            </SecondaryButton>
          </div>
        </section>

        <section className="bg-(--color-bg-card) rounded-xl border border-(--color-border)/40">
          <div className="flex items-center justify-between px-6 py-4 border-b border-(--color-border)/40">
            <h2 className="text-lg font-semibold text-white">{t('history.sectionTitle', language)}</h2>
            <SecondaryButton className="text-sm px-4 py-2">{t('history.exportCsv', language)}</SecondaryButton>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-400">
                  <th className="py-3 px-6 font-medium">{t('history.dateTime', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('history.invoiceNumber', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('page.batchId', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('common.status', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('history.issues', language)}</th>
                  <th className="py-3 px-6 font-medium">{t('history.link', language)}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-gray-400">
                      {t('common.loading', language)}
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-red-400">
                      {error}
                    </td>
                  </tr>
                ) : invoices.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-6 text-center text-gray-400">
                      {t('history.noInvoices', language)}
                    </td>
                  </tr>
                ) : (
                  invoices.map((invoice) => (
                    <tr key={invoice.id} className="border-t border-(--color-border)/30">
                      <td className="px-6 py-4 text-sm text-white">
                        {new Date(invoice.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">{invoice.invoice_number}</td>
                      <td className="px-6 py-4 text-sm text-gray-300">{invoice.batch_id || '-'}</td>
                      <td className="px-6 py-4 text-sm">
                        <StatusBadge status={invoice.status === 'fail' ? 'error' : 'success'}>
                          {invoice.status === 'fail' ? t('status.fail', language) : t('status.pass', language)}
                        </StatusBadge>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">{invoice.issues_count}</td>
                      <td className="px-6 py-4 text-sm">
                        {invoice.pdf_path ? (
                          <a
                            href={invoice.pdf_path}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-(--color-primary) hover:underline"
                          >
                            {t('history.viewPdf', language)}
                          </a>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-4 border-t border-(--color-border)/40">
              <div className="text-sm text-gray-400">
                {t('history.pageOf', language)
                  .replace('{current}', page.toString())
                  .replace('{total}', totalPages.toString())}
              </div>
              <div className="flex gap-2">
                <SecondaryButton
                  className="text-sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  {t('common.previous', language)}
                </SecondaryButton>
                <SecondaryButton
                  className="text-sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  {t('common.next', language)}
                </SecondaryButton>
              </div>
            </div>
          )}
        </section>
      </div>
    </Layout>
  );
}
