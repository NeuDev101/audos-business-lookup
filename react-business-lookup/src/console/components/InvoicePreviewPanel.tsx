import { StatusBadge } from './StatusBadge';
import { PrimaryButton } from './PrimaryButton';
import { Download } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

interface InvoicePreviewPanelProps {
  status?: 'compliant' | 'needs_review';
  issues?: string[];
  pdfUrl?: string;
  invoiceSummary?: {
    invoice_number?: string;
    issuer_name?: string;
    buyer?: string;
    subtotal?: number;
    taxTotal?: number;
    grandTotal?: number;
    invoice_date?: string;
    due_date?: string;
    remarks?: string;
    items?: Array<{
      description: string;
      qty: number;
      unitPrice: number;
      taxRate: string;
      amount?: number;
    }>;
    issuer_id?: string;
    seller_address?: string;
    seller_phone?: string;
    seller_email?: string;
  };
}

export function InvoicePreviewPanel({
  status,
  issues = [],
  pdfUrl,
  invoiceSummary,
}: InvoicePreviewPanelProps) {
  const { language } = useLanguage();
  const hasIssues = issues.length > 0;
  const isCompliant = status === 'compliant';

  const formatCurrency = (value: number) =>
    `¥${value.toLocaleString('ja-JP', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // TODO: Show real PDF preview when PDF generation is implemented

  return (
    <div className="bg-dark-panel rounded-lg p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">{t('console.invoicePreview', language)}</h2>
        {status && (
          <StatusBadge
            status={isCompliant ? 'success' : hasIssues ? 'warning' : 'error'}
            label={isCompliant ? t('page.compliant', language) : t('page.needsReview', language)}
          />
        )}
      </div>

      {/* Invoice Preview */}
      {invoiceSummary ? (
        <div className="bg-white rounded-lg p-6 space-y-4 border border-gray-200 shadow-sm">
          {/* Header */}
          <div className="text-right border-b border-gray-300 pb-3">
            <h3 className="text-2xl font-bold text-gray-900">請求書 / INVOICE</h3>
            {invoiceSummary.invoice_number && (
              <p className="text-sm text-gray-600 mt-1">
                請求番号 / Invoice No.: {invoiceSummary.invoice_number}
              </p>
            )}
            {invoiceSummary.invoice_date && (
              <p className="text-sm text-gray-600">
                発行日 / Issue Date: {invoiceSummary.invoice_date}
              </p>
            )}
          </div>

          {/* Seller Section */}
          {invoiceSummary.issuer_name && (
            <div className="space-y-2 border-b border-gray-200 pb-4">
              <h4 className="text-sm font-semibold text-gray-700">請求元 / Seller</h4>
              <div className="text-sm text-gray-900 space-y-1">
                <p className="font-medium">{invoiceSummary.issuer_name}</p>
                {invoiceSummary.issuer_id && (
                  <p className="text-gray-600">登録番号 / Registration No.: {invoiceSummary.issuer_id}</p>
                )}
                {invoiceSummary.seller_address && (
                  <p className="text-gray-600">{invoiceSummary.seller_address}</p>
                )}
                {(invoiceSummary.seller_phone || invoiceSummary.seller_email) && (
                  <p className="text-gray-600">
                    {invoiceSummary.seller_phone && `電話 / Phone: ${invoiceSummary.seller_phone}`}
                    {invoiceSummary.seller_phone && invoiceSummary.seller_email && ' | '}
                    {invoiceSummary.seller_email && `メール / Email: ${invoiceSummary.seller_email}`}
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Buyer Section */}
          {invoiceSummary.buyer && (
            <div className="space-y-2 border-b border-gray-200 pb-4">
              <h4 className="text-sm font-semibold text-gray-700">請求先 / Buyer</h4>
              <p className="text-sm text-gray-900">{invoiceSummary.buyer} 御中</p>
            </div>
          )}

          {/* Line Items Table */}
          {invoiceSummary.items && invoiceSummary.items.length > 0 && (
            <div className="border-b border-gray-200 pb-4">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-300 bg-gray-50">
                    <th className="text-left py-2 px-2 font-semibold text-gray-700">品目 / Description</th>
                    <th className="text-right py-2 px-2 font-semibold text-gray-700">数量 / Qty</th>
                    <th className="text-right py-2 px-2 font-semibold text-gray-700">単価 / Unit Price</th>
                    <th className="text-right py-2 px-2 font-semibold text-gray-700">金額 / Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {invoiceSummary.items.map((item, idx) => {
                    const amount = item.amount || (item.qty * item.unitPrice);
                    return (
                      <tr key={idx} className="border-b border-gray-100">
                        <td className="py-2 px-2 text-gray-900">{item.description}</td>
                        <td className="py-2 px-2 text-right text-gray-700">
                          {item.qty === Math.floor(item.qty)
                            ? item.qty.toLocaleString('ja-JP')
                            : item.qty.toLocaleString('ja-JP', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2 px-2 text-right text-gray-700">
                          {formatCurrency(item.unitPrice)}
                        </td>
                        <td className="py-2 px-2 text-right text-gray-900 font-medium">
                          {formatCurrency(amount)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Totals section */}
          {invoiceSummary.grandTotal !== undefined && (
            <div className="space-y-2 pt-2">
              {invoiceSummary.subtotal !== undefined && (
                <div className="flex justify-between text-sm text-gray-700">
                  <span>小計 / Subtotal</span>
                  <span>{formatCurrency(invoiceSummary.subtotal)}</span>
                </div>
              )}
              {invoiceSummary.taxTotal !== undefined && (
                <div className="flex justify-between text-sm text-gray-700">
                  <span>税額 / Tax</span>
                  <span>{formatCurrency(invoiceSummary.taxTotal)}</span>
                </div>
              )}
              <div className="flex justify-between text-base font-bold pt-2 border-t-2 border-gray-400 text-gray-900">
                <span>合計 / Total</span>
                <span>{formatCurrency(invoiceSummary.grandTotal)}</span>
              </div>
            </div>
          )}

          {/* Remarks */}
          {invoiceSummary.remarks && (
            <div className="pt-4 border-t border-gray-200">
              <p className="text-xs font-semibold text-gray-600 mb-1">備考 / Notes</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{invoiceSummary.remarks}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-dark-bg rounded-lg p-6 space-y-4">
          <div className="text-center text-gray-400 text-sm">
            {t('console.enterDetails', language)}
          </div>
        </div>
      )}

      {/* Detected Issues */}
      {status && (
        <div className="space-y-4">
          <h3 className="text-base font-semibold text-white">{t('console.detectedIssues', language)}</h3>
          {hasIssues ? (
            <ul className="space-y-3">
              {issues.map((issue, index) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-300">
                  <span className="w-2 h-2 rounded-full bg-error mt-1.5 flex-shrink-0" />
                  <span>{t('console.issuePrefix', language)} {issue}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">{t('console.noIssues', language)}</p>
          )}
        </div>
      )}

      {/* PDF Preview */}
      {pdfUrl && (
        <div className="space-y-4">
          <h3 className="text-base font-semibold text-white">{t('console.pdfPreview', language)}</h3>
          <div className="w-full border border-dark-border rounded-lg overflow-hidden bg-dark-bg">
            <iframe
              src={pdfUrl}
              className="w-full"
              style={{ height: '500px' }}
              title={t('console.pdfPreview', language)}
            />
          </div>
        </div>
      )}

      {/* PDF Download Button */}
      {pdfUrl && (
        <div className="pt-4 border-t border-dark-border">
          <a
            href={pdfUrl}
            download={`invoice_${invoiceSummary?.invoice_number || 'invoice'}.pdf`}
            className="block"
          >
            <PrimaryButton className="w-full flex items-center justify-center gap-2">
              <Download size={16} />
              {t('console.downloadPdf', language)}
            </PrimaryButton>
          </a>
        </div>
      )}
    </div>
  );
}
