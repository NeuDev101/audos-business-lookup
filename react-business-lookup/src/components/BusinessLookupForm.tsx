import { useState } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { PrimaryButton } from './PrimaryButton';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

interface BusinessLookupFormProps {
  onSubmit: (data: { corporateNumber: string; invoiceRegistrationNumber: string }) => void;
}

export function BusinessLookupForm({ onSubmit }: BusinessLookupFormProps) {
  const [corporateNumber, setCorporateNumber] = useState('');
  const [invoiceRegistrationNumber, setInvoiceRegistrationNumber] = useState('');
  const [corporateNumberError, setCorporateNumberError] = useState<string | null>(null);
  const { language } = useLanguage();

  const validateCorporateNumber = (value: string): string | null => {
    const trimmed = value.trim().replace(/[\s-]/g, '');
    if (!trimmed) {
      return t('validation.corporateNumberRequired', language);
    }
    if (!/^\d{13}$/.test(trimmed)) {
      return t('validation.corporateNumberLength', language);
    }
    return null;
  };

  const handleCorporateNumberChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/[\s-]/g, '');
    setCorporateNumber(value);
    const error = validateCorporateNumber(value);
    setCorporateNumberError(error);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = corporateNumber.trim().replace(/[\s-]/g, '');
    const error = validateCorporateNumber(trimmed);
    
    if (error) {
      setCorporateNumberError(error);
      return;
    }

    onSubmit({ 
      corporateNumber: trimmed, 
      invoiceRegistrationNumber: invoiceRegistrationNumber.trim() 
    });
  };

  const isCorporateNumberValid = corporateNumber.trim().replace(/[\s-]/g, '') && !corporateNumberError;

  return (
    <div className="bg-(--color-bg-card) rounded-lg p-6 border border-(--color-border)">
      <h2 className="text-2xl font-semibold text-white mb-6">{t('lookup.corporateNumberTitle', language)}</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="corporateNumber" className="block text-sm font-medium text-(--color-text-secondary) mb-2">
            {t('lookup.corporateNumberLabel', language)} <span className="text-red-500">*</span>
          </label>
          <div className="relative">
            <input
              type="text"
              id="corporateNumber"
              value={corporateNumber}
              onChange={handleCorporateNumberChange}
              maxLength={13}
              className="w-full bg-(--color-bg-dark) border border-(--color-border) rounded-lg px-4 py-3 pr-10 text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-primary)"
              placeholder={t('lookup.corporateNumberPlaceholder', language)}
            />
            {isCorporateNumberValid && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <CheckCircle2 size={18} className="text-green-500" />
              </div>
            )}
          </div>
          {corporateNumberError && (
            <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
              <XCircle size={12} />
              {corporateNumberError}
            </p>
          )}
          <p className="mt-1 text-xs text-(--color-text-muted)">
            {t('lookup.corporateNumberHelp', language)}
          </p>
        </div>

        <div>
          <label htmlFor="invoiceRegistrationNumber" className="block text-sm font-medium text-(--color-text-secondary) mb-2">
            {t('lookup.invoiceRegistrationNumber', language)}{' '}
            <span className="text-xs text-(--color-text-muted)">({t('common.optional', language)})</span>
          </label>
          <input
            type="text"
            id="invoiceRegistrationNumber"
            value={invoiceRegistrationNumber}
            onChange={(e) => setInvoiceRegistrationNumber(e.target.value)}
            className="w-full bg-(--color-bg-dark) border border-(--color-border) rounded-lg px-4 py-3 text-(--color-text-primary) placeholder:text-(--color-text-muted) focus:outline-none focus:border-(--color-primary)"
            placeholder={t('lookup.invoiceRegistrationNumber', language)}
          />
        </div>

        <PrimaryButton 
          type="submit" 
          className="w-full" 
          disabled={!isCorporateNumberValid}
        >
          {t('lookup.verifyBusiness', language)}
        </PrimaryButton>
      </form>
    </div>
  );
}
