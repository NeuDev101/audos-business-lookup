/**
 * History API calls.
 */

import { API_BASE_URL } from './api';
import { getAuthHeader } from './auth';

export interface InvoiceHistoryItem {
  id: number;
  user_id: number;
  invoice_number: string;
  batch_id: string | null;
  status: 'pass' | 'fail';
  issues_count: number;
  pdf_path: string | null;
  pdf_hash: string;
  ruleset_version: string;
  created_at: string;
}

export interface HistoryResponse {
  invoices: InvoiceHistoryItem[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}

export interface HistoryFilters {
  status?: 'pass' | 'fail';
  batch_id?: string;
  invoice_number?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}

/**
 * Get invoice history with filters.
 */
export async function getHistory(filters: HistoryFilters = {}): Promise<HistoryResponse> {
  const params = new URLSearchParams();
  
  if (filters.status) params.append('status', filters.status);
  if (filters.batch_id) params.append('batch_id', filters.batch_id);
  if (filters.invoice_number) params.append('invoice_number', filters.invoice_number);
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  if (filters.page) params.append('page', filters.page.toString());
  if (filters.per_page) params.append('per_page', filters.per_page.toString());

  const headers: HeadersInit = {};
  const authHeader = getAuthHeader();
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(`${API_BASE_URL}/api/history?${params.toString()}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Get a specific invoice detail.
 */
export async function getInvoiceDetail(invoiceId: number): Promise<InvoiceHistoryItem> {
  const headers: HeadersInit = {};
  const authHeader = getAuthHeader();
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  const response = await fetch(`${API_BASE_URL}/api/history/${invoiceId}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  return response.json();
}

