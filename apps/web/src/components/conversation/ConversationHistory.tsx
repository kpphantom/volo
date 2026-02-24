'use client';

import { useEffect, useState } from 'react';
import {
  MessageSquare,
  Search,
  Trash2,
  Edit3,
  Calendar,
  GitBranch,
  Download,
  MoreHorizontal,
} from 'lucide-react';
import { useConversationStore } from '@/stores/conversationStore';
import { useChatStore } from '@/stores/chatStore';
import { useAppStore } from '@/stores/appStore';

export function ConversationHistory() {
  const { conversations, loading, searchQuery, fetchConversations, deleteConversation, renameConversation, setSearchQuery } =
    useConversationStore();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [menuOpen, setMenuOpen] = useState<string | null>(null);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  const handleSearch = (q: string) => {
    setSearchQuery(q);
    fetchConversations();
  };

  const startRename = (id: string, currentTitle: string) => {
    setEditingId(id);
    setEditTitle(currentTitle);
    setMenuOpen(null);
  };

  const saveRename = () => {
    if (editingId && editTitle.trim()) {
      renameConversation(editingId, editTitle.trim());
    }
    setEditingId(null);
  };

  const openConversation = (id: string) => {
    // Load conversation into chat
    useAppStore.getState().setPage('chat');
  };

  const formatDate = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) return 'Today';
    if (diff < 172800000) return 'Yesterday';
    return d.toLocaleDateString();
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Conversations</h1>
          <p className="text-sm text-[var(--text-muted)]">Browse and manage your chat history</p>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-10 pr-4 py-2.5 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* List */}
        <div className="space-y-2">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => openConversation(conv.id)}
              className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 hover:border-blue-500/30 transition-colors cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <MessageSquare className="w-5 h-5 text-blue-400 mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    {editingId === conv.id ? (
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={saveRename}
                        onKeyDown={(e) => e.key === 'Enter' && saveRename()}
                        autoFocus
                        className="w-full px-2 py-1 bg-[var(--bg-primary)] border border-blue-500 rounded text-sm text-[var(--text-primary)] focus:outline-none"
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : (
                      <h3 className="font-medium text-[var(--text-primary)] truncate">
                        {conv.title}
                      </h3>
                    )}
                    <p className="text-xs text-[var(--text-muted)] mt-1 truncate">
                      {conv.preview || 'No messages yet'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(conv.updated_at)}
                  </span>
                  <span className="text-xs text-[var(--text-muted)] px-1.5 py-0.5 bg-[var(--bg-primary)] rounded">
                    {conv.message_count} msgs
                  </span>

                  {/* Actions */}
                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpen(menuOpen === conv.id ? null : conv.id);
                      }}
                      className="p-1 text-[var(--text-muted)] hover:text-[var(--text-primary)] opacity-0 group-hover:opacity-100 transition-all"
                    >
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                    {menuOpen === conv.id && (
                      <div className="absolute right-0 top-full mt-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-lg shadow-xl py-1 z-10 w-36">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            startRename(conv.id, conv.title);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-primary)]"
                        >
                          <Edit3 className="w-3 h-3" /> Rename
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpen(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-primary)]"
                        >
                          <Download className="w-3 h-3" /> Export
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteConversation(conv.id);
                            setMenuOpen(null);
                          }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-[var(--bg-primary)]"
                        >
                          <Trash2 className="w-3 h-3" /> Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}

          {conversations.length === 0 && !loading && (
            <div className="py-16 text-center">
              <MessageSquare className="w-10 h-10 text-[var(--text-muted)] mx-auto mb-3 opacity-40" />
              <h3 className="text-lg font-medium text-[var(--text-primary)] mb-1">No conversations</h3>
              <p className="text-sm text-[var(--text-muted)]">Start chatting to create your first conversation.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
