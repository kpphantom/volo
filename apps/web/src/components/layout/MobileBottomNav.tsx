'use client';

import { useState } from 'react';
import {
  MessageSquare,
  LayoutDashboard,
  Share2,
  MessagesSquare,
  Grid3X3,
  X,
  Settings,
  History,
  Clock,
  Activity,
  BarChart3,
  Chrome,
  Youtube,
  Heart,
  Terminal,
  Package,
  BookOpen,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore, type Page } from '@/stores/appStore';
import { useTranslation } from '@/lib/i18n';

const mobileNavItems: { id: Page; icon: typeof MessageSquare; labelKey: string }[] = [
  { id: 'chat', icon: MessageSquare, labelKey: 'nav.chat' },
  { id: 'dashboard', icon: LayoutDashboard, labelKey: 'nav.home' },
  { id: 'messages', icon: MessagesSquare, labelKey: 'nav.messages' },
  { id: 'social', icon: Share2, labelKey: 'nav.social' },
];

const moreMenuItems: { id: Page; icon: typeof Settings; labelKey: string }[] = [
  { id: 'settings', icon: Settings, labelKey: 'nav.settings' },
  { id: 'conversations', icon: History, labelKey: 'nav.history' },
  { id: 'standing-orders', icon: Clock, labelKey: 'nav.standingOrders' },
  { id: 'activity', icon: Activity, labelKey: 'nav.activity' },
  { id: 'analytics', icon: BarChart3, labelKey: 'nav.analytics' },
  { id: 'google', icon: Chrome, labelKey: 'nav.google' },
  { id: 'youtube', icon: Youtube, labelKey: 'nav.youtube' },
  { id: 'health', icon: Heart, labelKey: 'nav.health' },
  { id: 'vscode', icon: Terminal, labelKey: 'nav.vscode' },
  { id: 'marketplace', icon: Package, labelKey: 'nav.marketplace' },
  { id: 'docs', icon: BookOpen, labelKey: 'nav.docs' },
];

export function MobileBottomNav() {
  const { currentPage, setPage } = useAppStore();
  const [moreOpen, setMoreOpen] = useState(false);
  const { t } = useTranslation();

  // Hide on chat page — the chat input handles its own bottom-of-screen positioning
  if (currentPage === 'chat') return null;

  return (
    <>
      {/* More menu overlay */}
      {moreOpen && (
        <div className="md:hidden fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm animate-fade-in" onClick={() => setMoreOpen(false)}>
          <div
            className="absolute bottom-0 left-0 right-0 bg-surface-dark-1 border-t border-white/10 rounded-t-2xl safe-area-bottom p-4 pb-24 animate-slide-up-sheet"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">{t('menu.allFeatures')}</h3>
              <button
                onClick={() => setMoreOpen(false)}
                className="p-2 rounded-full hover:bg-white/10 transition-colors"
                aria-label="Close menu"
              >
                <X className="w-5 h-5 text-zinc-400" />
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {moreMenuItems.map((item) => {
                const active = currentPage === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => { setPage(item.id); setMoreOpen(false); }}
                    className={cn(
                      'flex flex-col items-center gap-1.5 p-3 rounded-xl transition-all min-h-[64px] active:scale-95',
                      active
                        ? 'bg-brand-600/15 text-brand-400'
                        : 'text-zinc-400 hover:bg-white/5 active:bg-white/10'
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="text-[11px] font-medium text-center leading-tight">{t(item.labelKey as any)}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Bottom nav bar */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface-dark-1/95 backdrop-blur-xl border-t border-white/5 safe-area-bottom tap-none"
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="flex items-center justify-around px-2 py-1">
          {mobileNavItems.map((item) => {
            const active = currentPage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setPage(item.id)}
                className={cn(
                  'flex flex-col items-center gap-0.5 px-2 py-2 rounded-xl transition-all min-w-0 flex-1 min-h-[48px] active:scale-95 tap-none relative',
                  active
                    ? 'text-brand-400'
                    : 'text-zinc-500 active:text-zinc-300'
                )}
                aria-label={t(item.labelKey as any)}
                aria-current={active ? 'page' : undefined}
              >
                <item.icon className={cn('w-5 h-5', active && 'drop-shadow-[0_0_6px_rgba(92,124,250,0.5)]')} />
                <span className={cn('text-[11px] font-medium', active ? 'text-brand-400' : 'text-zinc-500')}>
                  {t(item.labelKey as any)}
                </span>
                {active && (
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-brand-500" />
                )}
              </button>
            );
          })}
          {/* More */}
          <button
            onClick={() => setMoreOpen(true)}
            className={cn(
              'flex flex-col items-center gap-0.5 px-2 py-2 rounded-xl transition-all min-w-0 flex-1 min-h-[48px]',
              moreOpen ? 'text-brand-400' : 'text-zinc-500 active:text-zinc-300'
            )}
            aria-label="More features"
          >
            <Grid3X3 className="w-5 h-5" />
            <span className={cn('text-[11px] font-medium', moreOpen ? 'text-brand-400' : 'text-zinc-500')}>
              {t('nav.more')}
            </span>
          </button>
        </div>
      </nav>
    </>
  );
}
