import { describe, it, expect, beforeEach } from 'vitest';
import { useLocaleStore, getLocaleInfo, SUPPORTED_LOCALES } from '@/stores/localeStore';

describe('localeStore', () => {
  beforeEach(() => {
    useLocaleStore.setState({ locale: 'en' });
  });

  describe('setLocale()', () => {
    it('updates the active locale', () => {
      useLocaleStore.getState().setLocale('fr');
      expect(useLocaleStore.getState().locale).toBe('fr');
    });

    it('can switch between locales', () => {
      useLocaleStore.getState().setLocale('ja');
      expect(useLocaleStore.getState().locale).toBe('ja');
      useLocaleStore.getState().setLocale('en');
      expect(useLocaleStore.getState().locale).toBe('en');
    });
  });
});

describe('getLocaleInfo()', () => {
  it('returns correct info for English', () => {
    const info = getLocaleInfo('en');
    expect(info.code).toBe('en');
    expect(info.name).toBe('English');
    expect(info.nativeName).toBe('English');
    expect(info.dir).toBe('ltr');
  });

  it('returns RTL direction for Arabic', () => {
    const info = getLocaleInfo('ar');
    expect(info.dir).toBe('rtl');
  });

  it('returns correct nativeName for Spanish', () => {
    expect(getLocaleInfo('es').nativeName).toBe('Español');
  });

  it('returns correct nativeName for Chinese', () => {
    expect(getLocaleInfo('zh').nativeName).toBe('中文');
  });

  it('falls back to English for unknown locale code', () => {
    const info = getLocaleInfo('xx' as any);
    expect(info.code).toBe('en');
  });
});

describe('SUPPORTED_LOCALES', () => {
  it('contains 18 locales', () => {
    expect(SUPPORTED_LOCALES).toHaveLength(18);
  });

  it('Arabic is the only RTL locale', () => {
    const rtl = SUPPORTED_LOCALES.filter((l) => l.dir === 'rtl');
    expect(rtl).toHaveLength(1);
    expect(rtl[0].code).toBe('ar');
  });

  it('every locale has all required fields', () => {
    for (const locale of SUPPORTED_LOCALES) {
      expect(locale.code).toBeTruthy();
      expect(locale.name).toBeTruthy();
      expect(locale.nativeName).toBeTruthy();
      expect(['ltr', 'rtl']).toContain(locale.dir);
    }
  });

  it('all locale codes are unique', () => {
    const codes = SUPPORTED_LOCALES.map((l) => l.code);
    expect(new Set(codes).size).toBe(codes.length);
  });
});
