import { useState } from 'react';
import { Layout } from '../components/Layout';
import { PrimaryButton } from '../components/PrimaryButton';
import { SecondaryButton } from '../components/SecondaryButton';
import { useLanguage } from '../contexts/LanguageContext';
import { t } from '../lib/strings';

export function SettingsPage() {
  const [apiUrl, setApiUrl] = useState('https://api.audos.dev');
  const [apiKey, setApiKey] = useState('••••••••••••••••');
  const [corsOrigins, setCorsOrigins] = useState('http://localhost:5173');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [notifySuccess, setNotifySuccess] = useState(true);
  const [notifyFailure, setNotifyFailure] = useState(true);
  const [retentionDays, setRetentionDays] = useState(30);
  const [outputDir, setOutputDir] = useState('/var/lib/audos/batches');
  const { language } = useLanguage();

  const Section = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <section className="bg-(--color-bg-card) rounded-xl border border-(--color-border)/40 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <div className="flex gap-2">
          <SecondaryButton className="text-sm px-4 py-2" type="button">
            {t('common.cancel', language)}
          </SecondaryButton>
          <PrimaryButton className="text-sm px-4 py-2" type="button">
            {t('common.save', language)}
          </PrimaryButton>
        </div>
      </div>
      {children}
    </section>
  );

  const Input = ({
    label,
    ...props
  }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) => (
    <label className="block">
      <span className="text-sm text-gray-400 mb-2 inline-block">{label}</span>
      <input
        {...props}
        className={`w-full bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-3 py-2 text-sm text-white ${props.className || ''}`}
      />
    </label>
  );

  return (
    <Layout activeNav="settings">
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{t('settings.title', language)}</h1>
          <p className="text-(--color-text-secondary)">{t('settings.subtitle', language)}</p>
        </div>

        <Section title={t('settings.apiConfig', language)}>
          <div className="grid grid-cols-2 gap-4">
            <Input label={t('settings.baseUrl', language)} value={apiUrl} onChange={(event) => setApiUrl(event.target.value)} />
            <Input label={t('settings.apiKey', language)} type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
            <div className="col-span-2">
              <label className="block">
                <span className="text-sm text-gray-400 mb-2 inline-block">{t('settings.allowedCors', language)}</span>
                <textarea
                  value={corsOrigins}
                  onChange={(event) => setCorsOrigins(event.target.value)}
                  className="w-full bg-(--color-bg-dark) border border-(--color-border)/60 rounded-lg px-3 py-2 text-sm text-white min-h-[80px]"
                />
              </label>
            </div>
          </div>
        </Section>

        <Section title={t('settings.notifications', language)}>
          <div className="grid grid-cols-2 gap-4">
            <Input label={t('settings.webhookUrl', language)} value={webhookUrl} onChange={(event) => setWebhookUrl(event.target.value)} />
            <div className="flex flex-col justify-end gap-3">
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={notifySuccess}
                  onChange={(event) => setNotifySuccess(event.target.checked)}
                  className="accent-(--color-primary)"
                />
                {t('settings.notifySuccess', language)}
              </label>
              <label className="inline-flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={notifyFailure}
                  onChange={(event) => setNotifyFailure(event.target.checked)}
                  className="accent-(--color-primary)"
                />
                {t('settings.notifyFailure', language)}
              </label>
            </div>
          </div>
        </Section>

        <Section title={t('settings.dataRetention', language)}>
          <div className="grid grid-cols-2 gap-4">
            <Input
              label={t('settings.logRetention', language)}
              type="number"
              min={1}
              value={retentionDays}
              onChange={(event) => setRetentionDays(Number(event.target.value))}
            />
            <Input label={t('settings.outputDirectory', language)} value={outputDir} onChange={(event) => setOutputDir(event.target.value)} />
          </div>
        </Section>
      </div>
    </Layout>
  );
}
