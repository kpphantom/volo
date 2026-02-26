'use client';

import { useState, useRef, useEffect } from 'react';
import { Search, Command, PanelLeft, Bell, User, LogOut, Moon, Sun, Monitor, Settings, HelpCircle, Globe, X } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore, type ThemeMode } from '@/stores/themeStore';
import { useNotificationStore } from '@/stores/notificationStore';
import { NotificationCenter } from '@/components/notifications/NotificationCenter';
import { Tooltip } from '@/components/ui/Tooltip';
import { LanguagePicker } from '@/components/ui/LanguagePicker';
import { useTranslation } from '@/lib/i18n';
import { cn } from '@/lib/utils';

interface TopBarProps {
  onToggleSidebar: () => void;
  onOpenCommandPalette: () => void;
}

// Map page IDs (kebab-case) → translation keys (camelCase)
const pageKeyMap: Record<string, string> = {
  chat: 'page.chat',
  dashboard: 'page.dashboard',
  settings: 'page.settings',
  activity: 'page.activity',
  'standing-orders': 'page.standingOrders',
  analytics: 'page.analytics',
  marketplace: 'page.marketplace',
  docs: 'page.docs',
  conversations: 'page.conversations',
  google: 'page.google',
  youtube: 'page.youtube',
  social: 'page.social',
  messages: 'page.messages',
  health: 'page.health',
  vscode: 'page.vscode',
};

const themeOptions: { mode: ThemeMode; icon: typeof Sun; label: string }[] = [
  { mode: 'light', icon: Sun, label: 'Light' },
  { mode: 'dark', icon: Moon, label: 'Dark' },
  { mode: 'system', icon: Monitor, label: 'System' },
];

export function TopBar({ onToggleSidebar, onOpenCommandPalette }: TopBarProps) {
  const currentPage = useAppStore((s) => s.currentPage);
  const user    = useAuthStore(s => s.user);
  const logout  = useAuthStore(s => s.logout);
  const mode    = useThemeStore(s => s.mode);
  const setMode = useThemeStore(s => s.setMode);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const { t } = useTranslation();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);


  return (
    <header
      className="h-12 sm:h-14 flex items-center justify-between px-2 sm:px-4 border-b border-white/5 bg-surface-dark-1/50 backdrop-blur-xl"
      role="banner"
    >
      {/* Left */}
      <div className="flex items-center gap-1 sm:gap-3 min-w-0">
        <Tooltip content="Toggle sidebar (⌘B)">
          <button
            onClick={onToggleSidebar}
            className="p-2 sm:p-2.5 rounded-lg hover:bg-white/5 active:bg-white/10 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center tap-none"
            aria-label="Toggle sidebar"
          >
            <PanelLeft className="w-4 h-4 text-zinc-400" />
          </button>
        </Tooltip>
        <nav aria-label="Breadcrumb" className="text-sm text-zinc-500 truncate">
          <span className="text-zinc-300 font-medium hidden sm:inline">Volo</span>
          <span className="mx-2 text-zinc-700 hidden sm:inline" aria-hidden="true">/</span>
          <span aria-current="page" className="truncate">{t((pageKeyMap[currentPage] || 'page.chat') as any)}</span>
        </nav>
      </div>

      {/* Center — Command Palette Trigger */}
      <Tooltip content="Search or ask anything (⌘K)">
        <button
          onClick={onOpenCommandPalette}
          className="flex items-center gap-2 sm:gap-3 px-2.5 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-white/5 hover:bg-white/8 border border-white/5 transition-colors group min-h-[40px] sm:min-h-[44px] tap-none active:scale-[0.98]"
          aria-label="Open command palette"
        >
          <Search className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-xs sm:text-sm text-zinc-500 hidden sm:inline">{t('topbar.search')}</span>
          <kbd className="hidden sm:flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white/5 text-[10px] text-zinc-500 font-mono" aria-hidden="true">
            <Command className="w-2.5 h-2.5" />K
          </kbd>
        </button>
      </Tooltip>

      {/* Right */}
      <div className="flex items-center gap-1">
        {/* Theme Toggle */}
        <div className="hidden sm:flex items-center bg-white/5 rounded-lg p-0.5 mr-1">
          {themeOptions.map((opt) => (
            <Tooltip key={opt.mode} content={`${opt.label} mode`}>
              <button
                onClick={() => setMode(opt.mode)}
                className={cn(
                  'p-2 rounded-md transition-all min-h-[36px] min-w-[36px] flex items-center justify-center',
                  mode === opt.mode ? 'bg-brand-500/20 text-brand-400' : 'text-zinc-500 hover:text-zinc-300'
                )}
                aria-label={`Switch to ${opt.label} mode`}
                aria-pressed={mode === opt.mode}
              >
                <opt.icon className="w-3.5 h-3.5" />
              </button>
            </Tooltip>
          ))}
        </div>

        {/* Notifications */}
        <NotificationCenter />

        {/* User Menu */}
        <div className="relative" ref={menuRef}>
          <Tooltip content={user?.name || 'Account'}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-11 h-11 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center hover:shadow-lg hover:shadow-brand-500/20 transition-all"
              aria-label="User menu"
              aria-expanded={showUserMenu}
              aria-haspopup="true"
            >
              {user?.avatar ? (
                <img src={user.avatar} alt={user.name || 'User avatar'} width={44} height={44} className="w-full h-full rounded-full object-cover" />
              ) : (
                <span className="text-sm font-bold text-white">
                  {user?.name?.charAt(0)?.toUpperCase() || <User className="w-4 h-4 text-white" />}
                </span>
              )}
            </button>
          </Tooltip>

          {/* Dropdown — bottom sheet on mobile, absolute dropdown on desktop */}
          {showUserMenu && (
            <>
              {/* Mobile backdrop */}
              <div
                className="sm:hidden fixed inset-0 z-[60] bg-black/50 backdrop-blur-sm animate-fade-in"
                onClick={() => setShowUserMenu(false)}
              />
              <div
                className={cn(
                  'z-[70] rounded-xl bg-surface-dark-2 border border-white/5 shadow-xl shadow-black/30 py-1 animate-fade-in',
                  // Mobile: bottom sheet
                  'fixed bottom-0 left-0 right-0 rounded-b-none sm:rounded-xl',
                  // Desktop: absolute dropdown
                  'sm:absolute sm:right-0 sm:top-full sm:mt-2 sm:w-56 sm:bottom-auto sm:left-auto'
                )}
                role="menu"
                aria-label="User menu options"
              >
                {/* Mobile drag handle */}
                <div className="sm:hidden flex justify-center pt-2 pb-1">
                  <div className="w-10 h-1 rounded-full bg-white/20" />
                </div>
                <div className="px-4 py-3 border-b border-white/5">
                  <p className="text-sm font-medium text-white truncate">{user?.name || 'User'}</p>
                  <p className="text-xs text-zinc-500 truncate">{user?.email}</p>
                  {user?.provider && (
                    <span className="inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 capitalize">
                      {user.provider}
                    </span>
                  )}
                </div>
                <button
                  onClick={() => { useAppStore.getState().setPage('settings'); setShowUserMenu(false); }}
                  className="w-full flex items-center gap-3 px-4 py-3 sm:py-2.5 text-sm text-zinc-400 hover:text-white hover:bg-white/5 transition-colors min-h-[48px] sm:min-h-[44px]"
                  role="menuitem"
                >
                  <Settings className="w-4 h-4" />
                  {t('menu.settings')}
                </button>
                <button
                  onClick={() => { useAppStore.getState().setPage('docs'); setShowUserMenu(false); }}
                  className="w-full flex items-center gap-3 px-4 py-3 sm:py-2.5 text-sm text-zinc-400 hover:text-white hover:bg-white/5 transition-colors min-h-[48px] sm:min-h-[44px]"
                  role="menuitem"
                >
                  <HelpCircle className="w-4 h-4" />
                  {t('menu.helpDocs')}
                </button>
                {/* Theme toggle — always visible in dropdown, hidden on desktop TopBar */}
                <div className="sm:hidden border-t border-white/5 pt-1 mt-1">
                  <div className="px-4 py-2 flex items-center justify-between">
                    <span className="text-xs text-zinc-500">{t('menu.theme')}</span>
                    <div className="flex items-center bg-white/5 rounded-lg p-0.5">
                      {themeOptions.map((opt) => (
                        <button
                          key={opt.mode}
                          onClick={() => setMode(opt.mode)}
                          className={cn(
                            'p-2 rounded-md transition-all min-h-[36px] min-w-[36px] flex items-center justify-center',
                            mode === opt.mode ? 'bg-brand-500/20 text-brand-400' : 'text-zinc-500'
                          )}
                          aria-label={`${opt.label} mode`}
                        >
                          <opt.icon className="w-3.5 h-3.5" />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                {/* Language picker */}
                <div className="border-t border-white/5 mt-1 pt-1">
                  <LanguagePicker variant="inline" />
                </div>
                <div className="border-t border-white/5 mt-1 pt-1">
                  <button
                    onClick={() => { logout(); setShowUserMenu(false); }}
                    className="w-full flex items-center gap-3 px-4 py-3 sm:py-2.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/5 transition-colors min-h-[48px] sm:min-h-[44px]"
                    role="menuitem"
                  >
                    <LogOut className="w-4 h-4" />
                    {t('menu.signOut')}
                  </button>
                </div>
                {/* Safe area padding for mobile */}
                <div className="sm:hidden h-6" />
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
