import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/api', () => ({
  api: { get: vi.fn(), delete: vi.fn(), patch: vi.fn() },
}));

vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

import { api } from '@/lib/api';
import { toast } from 'sonner';
import { useConversationStore } from '@/stores/conversationStore';

const mockGet = vi.mocked(api.get);
const mockDelete = vi.mocked(api.delete);
const mockPatch = vi.mocked(api.patch);
const mockToastError = vi.mocked(toast.error);

const fakeConvs = [
  { id: 'c1', title: 'Chat 1', preview: 'hello', created_at: '', updated_at: '', message_count: 2 },
  { id: 'c2', title: 'Chat 2', preview: 'world', created_at: '', updated_at: '', message_count: 5 },
];

describe('conversationStore', () => {
  beforeEach(() => {
    useConversationStore.setState({ conversations: [], loading: false, searchQuery: '' });
    vi.clearAllMocks();
  });

  // ── fetchConversations ────────────────────────────────────────────────────

  describe('fetchConversations()', () => {
    it('loads conversations from the API', async () => {
      mockGet.mockResolvedValue({ conversations: fakeConvs });
      await useConversationStore.getState().fetchConversations();
      expect(useConversationStore.getState().conversations).toEqual(fakeConvs);
    });

    it('calls the base endpoint when searchQuery is empty', async () => {
      mockGet.mockResolvedValue({ conversations: [] });
      await useConversationStore.getState().fetchConversations();
      expect(mockGet).toHaveBeenCalledWith('/api/conversations');
    });

    it('appends search query to endpoint when set', async () => {
      mockGet.mockResolvedValue({ conversations: [] });
      useConversationStore.setState({ searchQuery: 'hello world' });
      await useConversationStore.getState().fetchConversations();
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining('search=hello%20world'),
      );
    });

    it('is loading during fetch and false after', async () => {
      let resolve!: (v: any) => void;
      mockGet.mockReturnValue(new Promise((r) => { resolve = r; }));

      const fetchPromise = useConversationStore.getState().fetchConversations();
      expect(useConversationStore.getState().loading).toBe(true);

      resolve({ conversations: [] });
      await fetchPromise;
      expect(useConversationStore.getState().loading).toBe(false);
    });

    it('keeps existing conversations and clears loading on API error', async () => {
      useConversationStore.setState({ conversations: fakeConvs });
      mockGet.mockRejectedValue(new Error('Network error'));
      await useConversationStore.getState().fetchConversations();
      expect(useConversationStore.getState().conversations).toEqual(fakeConvs);
      expect(useConversationStore.getState().loading).toBe(false);
    });

    it('stores an empty array when API returns nothing', async () => {
      mockGet.mockResolvedValue({ conversations: null });
      await useConversationStore.getState().fetchConversations();
      expect(useConversationStore.getState().conversations).toEqual([]);
    });
  });

  // ── deleteConversation ────────────────────────────────────────────────────

  describe('deleteConversation()', () => {
    it('removes the conversation optimistically', async () => {
      useConversationStore.setState({ conversations: fakeConvs });
      mockDelete.mockResolvedValue({});

      await useConversationStore.getState().deleteConversation('c1');

      const ids = useConversationStore.getState().conversations.map((c) => c.id);
      expect(ids).toEqual(['c2']);
    });

    it('rolls back and shows error toast on API failure', async () => {
      useConversationStore.setState({ conversations: fakeConvs });
      mockDelete.mockRejectedValue(new Error('Server error'));

      await useConversationStore.getState().deleteConversation('c1');

      expect(useConversationStore.getState().conversations).toEqual(fakeConvs);
      expect(mockToastError).toHaveBeenCalledWith('Failed to delete conversation');
    });
  });

  // ── renameConversation ────────────────────────────────────────────────────

  describe('renameConversation()', () => {
    it('updates the title optimistically', async () => {
      useConversationStore.setState({ conversations: fakeConvs });
      mockPatch.mockResolvedValue({});

      await useConversationStore.getState().renameConversation('c1', 'New Title');

      const conv = useConversationStore.getState().conversations.find((c) => c.id === 'c1')!;
      expect(conv.title).toBe('New Title');
    });

    it('rolls back and shows error toast on API failure', async () => {
      useConversationStore.setState({ conversations: fakeConvs });
      mockPatch.mockRejectedValue(new Error('Server error'));

      await useConversationStore.getState().renameConversation('c1', 'New Title');

      const conv = useConversationStore.getState().conversations.find((c) => c.id === 'c1')!;
      expect(conv.title).toBe('Chat 1');
      expect(mockToastError).toHaveBeenCalledWith('Failed to rename conversation');
    });

    it('only renames the target conversation', async () => {
      useConversationStore.setState({ conversations: fakeConvs });
      mockPatch.mockResolvedValue({});

      await useConversationStore.getState().renameConversation('c1', 'Renamed');

      const c2 = useConversationStore.getState().conversations.find((c) => c.id === 'c2')!;
      expect(c2.title).toBe('Chat 2');
    });
  });

  // ── setSearchQuery ────────────────────────────────────────────────────────

  describe('setSearchQuery()', () => {
    it('updates the search query', () => {
      useConversationStore.getState().setSearchQuery('vitest');
      expect(useConversationStore.getState().searchQuery).toBe('vitest');
    });

    it('can be cleared', () => {
      useConversationStore.setState({ searchQuery: 'something' });
      useConversationStore.getState().setSearchQuery('');
      expect(useConversationStore.getState().searchQuery).toBe('');
    });
  });
});
