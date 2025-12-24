import { useState, useMemo, useCallback, useEffect, useRef, type ReactNode } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { PrimaryButton } from './PrimaryButton';
import { LineItemsTable, type LineItem } from './LineItemsTable';
import { getAuthHeader } from '../../lib/auth';
import { useLanguage } from '../../contexts/LanguageContext';
import { t } from '../../lib/strings';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5000';

// Debounce delay for field validation (ms)
const VALIDATION_DEBOUNCE_MS = 500;

type ValidationStatus = 'pending' | 'validating' | 'valid' | 'invalid';

interface ManualInvoiceFormProps {
  onValidated: (result: {
    compliant: boolean;
    issues_count: number;
    issues: string[];
    normalized: any;
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
  }) => void;
}

interface FormErrors {
  sellerName?: string;
  sellerRegNo?: string;
  sellerAddress?: string;
  buyerName?: string;
  buyerAddress?: string;
  invoiceDate?: string;
  dueDate?: string;
  invoiceNo?: string;
  remarks?: string;
  items?: string;
  totals?: string;
}

interface SectionValidity {
  seller: boolean;
  buyer: boolean;
  invoiceDetails: boolean;
  lineItems: boolean;
  totals: boolean;
}

interface FieldWrapperProps {
  name: string;
  label: string;
  children: ReactNode;
  required?: boolean;
  error?: string;
  validationStatus?: ValidationStatus;
  value: string;
  touched: boolean;
}

const FieldWrapper = ({
  name,
  label,
  children,
  required = true,
  error,
  validationStatus,
  value,
  touched,
}: FieldWrapperProps) => {
  const hasNonEmptyValue = value.trim() !== '';
  const shouldShowFeedback = touched || hasNonEmptyValue;
  const isPending = validationStatus === 'pending' || validationStatus === 'validating';
  const isFieldValid = !error && (validationStatus === 'valid' || validationStatus === undefined);
  const showCheckmark = required
    ? shouldShowFeedback && hasNonEmptyValue && isFieldValid && !isPending
    : shouldShowFeedback && isFieldValid && !isPending;
  const showError = shouldShowFeedback && Boolean(error);

  return (
    <div>
      <label htmlFor={name} className="block text-sm text-gray-400 mb-2">
        {label} {required && <span className="text-error">*</span>}
      </label>
      <div className="relative">
        {children}
        {showCheckmark && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <CheckCircle2 size={18} className="text-success" />
          </div>
        )}
      </div>
      {showError && (
        <p className="mt-1 text-xs text-error flex items-center gap-1">
          <XCircle size={12} />
          {error}
        </p>
      )}
    </div>
  );
};

interface SectionWrapperProps {
  title: string;
  isValid: boolean;
  children: ReactNode;
}

const SectionWrapper = ({ title, isValid, children }: SectionWrapperProps) => {
  const { language } = useLanguage();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-white">{title}</h3>
        {isValid && (
          <div className="flex items-center gap-2 text-success">
            <CheckCircle2 size={18} />
            <span className="text-xs">{t('form.valid', language)}</span>
          </div>
        )}
      </div>
      {children}
    </div>
  );
};

export function ManualInvoiceForm({ onValidated }: ManualInvoiceFormProps) {
  const { language } = useLanguage();
  
  // Seller fields
  const [sellerName, setSellerName] = useState('');
  const [sellerRegNo, setSellerRegNo] = useState('');
  const [sellerAddress, setSellerAddress] = useState('');

  // Buyer fields
  const [buyerName, setBuyerName] = useState('');
  const [buyerAddress, setBuyerAddress] = useState('');

  // Invoice details
  const [invoiceDate, setInvoiceDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [invoiceNo, setInvoiceNo] = useState('');
  const [remarks, setRemarks] = useState('');

  // Line items - taxRate stored as number (0, 8, or 10)
  const [items, setItems] = useState<LineItem[]>([
    { description: '', qty: 1, unitPrice: 0, taxRate: 10 },
  ]);

  // Form state
  const [errors, setErrors] = useState<FormErrors>({});
  const [fieldValidationStatus, setFieldValidationStatus] = useState<Record<string, ValidationStatus>>({});
  const [touchedFields, setTouchedFields] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Debounce timers for field validation
  const validationTimers = useRef<Record<string, NodeJS.Timeout>>({});

  // Map backend field names back to UI field names
  const getUIFieldName = useCallback((backendFieldName: string): string => {
    const mapping: Record<string, string> = {
      issuer_name: 'sellerName',
      issuer_id: 'sellerRegNo',
      address: 'sellerAddress',
      buyer: 'buyerName',
      date: 'invoiceDate',
      invoice_number: 'invoiceNo',
    };
    return mapping[backendFieldName] || backendFieldName;
  }, []);

  // Validate a single field using the backend validator (debounced)
  // Only fires when field has non-empty value
  const validateFieldWithBackend = useCallback(async (fieldName: string, fieldValue: any) => {
    // Don't validate empty values
    if (!fieldValue || (typeof fieldValue === 'string' && !fieldValue.trim())) {
      return;
    }

    // Clear existing timer for this field
    if (validationTimers.current[fieldName]) {
      clearTimeout(validationTimers.current[fieldName]);
    }

    // Set status to pending
    setFieldValidationStatus((prev) => ({ ...prev, [fieldName]: 'pending' }));

    // Debounce the actual API call
    validationTimers.current[fieldName] = setTimeout(async () => {
      setFieldValidationStatus((prev) => ({ ...prev, [fieldName]: 'validating' }));

      try {
        const response = await fetch(`${API_BASE_URL}/validate_field`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            field: fieldName,
            value: fieldValue,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.error || 'Validation failed';
          const uiFieldName = getUIFieldName(fieldName);
          setErrors((prev) => ({ ...prev, [uiFieldName]: errorMessage }));
          setFieldValidationStatus((prev) => ({ ...prev, [fieldName]: 'invalid' }));
          return false;
        }

        const result = await response.json();
        const isValid = result.status === 'pass';
        setFieldValidationStatus((prev) => ({ ...prev, [fieldName]: isValid ? 'valid' : 'invalid' }));
        
        const uiFieldName = getUIFieldName(fieldName);
        
        // Clear error if field is now valid
        if (isValid) {
          setErrors((prev) => ({ ...prev, [uiFieldName]: undefined }));
        } else {
          // Extract error message from validation result - try multiple possible structures
          let errorMessage = 'Validation failed';
          if (result.messages) {
            const messages = result.messages;
            if (typeof messages === 'string') {
              errorMessage = messages;
            } else if (messages.en && Array.isArray(messages.en) && messages.en.length > 0) {
              errorMessage = messages.en[0];
            } else if (messages.en && typeof messages.en === 'string') {
              errorMessage = messages.en;
            } else if (Array.isArray(messages) && messages.length > 0) {
              errorMessage = messages[0];
            }
          } else if (result.message) {
            errorMessage = result.message;
          } else if (result.error) {
            errorMessage = result.error;
          }
          setErrors((prev) => ({ ...prev, [uiFieldName]: errorMessage }));
        }
        
        return isValid;
      } catch (error) {
        const uiFieldName = getUIFieldName(fieldName);
        setErrors((prev) => ({ ...prev, [uiFieldName]: t('validation.requestFailed', language) }));
        setFieldValidationStatus((prev) => ({ ...prev, [fieldName]: 'invalid' }));
        return false;
      }
    }, VALIDATION_DEBOUNCE_MS);
  }, [getUIFieldName, language]);

  // Mark field as touched
  const markFieldTouched = useCallback((fieldName: string) => {
    setTouchedFields((prev) => ({ ...prev, [fieldName]: true }));
  }, []);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      Object.values(validationTimers.current).forEach((timer) => {
        if (timer) clearTimeout(timer);
      });
    };
  }, []);

  // Map UI field names to backend validation field names
  const getBackendFieldName = useCallback((uiFieldName: string): string => {
    const mapping: Record<string, string> = {
      sellerName: 'issuer_name',
      sellerRegNo: 'issuer_id',
      sellerAddress: 'address',
      buyerName: 'buyer',
      invoiceDate: 'date',
      invoiceNo: 'invoice_number',
    };
    return mapping[uiFieldName] || uiFieldName;
  }, []);

  // Get validation status for a UI field by mapping to backend field name
  const getFieldValidationStatus = useCallback((uiFieldName: string): ValidationStatus | undefined => {
    const backendFieldName = getBackendFieldName(uiFieldName);
    return fieldValidationStatus[backendFieldName];
  }, [fieldValidationStatus, getBackendFieldName]);

  // Local validation helpers
  const validateRequired = (value: string): string | undefined => {
    if (!value.trim()) return t('validation.required', language);
    return undefined;
  };

  const validateDate = (value: string): string | undefined => {
    if (!value.trim()) return t('validation.dateRequired', language);
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    if (!dateRegex.test(value)) return t('validation.dateFormat', language);
    const date = new Date(value);
    if (isNaN(date.getTime())) return t('validation.invalidDate', language);
    return undefined;
  };

  const validateSellerRegNo = (value: string): string | undefined => {
    if (!value.trim()) return t('validation.sellerRegistrationRequired', language);
    const normalized = value.replace(/\D/g, '');
    if (normalized.length !== 13) return t('validation.corporateNumberLength', language);
    return undefined;
  };

  // Computed totals
  const totals = useMemo(() => {
    let subtotal = 0;
    let taxTotal = 0;

    items.forEach((item) => {
      const lineAmount = item.qty * item.unitPrice;
      subtotal += lineAmount;
      taxTotal += (lineAmount * item.taxRate) / 100;
    });

    const grandTotal = subtotal + taxTotal;

    return {
      subtotal: Math.round(subtotal * 100) / 100,
      taxTotal: Math.round(taxTotal * 100) / 100,
      grandTotal: Math.round(grandTotal * 100) / 100,
    };
  }, [items]);

  // Validate items (accepts items array as parameter to avoid stale closure)
  const validateItems = useCallback((itemsToValidate: LineItem[]): string | undefined => {
    if (itemsToValidate.length === 0) return t('validation.lineItemRequired', language);
    for (let i = 0; i < itemsToValidate.length; i++) {
      const item = itemsToValidate[i];
      const itemLabel = t('validation.itemLabel', language).replace('{index}', (i + 1).toString());
      if (!item.description.trim()) return `${itemLabel} ${t('validation.itemDescription', language)}`;
      if (item.qty <= 0) return `${itemLabel} ${t('validation.itemQuantity', language)}`;
      if (item.unitPrice < 0) return `${itemLabel} ${t('validation.itemUnitPrice', language)}`;
      if (![0, 8, 10].includes(item.taxRate)) {
        return `${itemLabel} ${t('validation.itemTaxRate', language)}`;
      }
    }
    return undefined;
  }, [language]);

  // Section-level validation
  const sectionValidity = useMemo<SectionValidity>(() => {
    const sellerValid =
      sellerName.trim() !== '' &&
      !errors.sellerName &&
      sellerRegNo.trim() !== '' &&
      !errors.sellerRegNo &&
      sellerAddress.trim() !== '' &&
      !errors.sellerAddress &&
      getFieldValidationStatus('sellerName') !== 'invalid' &&
      getFieldValidationStatus('sellerRegNo') !== 'invalid' &&
      getFieldValidationStatus('sellerAddress') !== 'invalid';

    const buyerValid =
      buyerName.trim() !== '' &&
      !errors.buyerName &&
      buyerAddress.trim() !== '' &&
      !errors.buyerAddress &&
      getFieldValidationStatus('buyerName') !== 'invalid';

    const invoiceDetailsValid =
      invoiceDate.trim() !== '' &&
      !errors.invoiceDate &&
      invoiceNo.trim() !== '' &&
      !errors.invoiceNo &&
      getFieldValidationStatus('invoiceDate') !== 'invalid' &&
      getFieldValidationStatus('invoiceNo') !== 'invalid';

    // Validate line items using validateItems helper
    const lineItemsError = validateItems(items);
    const lineItemsValid =
      items.length > 0 &&
      !lineItemsError &&
      items.every(
        (item) =>
          item.description.trim() !== '' &&
          item.qty > 0 &&
          item.unitPrice >= 0 &&
          [0, 8, 10].includes(item.taxRate)
      );

    const totalsValid = !errors.totals && items.length > 0;

    return {
      seller: sellerValid,
      buyer: buyerValid,
      invoiceDetails: invoiceDetailsValid,
      lineItems: lineItemsValid,
      totals: totalsValid,
    };
  }, [
    sellerName,
    sellerRegNo,
    sellerAddress,
    buyerName,
    buyerAddress,
    invoiceDate,
    invoiceNo,
    items,
    errors,
    getFieldValidationStatus,
  ]);

  // Handle field changes with validation (only show errors if touched or has value)
  // Backend validation only happens on blur to reduce churn
  const handleSellerNameChange = (value: string) => {
    setSellerName(value);
    const isTouched = touchedFields.sellerName;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) ? validateRequired(value) : undefined;
    setErrors((prev) => ({ ...prev, sellerName: error }));
    // Backend validation moved to blur handler only
  };

  const handleSellerNameBlur = () => {
    markFieldTouched('sellerName');
    const error = validateRequired(sellerName);
    setErrors((prev) => ({ ...prev, sellerName: error }));
    if (!error && sellerName.trim()) {
      validateFieldWithBackend('issuer_name', sellerName);
    }
  };

  const handleSellerRegNoChange = (value: string) => {
    const digitsOnly = value.replace(/\D/g, '');
    setSellerRegNo(digitsOnly);
    const isTouched = touchedFields.sellerRegNo;
    const hasValue = digitsOnly.trim() !== '';
    const error = (isTouched || hasValue) ? validateSellerRegNo(digitsOnly) : undefined;
    setErrors((prev) => ({ ...prev, sellerRegNo: error }));
    // Backend validation moved to blur handler only
  };

  const handleSellerRegNoBlur = () => {
    markFieldTouched('sellerRegNo');
    const error = validateSellerRegNo(sellerRegNo);
    setErrors((prev) => ({ ...prev, sellerRegNo: error }));
    if (!error && sellerRegNo.length === 13) {
      validateFieldWithBackend('issuer_id', `T${sellerRegNo}`);
    }
  };

  const handleSellerAddressChange = (value: string) => {
    setSellerAddress(value);
    const isTouched = touchedFields.sellerAddress;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) ? validateRequired(value) : undefined;
    setErrors((prev) => ({ ...prev, sellerAddress: error }));
    // Backend validation moved to blur handler only
  };

  const handleSellerAddressBlur = () => {
    markFieldTouched('sellerAddress');
    const error = validateRequired(sellerAddress);
    setErrors((prev) => ({ ...prev, sellerAddress: error }));
    if (!error && sellerAddress.trim()) {
      validateFieldWithBackend('address', sellerAddress);
    }
  };

  const handleBuyerNameChange = (value: string) => {
    setBuyerName(value);
    const isTouched = touchedFields.buyerName;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) ? validateRequired(value) : undefined;
    setErrors((prev) => ({ ...prev, buyerName: error }));
    // Backend validation moved to blur handler only
  };

  const handleBuyerNameBlur = () => {
    markFieldTouched('buyerName');
    const error = validateRequired(buyerName);
    setErrors((prev) => ({ ...prev, buyerName: error }));
    if (!error && buyerName.trim()) {
      validateFieldWithBackend('buyer', buyerName);
    }
  };

  const handleBuyerAddressChange = (value: string) => {
    setBuyerAddress(value);
    const isTouched = touchedFields.buyerAddress;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) ? validateRequired(value) : undefined;
    setErrors((prev) => ({ ...prev, buyerAddress: error }));
  };

  const handleBuyerAddressBlur = () => {
    markFieldTouched('buyerAddress');
    const error = validateRequired(buyerAddress);
    setErrors((prev) => ({ ...prev, buyerAddress: error }));
  };

  const handleInvoiceDateChange = (value: string) => {
    setInvoiceDate(value);
    const isTouched = touchedFields.invoiceDate;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) ? validateDate(value) : undefined;
    setErrors((prev) => ({ ...prev, invoiceDate: error }));
    // Backend validation moved to blur handler only
  };

  const handleInvoiceDateBlur = () => {
    markFieldTouched('invoiceDate');
    const error = validateDate(invoiceDate);
    setErrors((prev) => ({ ...prev, invoiceDate: error }));
    if (!error && invoiceDate.trim()) {
      validateFieldWithBackend('date', invoiceDate);
    }
  };

  const handleDueDateChange = (value: string) => {
    setDueDate(value);
    const isTouched = touchedFields.dueDate;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) && value.trim() ? validateDate(value) : undefined;
    setErrors((prev) => ({ ...prev, dueDate: error }));
  };

  const handleDueDateBlur = () => {
    markFieldTouched('dueDate');
    const error = dueDate.trim() ? validateDate(dueDate) : undefined;
    setErrors((prev) => ({ ...prev, dueDate: error }));
  };

  const handleInvoiceNoChange = (value: string) => {
    setInvoiceNo(value);
    const isTouched = touchedFields.invoiceNo;
    const hasValue = value.trim() !== '';
    const error = (isTouched || hasValue) ? validateRequired(value) : undefined;
    setErrors((prev) => ({ ...prev, invoiceNo: error }));
    // Backend validation moved to blur handler only
  };

  const handleInvoiceNoBlur = () => {
    markFieldTouched('invoiceNo');
    const error = validateRequired(invoiceNo);
    setErrors((prev) => ({ ...prev, invoiceNo: error }));
    if (!error && invoiceNo.trim()) {
      validateFieldWithBackend('invoice_number', invoiceNo);
    }
  };

  const handleRemarksChange = (value: string) => {
    setRemarks(value);
    // Remarks is optional, so no validation needed
    setErrors((prev) => ({ ...prev, remarks: undefined }));
  };

  const handleItemsChange = (newItems: LineItem[]) => {
    setItems(newItems);
    // Validate with newItems array (not stale items state)
    const itemError = validateItems(newItems);
    setErrors((prev) => ({ ...prev, items: itemError }));
  };

  // Overall form validity
  const formIsValid = useMemo(() => {
    return (
      sectionValidity.seller &&
      sectionValidity.buyer &&
      sectionValidity.invoiceDetails &&
      sectionValidity.lineItems &&
      sectionValidity.totals &&
      Object.values(errors).every((err) => !err)
    );
  }, [sectionValidity, errors]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);

    // Mark all fields as touched on submit to show validation feedback
    setTouchedFields({
      sellerName: true,
      sellerRegNo: true,
      sellerAddress: true,
      buyerName: true,
      buyerAddress: true,
      invoiceDate: true,
      dueDate: true,
      invoiceNo: true,
      remarks: true,
    });

    // Re-validate all fields now that they're touched
    const sellerNameError = validateRequired(sellerName);
    const sellerRegNoError = validateSellerRegNo(sellerRegNo);
    const sellerAddressError = validateRequired(sellerAddress);
    const buyerNameError = validateRequired(buyerName);
    const buyerAddressError = validateRequired(buyerAddress);
    const invoiceDateError = validateDate(invoiceDate);
    const invoiceNoError = validateRequired(invoiceNo);
    const dueDateError = dueDate.trim() ? validateDate(dueDate) : undefined;

    setErrors({
      sellerName: sellerNameError,
      sellerRegNo: sellerRegNoError,
      sellerAddress: sellerAddressError,
      buyerName: buyerNameError,
      buyerAddress: buyerAddressError,
      invoiceDate: invoiceDateError,
      invoiceNo: invoiceNoError,
      dueDate: dueDateError,
    });

    // Final validation (use current items state)
    const itemError = validateItems(items);
    if (itemError) {
      setErrors((prev) => ({ ...prev, items: itemError }));
      setSubmitError('Please fix validation errors before submitting');
      return;
    }

    if (!formIsValid) {
      setSubmitError('Please fix validation errors before submitting');
      return;
    }

    setIsSubmitting(true);

    try {
      // Build payload matching backend expectations
      // Backend expects: sellerName, sellerRegNo, sellerAddress, buyerName, buyerAddress,
      // invoiceDate, dueDate, invoiceNo, remarks, items[], totals{}, language
      // Items expect taxRate as string with "%" (e.g., "10%")
      const payload = {
        sellerName,
        sellerRegNo,
        sellerAddress,
        buyerName,
        buyerAddress,
        invoiceDate,
        dueDate: dueDate || undefined,
        invoiceNo,
        remarks: remarks || undefined,
        language,
        items: items.map((item) => ({
          description: item.description.trim(),
          qty: item.qty,
          unitPrice: item.unitPrice,
          taxRate: `${item.taxRate}%`, // Format as string with "%" for backend
        })),
        totals: {
          subtotal: totals.subtotal,
          taxTotal: totals.taxTotal,
          grandTotal: totals.grandTotal,
        },
      };

      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      const authHeader = getAuthHeader();
      if (authHeader) {
        headers['Authorization'] = authHeader;
      }

      const response = await fetch(`${API_BASE_URL}/manual-invoice/validate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        // Extract error message - could be a string or array of details
        let errorMessage = errorData.error || `Validation failed: ${response.statusText}`;
        if (errorData.details && Array.isArray(errorData.details) && errorData.details.length > 0) {
          // Show first error detail if available
          errorMessage = errorData.details[0];
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();
      
      // Check if validation result has issues and surface them
      if (result.issues && Array.isArray(result.issues) && result.issues.length > 0) {
        // Surface first issue as submit error
        setSubmitError(result.issues[0]);
      }
      
      // After successful validation, generate PDF
      setIsGeneratingPdf(true);
      let pdfUrl: string | undefined;
      try {
        const pdfHeaders: HeadersInit = {
          'Content-Type': 'application/json',
        };
        const pdfAuthHeader = getAuthHeader();
        if (pdfAuthHeader) {
          pdfHeaders['Authorization'] = pdfAuthHeader;
        }

        const pdfResponse = await fetch(`${API_BASE_URL}/manual-invoice/generate`, {
          method: 'POST',
          headers: pdfHeaders,
          body: JSON.stringify(payload),
        });

        if (pdfResponse.ok) {
          const pdfBlob = await pdfResponse.blob();
          pdfUrl = URL.createObjectURL(pdfBlob);
        } else {
          const errorData = await pdfResponse.json().catch(() => ({}));
          const pdfError = errorData.error || 'PDF generation failed';
          console.warn('PDF generation failed:', pdfError);
          setSubmitError(pdfError);
          // Don't fail the whole flow if PDF generation fails, but show error
        }
      } catch (pdfError) {
        const errorMessage = pdfError instanceof Error ? pdfError.message : 'PDF generation error';
        console.warn('PDF generation error:', errorMessage);
        setSubmitError(errorMessage);
        // Don't fail the whole flow if PDF generation fails
      } finally {
        setIsGeneratingPdf(false);
      }
      
      onValidated({
        ...result,
        pdfUrl,
        remarks: remarks || undefined,
        formData: {
          sellerName,
          sellerRegNo,
          sellerAddress,
          buyerName,
          buyerAddress,
          invoiceDate,
          dueDate,
          invoiceNo,
          items: items.map(item => ({
            description: item.description,
            qty: item.qty,
            unitPrice: item.unitPrice,
            taxRate: `${item.taxRate}%`,
            amount: item.qty * item.unitPrice,
          })),
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Validation request failed';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Helper to get field value by name
  const getFieldValue = useCallback((fieldName: string): string => {
    const fieldMap: Record<string, string> = {
      sellerName,
      sellerRegNo,
      sellerAddress,
      buyerName,
      buyerAddress,
      invoiceDate,
      dueDate,
      invoiceNo,
      remarks,
    };
    return fieldMap[fieldName] || '';
  }, [sellerName, sellerRegNo, sellerAddress, buyerName, buyerAddress, invoiceDate, dueDate, invoiceNo, remarks]);

  // Initialize invoice date to today
  useEffect(() => {
    if (!invoiceDate) {
      const today = new Date().toISOString().split('T')[0];
      setInvoiceDate(today);
    }
  }, []);

  return (
    <div className="bg-dark-panel rounded-lg p-6">
      <h2 className="text-lg font-semibold text-white mb-6">{t('page.manualInvoice', language)}</h2>

      {submitError && (
        <div className="mb-4 p-3 rounded-lg border border-error/40 bg-error/10 text-sm text-error">
          {submitError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Seller Information */}
        <SectionWrapper title={t('form.sellerInfo', language)} isValid={sectionValidity.seller}>
          <FieldWrapper
            name="sellerName"
            label={t('form.sellerName', language)}
            error={errors.sellerName}
            validationStatus={getFieldValidationStatus('sellerName')}
            value={getFieldValue('sellerName')}
            touched={Boolean(touchedFields.sellerName)}
          >
            <input
              id="sellerName"
              type="text"
              value={sellerName}
              onChange={(e) => handleSellerNameChange(e.target.value)}
              onBlur={handleSellerNameBlur}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
            />
          </FieldWrapper>

          <div className="grid grid-cols-2 gap-4">
            <FieldWrapper
              name="sellerRegNo"
              label={t('form.sellerRegNo', language)}
              error={errors.sellerRegNo}
              validationStatus={getFieldValidationStatus('sellerRegNo')}
              value={getFieldValue('sellerRegNo')}
              touched={Boolean(touchedFields.sellerRegNo)}
            >
              <input
                id="sellerRegNo"
                type="text"
                value={sellerRegNo}
                onChange={(e) => handleSellerRegNoChange(e.target.value)}
                onBlur={handleSellerRegNoBlur}
                maxLength={13}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
            <FieldWrapper
              name="sellerAddress"
              label={t('form.sellerAddress', language)}
              error={errors.sellerAddress}
              validationStatus={getFieldValidationStatus('sellerAddress')}
              value={getFieldValue('sellerAddress')}
              touched={Boolean(touchedFields.sellerAddress)}
            >
              <input
                id="sellerAddress"
                type="text"
                value={sellerAddress}
                onChange={(e) => handleSellerAddressChange(e.target.value)}
                onBlur={handleSellerAddressBlur}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
          </div>
        </SectionWrapper>

        {/* Buyer Information */}
        <SectionWrapper title={t('form.buyerInfo', language)} isValid={sectionValidity.buyer}>
          <div className="grid grid-cols-2 gap-4">
            <FieldWrapper
              name="buyerName"
              label={t('form.buyerName', language)}
              error={errors.buyerName}
              validationStatus={getFieldValidationStatus('buyerName')}
              value={getFieldValue('buyerName')}
              touched={Boolean(touchedFields.buyerName)}
            >
              <input
                id="buyerName"
                type="text"
                value={buyerName}
                onChange={(e) => handleBuyerNameChange(e.target.value)}
                onBlur={handleBuyerNameBlur}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
            <FieldWrapper
              name="buyerAddress"
              label={t('form.buyerAddress', language)}
              error={errors.buyerAddress}
              validationStatus={getFieldValidationStatus('buyerAddress')}
              value={getFieldValue('buyerAddress')}
              touched={Boolean(touchedFields.buyerAddress)}
            >
              <input
                id="buyerAddress"
                type="text"
                value={buyerAddress}
                onChange={(e) => handleBuyerAddressChange(e.target.value)}
                onBlur={handleBuyerAddressBlur}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
          </div>
        </SectionWrapper>

        {/* Invoice Details */}
        <SectionWrapper title={t('form.invoiceDetails', language)} isValid={sectionValidity.invoiceDetails}>
          <div className="grid grid-cols-3 gap-4">
            <FieldWrapper
              name="invoiceDate"
              label={t('form.invoiceDate', language)}
              error={errors.invoiceDate}
              validationStatus={getFieldValidationStatus('invoiceDate')}
              value={getFieldValue('invoiceDate')}
              touched={Boolean(touchedFields.invoiceDate)}
            >
              <input
                id="invoiceDate"
                type="date"
                value={invoiceDate}
                onChange={(e) => handleInvoiceDateChange(e.target.value)}
                onBlur={handleInvoiceDateBlur}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
            <FieldWrapper
              name="dueDate"
              label={t('form.dueDate', language)}
              required={false}
              error={errors.dueDate}
              validationStatus={getFieldValidationStatus('dueDate')}
              value={getFieldValue('dueDate')}
              touched={Boolean(touchedFields.dueDate)}
            >
              <input
                id="dueDate"
                type="date"
                value={dueDate}
                onChange={(e) => handleDueDateChange(e.target.value)}
                onBlur={handleDueDateBlur}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
            <FieldWrapper
              name="invoiceNo"
              label={t('form.invoiceNo', language)}
              error={errors.invoiceNo}
              validationStatus={getFieldValidationStatus('invoiceNo')}
              value={getFieldValue('invoiceNo')}
              touched={Boolean(touchedFields.invoiceNo)}
            >
              <input
                id="invoiceNo"
                type="text"
                value={invoiceNo}
                onChange={(e) => handleInvoiceNoChange(e.target.value)}
                onBlur={handleInvoiceNoBlur}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 pr-10 text-white focus:outline-none focus:border-primary"
              />
            </FieldWrapper>
          </div>
          <FieldWrapper
            name="remarks"
            label={t('form.remarks', language)}
            required={false}
            error={errors.remarks}
            validationStatus={getFieldValidationStatus('remarks')}
            value={getFieldValue('remarks')}
            touched={Boolean(touchedFields.remarks)}
          >
            <textarea
              id="remarks"
              value={remarks}
              onChange={(e) => handleRemarksChange(e.target.value)}
              rows={3}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-primary resize-y"
            />
          </FieldWrapper>
        </SectionWrapper>

        {/* Line Items */}
        <SectionWrapper title={t('form.lineItems', language)} isValid={sectionValidity.lineItems}>
          <LineItemsTable items={items} onItemsChange={handleItemsChange} />
          {errors.items && (
            <p className="text-xs text-error flex items-center gap-1">
              <XCircle size={12} />
              {errors.items}
            </p>
          )}
        </SectionWrapper>

        {/* Totals Section */}
        <SectionWrapper title={t('form.totals', language)} isValid={sectionValidity.totals}>
          <div className="bg-dark-bg rounded-lg p-4 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">{t('form.subtotal', language)}</span>
              <span className="text-white">¥{totals.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">{t('form.taxTotal', language)}</span>
              <span className="text-white">¥{totals.taxTotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-base font-semibold pt-2 border-t border-dark-border">
              <span className="text-white">{t('form.grandTotal', language)}</span>
              <span className="text-white">¥{totals.grandTotal.toFixed(2)}</span>
            </div>
          </div>
        </SectionWrapper>

        {/* Submit Button */}
        <PrimaryButton type="submit" className="w-full" disabled={!formIsValid || isSubmitting || isGeneratingPdf}>
          {isGeneratingPdf ? t('form.generatingPdf', language) : isSubmitting ? t('form.validating', language) : t('form.validateGenerate', language)}
        </PrimaryButton>
      </form>
    </div>
  );
}
