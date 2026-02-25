'use client';

import { Toaster } from 'sonner';
import { useThemeStore } from '@/stores/themeStore';
import { useLocaleStore } from '@/stores/localeStore';
import { useEffect, useState } from 'react';

/**
 * Renders the Sonner <Toaster> with theme synced from themeStore and
 * locale-aware direction for RTL support.
 * Also syncs the html[lang] attribute on mount to the persisted locale.
 */
export function ToasterThemeSync() {
  const mode = useThemeStore((s) => s.mode);
  const locale = useLocaleStore((s) => s.locale);
  const [resolved, setResolved] = useState<'light' | 'dark'>('dark');

  useEffect(() => {
    if (mode === 'system') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      setResolved(mq.matches ? 'dark' : 'light');
      const handler = (e: MediaQueryListEvent) => setResolved(e.matches ? 'dark' : 'light');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
    setResolved(mode === 'light' ? 'light' : 'dark');
  }, [mode]);

  // Sync html[lang] on hydration
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const isDark = resolved === 'dark';

  return (
    <Toaster
      theme={resolved}
      position="bottom-right"
      toastOptions={{
        style: {
          background: isDark ? '#18181b' : '#ffffff',
          border: isDark ? '1px solid rgba(255,255,255,0.05)' : '1px solid rgba(0,0,0,0.08)',
          color: isDark ? '#e4e4e7' : '#1a1a2e',
          fontSize: '13px',
        },
      }}
    />
  );
}
