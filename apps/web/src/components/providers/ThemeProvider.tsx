'use client';

import { useEffect } from 'react';
import { useThemeStore, fontSizeScale } from '@/stores/themeStore';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const { mode, fontSize, highContrast, reducedMotion, colorTheme } = useThemeStore();

  useEffect(() => {
    const root = document.documentElement;

    // Theme mode
    if (mode === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.classList.toggle('dark', prefersDark);
      root.classList.toggle('light', !prefersDark);

      const listener = (e: MediaQueryListEvent) => {
        root.classList.toggle('dark', e.matches);
        root.classList.toggle('light', !e.matches);
      };
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      mq.addEventListener('change', listener);
      return () => mq.removeEventListener('change', listener);
    } else {
      root.classList.toggle('dark', mode === 'dark');
      root.classList.toggle('light', mode === 'light');
    }
  }, [mode]);

  useEffect(() => {
    document.documentElement.style.fontSize = fontSizeScale[fontSize];
  }, [fontSize]);

  useEffect(() => {
    document.documentElement.classList.toggle('high-contrast', highContrast);
  }, [highContrast]);

  useEffect(() => {
    document.documentElement.classList.toggle('reduce-motion', reducedMotion);
  }, [reducedMotion]);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', colorTheme);
  }, [colorTheme]);

  return <>{children}</>;
}
