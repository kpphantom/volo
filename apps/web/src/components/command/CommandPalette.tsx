'use client';

import { useEffect, useRef, useState } from 'react';
import {
  Search,
  MessageSquare,
  Code,
  TrendingUp,
  Mail,
  Settings,
  Terminal,
  Calendar,
  LayoutDashboard,
  Moon,
  Globe,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/stores/appStore';
import { useChatStore } from '@/stores/chatStore';
import { toast } from 'sonner';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface Command {
  id: string;
  icon: any;
  label: string;
  category: string;
  shortcut?: string;
  action: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const setPage = useAppStore((s) => s.setPage);
  const { clearMessages, sendMessage } = useChatStore();

  const commands: Command[] = [
    {
      id: 'chat',
      icon: MessageSquare,
      label: 'New conversation',
      category: 'General',
      shortcut: '⌘N',
      action: () => { clearMessages(); setPage('chat'); },
    },
    {
      id: 'dashboard',
      icon: LayoutDashboard,
      label: 'Open dashboard',
      category: 'General',
      action: () => setPage('dashboard'),
    },
    {
      id: 'settings',
      icon: Settings,
      label: 'Settings',
      category: 'General',
      shortcut: '⌘,',
      action: () => setPage('settings'),
    },
    {
      id: 'briefing',
      icon: Calendar,
      label: 'Morning briefing',
      category: 'Actions',
      action: () => { setPage('chat'); setTimeout(() => sendMessage('Give me my morning briefing'), 100); },
    },
    {
      id: 'portfolio',
      icon: TrendingUp,
      label: 'Portfolio overview',
      category: 'Actions',
      action: () => { setPage('chat'); setTimeout(() => sendMessage('Show me my portfolio overview and current market prices'), 100); },
    },
    {
      id: 'email',
      icon: Mail,
      label: 'Check email',
      category: 'Actions',
      action: () => { setPage('chat'); setTimeout(() => sendMessage('Check my emails and summarize the important ones'), 100); },
    },
    {
      id: 'deploy',
      icon: Code,
      label: 'Deploy a project',
      category: 'Actions',
      action: () => { setPage('chat'); setTimeout(() => sendMessage('Help me deploy my latest project'), 100); },
    },
    {
      id: 'terminal',
      icon: Terminal,
      label: 'Run terminal command',
      category: 'Actions',
      action: () => { setPage('chat'); setTimeout(() => sendMessage('I need to run some terminal commands'), 100); },
    },
    {
      id: 'social',
      icon: Globe,
      label: 'Social media overview',
      category: 'Actions',
      action: () => { setPage('chat'); setTimeout(() => sendMessage('Give me an overview of my social media'), 100); },
    },
    {
      id: 'theme',
      icon: Moon,
      label: 'Toggle dark mode',
      category: 'Appearance',
      action: () => {
        import('@/stores/themeStore').then(({ useThemeStore }) => {
          const current = useThemeStore.getState().mode;
          const next = current === 'dark' ? 'light' : 'dark';
          useThemeStore.getState().setMode(next);
          document.documentElement.classList.toggle('dark', next === 'dark');
          toast.success(`Switched to ${next} mode`);
        });
      },
    },
  ];

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const filtered = commands.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  );

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => (i + 1) % filtered.length);
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => (i - 1 + filtered.length) % filtered.length);
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) {
          filtered[selectedIndex].action();
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, filtered, selectedIndex]);

  // Reset selection when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) return null;

  const grouped = filtered.reduce(
    (acc, cmd) => {
      if (!acc[cmd.category]) acc[cmd.category] = [];
      acc[cmd.category].push(cmd);
      return acc;
    },
    {} as Record<string, Command[]>
  );

  let flatIndex = 0;

  return (
    <div className="fixed inset-0 z-50 cmd-overlay" onClick={onClose}>
      <div
        className="mx-auto mt-[20vh] w-full max-w-lg animate-slide-up px-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-2xl bg-surface-dark-1 border border-white/10 shadow-2xl overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
            <Search className="w-4 h-4 text-zinc-500" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search commands, actions, anything..."
              className="flex-1 bg-transparent text-sm text-zinc-200 placeholder-zinc-600 outline-none"
            />
            <kbd className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-500 font-mono">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div className="max-h-80 overflow-y-auto py-2">
            {Object.entries(grouped).map(([category, cmds]) => (
              <div key={category}>
                <p className="px-4 py-1.5 text-[10px] font-semibold text-zinc-500 uppercase tracking-wider">
                  {category}
                </p>
                {cmds.map((cmd) => {
                  const thisIndex = flatIndex++;
                  return (
                    <button
                      key={cmd.id}
                      className={cn(
                        'w-full flex items-center gap-3 px-4 py-2.5 transition-colors group',
                        selectedIndex === thisIndex
                          ? 'bg-brand-600/10 text-brand-300'
                          : 'hover:bg-white/5'
                      )}
                      onClick={() => {
                        cmd.action();
                        onClose();
                      }}
                      onMouseEnter={() => setSelectedIndex(thisIndex)}
                    >
                      <cmd.icon className={cn(
                        'w-4 h-4',
                        selectedIndex === thisIndex ? 'text-brand-400' : 'text-zinc-500'
                      )} />
                      <span className="text-sm text-zinc-300 flex-1 text-left">{cmd.label}</span>
                      {cmd.shortcut && (
                        <kbd className="px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-600 font-mono">
                          {cmd.shortcut}
                        </kbd>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="px-4 py-8 text-sm text-zinc-600 text-center">
                No commands found. Try&nbsp;
                <span className="text-brand-400">asking Volo</span> directly.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
