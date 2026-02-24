'use client';

import { useState, useEffect } from 'react';
import {
  MessageSquare,
  Plus,
  Settings,
  Zap,
  Code,
  TrendingUp,
  Mail,
  Terminal,
  Globe,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Brain,
  Trash2,
  Activity,
  Clock,
  BarChart3,
  Package,
  BookOpen,
  History,
  Chrome,
  Youtube,
  Share2,
  MessagesSquare,
  Heart,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { useChatStore } from '@/stores/chatStore';
import { useAppStore, type Page } from '@/stores/appStore';

interface IntegrationInfo {
  id: string;
  name: string;
  icon: typeof Code;
  connected: boolean;
}

const defaultIntegrations: IntegrationInfo[] = [
  { id: 'github', name: 'GitHub', icon: Code, connected: false },
  { id: 'email', name: 'Email', icon: Mail, connected: false },
  { id: 'trading', name: 'Trading', icon: TrendingUp, connected: false },
  { id: 'terminal', name: 'Machine', icon: Terminal, connected: false },
  { id: 'social', name: 'Social', icon: Globe, connected: false },
];

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<'chats' | 'integrations'>('chats');
  const [integrations, setIntegrations] = useState<IntegrationInfo[]>(defaultIntegrations);
  const { messages, clearMessages } = useChatStore();
  const { sidebarOpen, currentPage, setPage, toggleSidebar } = useAppStore();

  // Fetch real integration status
  useEffect(() => {
    const fetchIntegrations = async () => {
      try {
        const data = await api.get<{ integrations_count?: number; github?: boolean; email?: boolean; trading?: boolean }>('/api/system/status');
        setIntegrations((prev) =>
          prev.map((int) => {
            if (int.id === 'github' && data.github) return { ...int, connected: true };
            if (int.id === 'trading' && data.trading) return { ...int, connected: true };
            if (int.id === 'email' && data.email) return { ...int, connected: true };
            return int;
          })
        );
      } catch {
        // Keep defaults
      }
    };
    fetchIntegrations();
  }, []);

  // Derive conversation info from current messages
  const hasConversation = messages.length > 0;
  const conversationTitle = hasConversation
    ? messages[0]?.content.slice(0, 40) + (messages[0]?.content.length > 40 ? '...' : '')
    : '';

  const handleNewConversation = () => {
    clearMessages();
    setPage('chat');
  };

  const navItems: { id: Page; icon: typeof LayoutDashboard; label: string }[] = [
    { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { id: 'conversations', icon: History, label: 'History' },
    { id: 'standing-orders', icon: Clock, label: 'Standing Orders' },
    { id: 'activity', icon: Activity, label: 'Activity' },
    { id: 'analytics', icon: BarChart3, label: 'Analytics' },
    { id: 'google', icon: Chrome, label: 'Google' },
    { id: 'youtube', icon: Youtube, label: 'YouTube' },
    { id: 'social', icon: Share2, label: 'Social Feed' },
    { id: 'messages', icon: MessagesSquare, label: 'Messages' },
    { id: 'health', icon: Heart, label: 'Health' },
    { id: 'vscode', icon: Terminal, label: 'VS Code' },
    { id: 'marketplace', icon: Package, label: 'Marketplace' },
    { id: 'docs', icon: BookOpen, label: 'Docs' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <aside
      className={cn(
        'relative flex flex-col border-r border-white/5 bg-surface-dark-1 transition-all duration-300 z-40',
        sidebarOpen ? 'w-72' : 'w-0 overflow-hidden',
        'md:relative fixed inset-y-0 left-0'
      )}
      role="complementary"
      aria-label="Sidebar navigation"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <span className="text-lg font-bold tracking-tight gradient-text">VOLO</span>
      </div>

      {/* New Chat Button */}
      <div className="px-3 py-3">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Conversation
        </button>
      </div>

      {/* Tabs */}
      <div className="flex px-3 gap-1">
        <button
          onClick={() => setActiveTab('chats')}
          className={cn(
            'flex-1 py-2 text-xs font-medium rounded-lg transition-colors',
            activeTab === 'chats'
              ? 'bg-white/10 text-white'
              : 'text-zinc-500 hover:text-zinc-300'
          )}
        >
          Conversations
        </button>
        <button
          onClick={() => setActiveTab('integrations')}
          className={cn(
            'flex-1 py-2 text-xs font-medium rounded-lg transition-colors',
            activeTab === 'integrations'
              ? 'bg-white/10 text-white'
              : 'text-zinc-500 hover:text-zinc-300'
          )}
        >
          Integrations
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
        {activeTab === 'chats' ? (
          <>
            {hasConversation ? (
              <>
                <p className="px-3 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                  Current
                </p>
                <div className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white/5 text-left group">
                  <MessageSquare className="w-4 h-4 text-brand-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-zinc-300 truncate">{conversationTitle}</p>
                    <p className="text-[10px] text-zinc-600">
                      {messages.length} messages
                    </p>
                  </div>
                  <button
                    onClick={handleNewConversation}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/10 transition-all"
                    title="Clear conversation"
                  >
                    <Trash2 className="w-3 h-3 text-zinc-500 hover:text-red-400" />
                  </button>
                </div>
              </>
            ) : (
              <div className="px-3 py-8 text-center">
                <MessageSquare className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                <p className="text-xs text-zinc-600">
                  No conversations yet.
                </p>
                <p className="text-[10px] text-zinc-700 mt-1">
                  Start chatting with Volo!
                </p>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="px-3 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
              Connected Services
            </p>
            {integrations.map((integration) => (
              <button
                key={integration.id}
                onClick={() => setPage('settings')}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 text-left transition-colors group"
              >
                <integration.icon className="w-4 h-4 text-zinc-500 group-hover:text-brand-400 transition-colors" />
                <div className="flex-1">
                  <p className="text-sm text-zinc-300">{integration.name}</p>
                </div>
                <span
                  className={cn(
                    'text-[10px] px-2 py-0.5 rounded-full',
                    integration.connected
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-zinc-800 text-zinc-500'
                  )}
                >
                  {integration.connected ? 'Active' : 'Setup'}
                </span>
              </button>
            ))}
          </>
        )}
      </div>

      {/* Bottom — Dashboard & Settings */}
      <nav className="border-t border-white/5 p-3 space-y-1 overflow-y-auto max-h-[50vh]" role="navigation" aria-label="Main navigation">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setPage(item.id)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors min-h-[44px]',
              currentPage === item.id
                ? 'bg-brand-600/10 text-brand-400'
                : 'hover:bg-white/5 text-zinc-400'
            )}
            aria-label={item.label}
            aria-current={currentPage === item.id ? 'page' : undefined}
          >
            <item.icon className="w-4 h-4" />
            <span className="text-sm">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Toggle button */}
      <button
        onClick={toggleSidebar}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-surface-dark-2 border border-white/10 flex items-center justify-center hover:bg-surface-dark-3 transition-colors z-10 hidden md:flex"
      >
        {sidebarOpen ? (
          <ChevronLeft className="w-3 h-3 text-zinc-400" />
        ) : (
          <ChevronRight className="w-3 h-3 text-zinc-400" />
        )}
      </button>
    </aside>
  );
}
