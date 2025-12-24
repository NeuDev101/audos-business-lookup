import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InvoicePreviewPanel } from '../InvoicePreviewPanel';
import { LanguageProvider } from '../../../contexts/LanguageContext';
import { t } from '../../../lib/strings';

describe('InvoicePreviewPanel', () => {
  it('renders empty state when no invoice summary provided', () => {
    render(
      <LanguageProvider>
        <InvoicePreviewPanel />
      </LanguageProvider>,
    );
    expect(screen.getByText(t('console.enterDetails', 'ja'))).toBeInTheDocument();
  });

  it('displays invoice data when summary is provided', () => {
    const invoiceSummary = {
      invoice_number: 'INV-001',
      issuer_name: 'Test Company',
      buyer: 'Customer Inc',
      invoice_date: '2024-01-15',
      subtotal: 1000,
      taxTotal: 100,
      grandTotal: 1100,
      items: [
        { description: 'Product A', qty: 1, unitPrice: 1000, taxRate: '10%', amount: 1000 },
      ],
    };

    render(
      <LanguageProvider>
        <InvoicePreviewPanel invoiceSummary={invoiceSummary} status="compliant" />
      </LanguageProvider>,
    );
    
    expect(screen.getAllByText(/INVOICE/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/INV-001/i)).toBeInTheDocument();
    expect(screen.getByText(/Test Company/i)).toBeInTheDocument();
    expect(screen.getByText(/Customer Inc/i)).toBeInTheDocument();
    expect(screen.getByText(/Product A/i)).toBeInTheDocument();
    expect(screen.getByText(/¥1,100.00/i)).toBeInTheDocument();
  });

  it('displays compliance status badge', () => {
    render(
      <LanguageProvider>
        <InvoicePreviewPanel status="compliant" />
      </LanguageProvider>,
    );
    expect(screen.getByText(t('page.compliant', 'ja'))).toBeInTheDocument();
  });

  it('displays issues when present', () => {
    const issues = ['Missing required field: invoice_number', 'Invalid date format'];
    render(
      <LanguageProvider>
        <InvoicePreviewPanel status="needs_review" issues={issues} />
      </LanguageProvider>,
    );
    
    expect(screen.getByText(t('console.detectedIssues', 'ja'))).toBeInTheDocument();
    expect(screen.getByText(/Missing required field/i)).toBeInTheDocument();
    expect(screen.getByText(/Invalid date format/i)).toBeInTheDocument();
  });

  it('displays line items table when items are provided', () => {
    const invoiceSummary = {
      invoice_number: 'INV-001',
      issuer_name: 'Test Company',
      buyer: 'Customer Inc',
      items: [
        { description: 'Item 1', qty: 2, unitPrice: 500, taxRate: '10%', amount: 1000 },
        { description: 'Item 2', qty: 1, unitPrice: 300, taxRate: '8%', amount: 300 },
      ],
      subtotal: 1300,
      taxTotal: 124,
      grandTotal: 1424,
    };

    render(
      <LanguageProvider>
        <InvoicePreviewPanel invoiceSummary={invoiceSummary} />
      </LanguageProvider>,
    );
    
    expect(screen.getByText(/Item 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Item 2/i)).toBeInTheDocument();
    expect(screen.getAllByText('2', { selector: 'td' }).length).toBeGreaterThan(0); // Quantity cell
    expect(screen.getByText(/¥500.00/i)).toBeInTheDocument(); // Unit price
  });
});
