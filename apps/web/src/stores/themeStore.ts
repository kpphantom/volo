'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ThemeMode = 'dark' | 'light' | 'system';
export type FontSize = 'small' | 'default' | 'large' | 'xl';
export type ColorTheme = 'midnight' | 'aurora' | 'ember' | 'ocean';

interface ThemeState {
  mode: ThemeMode;
  fontSize: FontSize;
  reducedMotion: boolean;
  highContrast: boolean;
  colorTheme: ColorTheme;

  setMode: (mode: ThemeMode) => void;
  setFontSize: (size: FontSize) => void;
  setReducedMotion: (on: boolean) => void;
  setHighContrast: (on: boolean) => void;
  setColorTheme: (theme: ColorTheme) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: 'dark',
      fontSize: 'default',
      reducedMotion: false,
      highContrast: false,
      colorTheme: 'midnight',

      setMode: (mode) => set({ mode }),
      setFontSize: (fontSize) => set({ fontSize }),
      setReducedMotion: (reducedMotion) => set({ reducedMotion }),
      setHighContrast: (highContrast) => set({ highContrast }),
      setColorTheme: (colorTheme) => set({ colorTheme }),
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
