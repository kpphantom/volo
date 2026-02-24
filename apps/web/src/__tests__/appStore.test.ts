import { describe, it, expect } from 'vitest';
import { useAppStore } from '@/stores/appStore';

describe('appStore', () => {
  it('defaults to chat page', () => {
    const state = useAppStore.getState();
    expect(state.currentPage).toBe('chat');
  });

  it('can change page', () => {
    useAppStore.getState().setPage('dashboard');
    expect(useAppStore.getState().currentPage).toBe('dashboard');
    useAppStore.getState().setPage('chat');
  });

  it('can toggle sidebar', () => {
    const initial = useAppStore.getState().sidebarOpen;
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(!initial);
    useAppStore.getState().toggleSidebar();
    expect(useAppStore.getState().sidebarOpen).toBe(initial);
  });

  it('supports all page types', () => {
    const pages = [
      'chat', 'dashboard', 'settings', 'activity',
      'standing-orders', 'analytics', 'marketplace', 'docs', 'conversations',
    ] as const;
    for (const page of pages) {
      useAppStore.getState().setPage(page);
      expect(useAppStore.getState().currentPage).toBe(page);
    }
    useAppStore.getState().setPage('chat');
  });
});
