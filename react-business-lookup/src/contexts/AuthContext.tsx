import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { clearTokens, getAccessToken, getRefreshToken, type User } from '../lib/auth';
import { refreshAccessToken } from '../lib/authApi';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Check if demo mode is explicitly enabled via environment variable
// Also fall back to demo mode when backend has DISABLE_AUTH=1 (via VITE_DISABLE_AUTH)
const DEMO_MODE = 
  import.meta.env.VITE_DEMO_MODE === 'true' || 
  import.meta.env.VITE_DEMO_MODE === '1' ||
  import.meta.env.VITE_DISABLE_AUTH === 'true' ||
  import.meta.env.VITE_DISABLE_AUTH === '1';
const demoUser: User = { id: 0, email: 'demo@audos.local', username: 'demo' };

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from stored tokens
  useEffect(() => {
    const initAuth = async () => {
      if (DEMO_MODE) {
        setUser(demoUser);
        setIsLoading(false);
        return;
      }

      const accessToken = getAccessToken();
      const refreshToken = getRefreshToken();

      if (accessToken) {
        // Token exists - try to refresh if needed
        // For now, assume token is valid if it exists
        // In a real app, you'd decode and validate the token
        // For demo purposes, we'll check if we can refresh
        try {
          const newToken = await refreshAccessToken();
          if (newToken) {
            // Token is valid - user is authenticated
            // In a real app, decode token to get user info
            // For now, we'll need to fetch user info from an endpoint or decode token
            setUser({ id: 0, email: 'user@audos.local', username: 'user' });
          } else {
            setUser(null);
          }
        } catch {
          setUser(null);
        }
      } else if (refreshToken) {
        // Try to refresh access token
        try {
          const newToken = await refreshAccessToken();
          if (newToken) {
            setUser({ id: 0, email: 'user@audos.local', username: 'user' });
          } else {
            setUser(null);
          }
        } catch {
          setUser(null);
        }
      } else {
        setUser(null);
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = (userData: User) => {
    setUser(userData);
  };

  const logout = () => {
    setUser(null);
    clearTokens();
  };

  const isAuthenticated = user !== null || DEMO_MODE;

  return (
    <AuthContext.Provider value={{ user: user || (DEMO_MODE ? demoUser : null), isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
