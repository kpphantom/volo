'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Locale =
  | 'en' | 'es' | 'fr' | 'de' | 'pt' | 'it'
  | 'ar' | 'zh' | 'ja' | 'ko' | 'hi' | 'ru'
  | 'tr' | 'nl' | 'pl' | 'sv' | 'th' | 'vi';

export interface LocaleInfo {
  code: Locale;
  name: string;       // English name
  nativeName: string;  // Name in its own language
  dir: 'ltr' | 'rtl';
}

export const SUPPORTED_LOCALES: LocaleInfo[] = [
  { code: 'en', name: 'English', nativeName: 'English', dir: 'ltr' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', dir: 'ltr' },
  { code: 'fr', name: 'French', nativeName: 'Français', dir: 'ltr' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', dir: 'ltr' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português', dir: 'ltr' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano', dir: 'ltr' },
  { code: 'nl', name: 'Dutch', nativeName: 'Nederlands', dir: 'ltr' },
  { code: 'pl', name: 'Polish', nativeName: 'Polski', dir: 'ltr' },
  { code: 'sv', name: 'Swedish', nativeName: 'Svenska', dir: 'ltr' },
  { code: 'tr', name: 'Turkish', nativeName: 'Türkçe', dir: 'ltr' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский', dir: 'ltr' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', dir: 'rtl' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', dir: 'ltr' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', dir: 'ltr' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', dir: 'ltr' },
  { code: 'ko', name: 'Korean', nativeName: '한국어', dir: 'ltr' },
  { code: 'th', name: 'Thai', nativeName: 'ไทย', dir: 'ltr' },
  { code: 'vi', name: 'Vietnamese', nativeName: 'Tiếng Việt', dir: 'ltr' },
];

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

/** Detect browser language and map to supported locale */
function detectBrowserLocale(): Locale {
  if (typeof navigator === 'undefined') return 'en';
  const browserLang = navigator.language?.split('-')[0]?.toLowerCase() || 'en';
  const supported = SUPPORTED_LOCALES.find((l) => l.code === browserLang);
  return supported ? supported.code : 'en';
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: detectBrowserLocale(),
      setLocale: (locale) => set({ locale }),
    }),
    { name: 'volo-locale' }
  )
);

/** Get info for a locale code */
export function getLocaleInfo(code: Locale): LocaleInfo {
  return SUPPORTED_LOCALES.find((l) => l.code === code) || SUPPORTED_LOCALES[0];
}
