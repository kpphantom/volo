import { useCallback } from 'react';
import { useLocaleStore, getLocaleInfo } from '@/stores/localeStore';
import { translate, type TranslationKey } from './translations';

/**
 * Translation hook for Volo components.
 *
 * Usage:
 *   const { t, locale, dir } = useTranslation();
 *   <p>{t('greeting.morning')}</p>
 */
export function useTranslation() {
  const locale = useLocaleStore((s) => s.locale);
  const info = getLocaleInfo(locale);

  const t = useCallback(
    (key: TranslationKey) => translate(locale, key),
    [locale]
  );

  return {
    t,
    locale,
    dir: info.dir,
    localeName: info.nativeName,
  };
}
