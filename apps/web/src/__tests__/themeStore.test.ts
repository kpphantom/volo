import { describe, it, expect, beforeEach } from 'vitest';
import { useThemeStore, fontSizeScale } from '@/stores/themeStore';

describe('themeStore', () => {
  beforeEach(() => {
    useThemeStore.setState({
      mode: 'dark',
      fontSize: 'default',
      reducedMotion: false,
      highContrast: false,
    });
  });

  it('defaults to dark mode', () => {
    expect(useThemeStore.getState().mode).toBe('dark');
  });

  it('defaults to default font size', () => {
    expect(useThemeStore.getState().fontSize).toBe('default');
  });

  describe('setMode()', () => {
    it('switches to light', () => {
      useThemeStore.getState().setMode('light');
      expect(useThemeStore.getState().mode).toBe('light');
    });

    it('switches to system', () => {
      useThemeStore.getState().setMode('system');
      expect(useThemeStore.getState().mode).toBe('system');
    });

    it('switches back to dark', () => {
      useThemeStore.getState().setMode('light');
      useThemeStore.getState().setMode('dark');
      expect(useThemeStore.getState().mode).toBe('dark');
    });
  });

  describe('setFontSize()', () => {
    it('handles all valid sizes', () => {
      const sizes = ['small', 'default', 'large', 'xl'] as const;
      for (const size of sizes) {
        useThemeStore.getState().setFontSize(size);
        expect(useThemeStore.getState().fontSize).toBe(size);
      }
    });
  });

  describe('setReducedMotion()', () => {
    it('enables reduced motion', () => {
      useThemeStore.getState().setReducedMotion(true);
      expect(useThemeStore.getState().reducedMotion).toBe(true);
    });

    it('disables reduced motion', () => {
      useThemeStore.setState({ reducedMotion: true });
      useThemeStore.getState().setReducedMotion(false);
      expect(useThemeStore.getState().reducedMotion).toBe(false);
    });
  });

  describe('setHighContrast()', () => {
    it('enables high contrast', () => {
      useThemeStore.getState().setHighContrast(true);
      expect(useThemeStore.getState().highContrast).toBe(true);
    });

    it('disables high contrast', () => {
      useThemeStore.setState({ highContrast: true });
      useThemeStore.getState().setHighContrast(false);
      expect(useThemeStore.getState().highContrast).toBe(false);
    });
  });

  describe('fontSizeScale', () => {
    it('maps every FontSize to a pixel value', () => {
      expect(fontSizeScale.small).toBe('14px');
      expect(fontSizeScale.default).toBe('16px');
      expect(fontSizeScale.large).toBe('18px');
      expect(fontSizeScale.xl).toBe('20px');
    });
  });
});
