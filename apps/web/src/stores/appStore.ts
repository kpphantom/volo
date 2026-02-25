'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Page =
  | 'chat'
  | 'dashboard'
  | 'settings'
  | 'activity'
  | 'standing-orders'
  | 'analytics'
  | 'marketplace'
  | 'docs'
  | 'conversations'
  | 'google'
  | 'youtube'
  | 'social'
  | 'messages'
  | 'health'
  | 'vscode'
  | 'finance';

interface AppState {
  currentPage: Page;
  sidebarOpen: boolean;
  commandPaletteOpen: boolean;

  // Actions
  setPage: (page: Page) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentPage: 'chat',
      sidebarOpen: true,
      commandPaletteOpen: false,

      setPage: (page) => set({ currentPage: page }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
    }),
    {
      name: 'volo-app-state',
      partialize: (state) => ({ currentPage: state.currentPage, sidebarOpen: state.sidebarOpen }),
    }
  )
);
