import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register, type LoginRequest, type RegisterRequest } from '../lib/authApi';
import { useAuth } from '../contexts/AuthContext';
import { PrimaryButton } from '../components/PrimaryButton';
import { SecondaryButton } from '../components/SecondaryButton';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login: setAuthUser } = useAuth();
  const navigate = useNavigate();
  const { language } = useLanguage();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      if (isLogin) {
        const data: LoginRequest = { email, password };
        const result = await login(data);
        setAuthUser(result.user);
        navigate('/dashboard');
      } else {
        const data: RegisterRequest = { email, password, username: username || undefined };
        const result = await register(data);
        setAuthUser(result.user);
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('auth.failed', language));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="w-full max-w-md">
        <div className="bg-(--color-bg-card) rounded-xl border border-(--color-border)/40 p-8 shadow-xl">
          <h1 className="text-3xl font-bold text-white mb-2 text-center">
            {isLogin ? t('auth.login', language) : t('auth.register', language)}
          </h1>
          <p className="text-gray-400 text-center mb-6">
            {isLogin ? t('auth.loginSubtitle', language) : t('auth.registerSubtitle', language)}
          </p>

          {error && (
            <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  {t('auth.username', language)} ({t('common.optional', language)})
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-(--color-primary)"
                />
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-2">{t('auth.email', language)}</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-(--color-primary)"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">{t('auth.password', language)}</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                className="w-full bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-(--color-primary)"
              />
            </div>

            <PrimaryButton type="submit" disabled={isLoading} className="w-full">
              {isLoading ? t('common.pleaseWait', language) : isLogin ? t('auth.login', language) : t('auth.register', language)}
            </PrimaryButton>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => {
                setIsLogin(!isLogin);
                setError(null);
              }}
              className="text-(--color-primary) hover:underline text-sm"
            >
              {isLogin ? t('auth.noAccount', language) : t('auth.haveAccount', language)}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
