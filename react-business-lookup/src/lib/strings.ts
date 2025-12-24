import en from '../locales/en.json';
import ja from '../locales/ja.json';

export type Language = 'en' | 'ja';

const locales: Record<Language, Record<string, string>> = {
  en,
  ja,
};

export function t(key: string, lang: Language = 'ja'): string {
  const localeStrings = locales[lang] || locales.ja;
  return localeStrings[key] ?? locales.en[key] ?? key;
}
