import { useState } from 'react';
import { ManualInvoiceForm } from '../components/ManualInvoiceForm';
import { InvoicePreviewPanel } from '../components/InvoicePreviewPanel';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

interface ValidationResult {
  compliant: boolean;
  issues_count: number;
  issues: string[];
  normalized: {
    invoice_number?: string;
    issuer_name?: string;
    buyer?: string;
    date?: string;
    items?: Array<{ amount_excl_tax: number; tax_rate?: string }>;
    remarks?: string;
  };
  status: string;
  pdfUrl?: string;
  remarks?: string;
  formData?: {
    sellerName: string;
    sellerRegNo: string;
    sellerAddress: string;
    buyerName: string;
    buyerAddress: string;
    invoiceDate: string;
    dueDate: string;
    invoiceNo: string;
    items: Array<{
      description: string;
      qty: number;
      unitPrice: number;
      taxRate: string;
      amount: number;
    }>;
  };
}

export function ManualInvoiceEntryPage() {
  const { language } = useLanguage();
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | undefined>(undefined);

  const handleValidated = (result: ValidationResult) => {
    setValidationResult({
      ...result,
      normalized: {
        ...result.normalized,
        remarks: result.remarks,
      },
    });
    setPdfUrl(result.pdfUrl);
  };

  const calculateTotals = () => {
    if (!validationResult?.normalized?.items) {
      return { subtotal: 0, taxTotal: 0, grandTotal: 0 };
    }

    let subtotal = 0;
    let taxTotal = 0;

    validationResult.normalized.items.forEach((item: any) => {
      const amount = item.amount_excl_tax || 0;
      subtotal += amount;

      const taxRateStr = item.tax_rate || '0%';
      const taxRateNum = parseFloat(taxRateStr.replace('%', ''));
      taxTotal += (amount * taxRateNum) / 100;
    });

    const grandTotal = subtotal + taxTotal;

    return {
      subtotal: Math.round(subtotal * 100) / 100,
      taxTotal: Math.round(taxTotal * 100) / 100,
      grandTotal: Math.round(grandTotal * 100) / 100,
    };
  };

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <h1 className="text-2xl font-semibold text-white">{t('page.manualInvoice', language)}</h1>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <ManualInvoiceForm onValidated={handleValidated} />
        </div>
        <div>
          <InvoicePreviewPanel
            status={validationResult ? (validationResult.compliant ? 'compliant' : 'needs_review') : undefined}
            issues={validationResult?.issues}
            pdfUrl={pdfUrl}
            invoiceSummary={
              validationResult && validationResult.formData
                ? {
                    invoice_number: validationResult.formData.invoiceNo || validationResult.normalized.invoice_number,
                    issuer_name: validationResult.formData.sellerName || validationResult.normalized.issuer_name,
                    buyer: validationResult.formData.buyerName || validationResult.normalized.buyer,
                    invoice_date: validationResult.formData.invoiceDate || validationResult.normalized.date,
                    due_date: validationResult.formData.dueDate,
                    remarks: validationResult.normalized.remarks || validationResult.remarks,
                    items: validationResult.formData.items,
                    issuer_id: validationResult.formData.sellerRegNo,
                    seller_address: validationResult.formData.sellerAddress,
                    ...calculateTotals(),
                  }
                : validationResult
                ? {
                    invoice_number: validationResult.normalized.invoice_number,
                    issuer_name: validationResult.normalized.issuer_name,
                    buyer: validationResult.normalized.buyer,
                    invoice_date: validationResult.normalized.date,
                    remarks: validationResult.normalized.remarks || validationResult.remarks,
                    ...calculateTotals(),
                  }
                : undefined
            }
          />
        </div>
      </div>
    </div>
  );
}
