'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeMode = 'dark' | 'light' | 'system';
export type FontSize = 'small' | 'default' | 'large' | 'xl';

interface ThemeState {
  mode: ThemeMode;
  fontSize: FontSize;
  reducedMotion: boolean;
  highContrast: boolean;

  setMode: (mode: ThemeMode) => void;
  setFontSize: (size: FontSize) => void;
  setReducedMotion: (on: boolean) => void;
  setHighContrast: (on: boolean) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: 'dark',
      fontSize: 'default',
      reducedMotion: false,
      highContrast: false,

      setMode: (mode) => set({ mode }),
      setFontSize: (fontSize) => set({ fontSize }),
      setReducedMotion: (reducedMotion) => set({ reducedMotion }),
      setHighContrast: (highContrast) => set({ highContrast }),
    }),
    { name: 'volo-theme' }
  )
);

export const fontSizeScale: Record<FontSize, string> = {
  small: '14px',
  default: '16px',
  large: '18px',
  xl: '20px',
};
