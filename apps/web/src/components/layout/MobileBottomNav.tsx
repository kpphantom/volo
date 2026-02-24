'use client';

import {
  MessageSquare,
  LayoutDashboard,
  Heart,
  Share2,
  MessagesSquare,
  User,
  Monitor,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore, type Page } from '@/stores/appStore';
import { useAuthStore } from '@/stores/authStore';

const mobileNavItems: { id: Page; icon: typeof MessageSquare; label: string }[] = [
  { id: 'chat', icon: MessageSquare, label: 'Chat' },
  { id: 'dashboard', icon: LayoutDashboard, label: 'Home' },
  { id: 'social', icon: Share2, label: 'Social' },
  { id: 'messages', icon: MessagesSquare, label: 'Messages' },
  { id: 'health', icon: Heart, label: 'Health' },
  { id: 'vscode', icon: Monitor, label: 'VS Code' },
];

export function MobileBottomNav() {
  const { currentPage, setPage } = useAppStore();
  const user = useAuthStore((s) => s.user);

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface-dark-1/95 backdrop-blur-xl border-t border-white/5 safe-area-bottom"
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
                'flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl transition-all min-w-[60px] min-h-[48px]',
                active
                  ? 'text-brand-400'
                  : 'text-zinc-500 active:text-zinc-300'
              )}
              aria-label={item.label}
              aria-current={active ? 'page' : undefined}
            >
              <item.icon className={cn('w-5 h-5', active && 'drop-shadow-[0_0_6px_rgba(92,124,250,0.5)]')} />
              <span className={cn('text-[10px] font-medium', active ? 'text-brand-400' : 'text-zinc-500')}>
                {item.label}
              </span>
              {active && (
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-brand-500" />
              )}
            </button>
          );
        })}
        {/* Profile / More */}
        <button
          onClick={() => setPage('settings')}
          className={cn(
            'flex flex-col items-center gap-0.5 px-3 py-2 rounded-xl transition-all min-w-[60px] min-h-[48px]',
            currentPage === 'settings' ? 'text-brand-400' : 'text-zinc-500 active:text-zinc-300'
          )}
          aria-label="Settings"
        >
          {user?.avatar ? (
            <img src={user.avatar} alt="" className="w-5 h-5 rounded-full" />
          ) : (
            <User className="w-5 h-5" />
          )}
          <span className={cn('text-[10px] font-medium', currentPage === 'settings' ? 'text-brand-400' : 'text-zinc-500')}>
            More
          </span>
        </button>
      </div>
    </nav>
  );
}
