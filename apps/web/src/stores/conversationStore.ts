'use client';

import { create } from 'zustand';

interface Conversation {
  id: string;
  title: string;
  preview: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface ConversationState {
  conversations: Conversation[];
  loading: boolean;
  searchQuery: string;

  // Actions
  fetchConversations: () => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  setSearchQuery: (query: string) => void;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useConversationStore = create<ConversationState>((set, get) => ({
  conversations: [],
  loading: false,
  searchQuery: '',

  fetchConversations: async () => {
    set({ loading: true });
    try {
      const q = get().searchQuery;
      const url = q
        ? `${API}/api/conversations?search=${encodeURIComponent(q)}`
        : `${API}/api/conversations`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        set({ conversations: data.conversations || [] });
      }
    } catch {
      // silently fail
    } finally {
      set({ loading: false });
    }
  },

  deleteConversation: async (id) => {
    try {
      await fetch(`${API}/api/conversations/${id}`, { method: 'DELETE' });
      set((s) => ({
        conversations: s.conversations.filter((c) => c.id !== id),
      }));
    } catch {
      // silently fail
    }
  },

  renameConversation: async (id, title) => {
    try {
      await fetch(`${API}/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      set((s) => ({
        conversations: s.conversations.map((c) =>
          c.id === id ? { ...c, title } : c,
        ),
      }));
    } catch {
      // silently fail
    }
  },

  setSearchQuery: (query) => set({ searchQuery: query }),
}));
