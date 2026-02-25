'use client';

import { useState } from 'react';
import { Globe, Check, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useLocaleStore, SUPPORTED_LOCALES, type Locale } from '@/stores/localeStore';
import { useTranslation } from '@/lib/i18n';

interface LanguagePickerProps {
  /** 'inline' = dropdown inside user menu, 'standalone' = full settings panel */
  variant?: 'inline' | 'standalone';
  onSelect?: () => void;
}

export function LanguagePicker({ variant = 'inline', onSelect }: LanguagePickerProps) {
  const { locale, setLocale } = useLocaleStore();
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const currentInfo = SUPPORTED_LOCALES.find((l) => l.code === locale);

  const handleSelect = (code: Locale) => {
    setLocale(code);
    setOpen(false);
    onSelect?.();
    // Auto-set document direction for RTL languages
    const info = SUPPORTED_LOCALES.find((l) => l.code === code);
    if (info) {
      document.documentElement.dir = info.dir;
      document.documentElement.lang = code;
    }
  };

  if (variant === 'standalone') {
    return (
      <div className="space-y-2">
        <label className="text-sm font-medium text-zinc-300">{t('menu.language')}</label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
          {SUPPORTED_LOCALES.map((loc) => (
            <button
              key={loc.code}
              onClick={() => handleSelect(loc.code)}
              className={cn(
                'flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm transition-all text-left min-h-[44px]',
                locale === loc.code
                  ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30'
                  : 'bg-white/5 text-zinc-400 border border-white/5 hover:bg-white/10 hover:text-white'
              )}
            >
              <span className="flex-1 truncate">
                <span className="block text-xs opacity-75">{loc.name}</span>
                <span className="block font-medium">{loc.nativeName}</span>
              </span>
              {locale === loc.code && <Check className="w-4 h-4 text-brand-400 shrink-0" />}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // Inline variant for user menu dropdown
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 sm:py-2.5 text-sm text-zinc-400 hover:text-white hover:bg-white/5 transition-colors min-h-[48px] sm:min-h-[44px]"
      >
        <Globe className="w-4 h-4" />
        <span className="flex-1 text-left">{t('menu.language')}</span>
        <span className="text-xs text-zinc-500">{currentInfo?.nativeName}</span>
        <ChevronDown className={cn('w-3.5 h-3.5 text-zinc-500 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="px-2 pb-1 max-h-48 overflow-y-auto">
          <div className="grid grid-cols-2 gap-1">
            {SUPPORTED_LOCALES.map((loc) => (
              <button
                key={loc.code}
                onClick={() => handleSelect(loc.code)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all text-left',
                  locale === loc.code
                    ? 'bg-brand-500/15 text-brand-400'
                    : 'text-zinc-400 hover:bg-white/5 hover:text-white'
                )}
              >
                <span className="truncate">{loc.nativeName}</span>
                {locale === loc.code && <Check className="w-3 h-3 text-brand-400 shrink-0" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
