// API helper for Flask backend
// In dev: uses VITE_API_BASE_URL (defaults to http://localhost:5000)
// In prod: uses empty string (same origin) if VITE_API_BASE_URL is not set

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? "" : "http://localhost:5000");

import { getAuthHeader } from './auth';

/**
 * Get default headers with authentication if available.
 */
function getDefaultHeaders(): HeadersInit {
  const headers: HeadersInit = {};
  const authHeader = getAuthHeader();
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }
  return headers;
}

export interface SingleLookupResult {
  business_id: string;
  name?: string;
  address?: string;
  registration_status?: string;
  timestamp: string;
  error?: string;
}

export interface BulkLookupResult {
  business_id: string;
  name?: string;
  address?: string;
  registration_status?: string;
  timestamp: string;
  error?: string;
}

export interface BulkLookupResponse {
  results: BulkLookupResult[];
  errors?: Array<{
    business_id: string;
    error: string;
    row?: number;
  }>;
}

/**
 * Single business lookup
 * @param businessId - 13-digit corporate number
 * @returns Promise with lookup result
 */
export async function lookupSingle(businessId: string): Promise<SingleLookupResult> {
  console.log("[API] lookupSingle called with", businessId);

  const res = await fetch(`${API_BASE_URL}/lookup-single`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      business_id: businessId,
    }),
  });

  console.log("[API] lookupSingle status", res.status);

  const data = await res.json().catch((err) => {
    console.error("[API] lookupSingle JSON parse error", err);
    throw err;
  });

  console.log("[API] lookupSingle body", data);

  if (!res.ok) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }

  return data;
}

/**
 * Bulk CSV lookup
 * @param file - CSV file to upload
 * @returns Promise with array of lookup results
 */
export async function lookupCsv(file: File): Promise<BulkLookupResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/lookup-csv`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Bulk JSON lookup (array of business IDs)
 * @param businessIds - Array of 13-digit corporate numbers
 * @returns Promise with array of lookup results
 */
export async function lookupBulk(businessIds: string[]): Promise<BulkLookupResponse> {
  const response = await fetch(`${API_BASE_URL}/lookup-bulk`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ business_ids: businessIds }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  return response.json();
}

