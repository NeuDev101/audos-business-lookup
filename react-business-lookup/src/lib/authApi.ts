/**
 * Authentication API calls.
 */

import { API_BASE_URL } from './api';
import { storeTokens, clearTokens, getRefreshToken, getAccessToken, type AuthTokens, type User } from './auth';

// Check if demo mode is explicitly enabled via environment variable
// Also fall back to demo mode when backend has DISABLE_AUTH=1 (via VITE_DISABLE_AUTH)
const DEMO_MODE = 
  import.meta.env.VITE_DEMO_MODE === 'true' || 
  import.meta.env.VITE_DEMO_MODE === '1' ||
  import.meta.env.VITE_DISABLE_AUTH === 'true' ||
  import.meta.env.VITE_DISABLE_AUTH === '1';
const demoResponse: AuthTokens = {
  access_token: 'demo-access-token',
  refresh_token: 'demo-refresh-token',
  user: { id: 0, email: 'demo@audos.local', username: 'demo' },
};

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username?: string;
}

/**
 * Register a new user.
 */
export async function register(data: RegisterRequest): Promise<AuthTokens> {
  if (DEMO_MODE) {
    storeTokens(demoResponse);
    return demoResponse;
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  const tokens = await response.json();
  storeTokens(tokens);
  return tokens;
}

/**
 * Login and get tokens.
 */
export async function login(data: LoginRequest): Promise<AuthTokens> {
  if (DEMO_MODE) {
    storeTokens(demoResponse);
    return demoResponse;
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  const tokens = await response.json();
  storeTokens(tokens);
  return tokens;
}

/**
 * Refresh access token.
 */
export async function refreshAccessToken(): Promise<string | null> {
  if (DEMO_MODE) {
    return demoResponse.access_token;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearTokens();
      return null;
    }

    const data = await response.json();
    const newAccessToken = data.access_token;
    
    // Update stored access token
    localStorage.setItem('audos_access_token', newAccessToken);
    
    return newAccessToken;
  } catch (error) {
    clearTokens();
    return null;
  }
}

/**
 * Logout (clear tokens).
 */
export function logout(): void {
  clearTokens();
}
