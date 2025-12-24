import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';
import { LanguageProvider } from '../contexts/LanguageContext';
import { t } from '../lib/strings';
import { AuthProvider } from '../contexts/AuthContext';
import { vi } from 'vitest';
import React from 'react';

vi.mock('../contexts/AuthContext', async () => {
  const mockAuth = {
    user: { id: 0, email: 'demo@audos.local', username: 'demo' },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  };
  return {
    AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    useAuth: () => mockAuth,
  };
});

describe('<App /> routing', () => {
  it('shows all sidebar navigation labels', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AuthProvider>
          <LanguageProvider>
            <App />
          </LanguageProvider>
        </AuthProvider>
      </MemoryRouter>,
    );

    const labels = [
      t('nav.dashboard', 'ja'),
      t('nav.invoices', 'ja'),
      t('nav.businessLookup', 'ja'),
      t('nav.history', 'ja'),
      t('nav.settings', 'ja'),
    ];

    for (const label of labels) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
    }
  });

  it('renders core routes without throwing', () => {
    const routes = ['/single', '/bulk', '/console', '/console/bulk'];

    for (const route of routes) {
      const { unmount } = render(
        <MemoryRouter initialEntries={[route]}>
          <AuthProvider>
            <LanguageProvider>
              <App />
            </LanguageProvider>
          </AuthProvider>
        </MemoryRouter>,
      );
      unmount();
    }
  });
});
