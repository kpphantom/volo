'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bell,
  X,
  Check,
  CheckCheck,
  Info,
  AlertTriangle,
  AlertCircle,
  ShieldAlert,
  Trash2,
} from 'lucide-react';
import { useNotificationStore } from '@/stores/notificationStore';

const typeIcons = {
  info: <Info className="w-4 h-4 text-blue-400" />,
  success: <Check className="w-4 h-4 text-green-400" />,
  warning: <AlertTriangle className="w-4 h-4 text-yellow-400" />,
  error: <AlertCircle className="w-4 h-4 text-red-400" />,
  approval: <ShieldAlert className="w-4 h-4 text-orange-400" />,
};

export function NotificationCenter() {
  const {
    notifications,
    unreadCount,
    panelOpen,
    togglePanel,
    setPanelOpen,
    markRead,
    markAllRead,
    removeNotification,
    clearAll,
  } = useNotificationStore();

  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setPanelOpen(false);
      }
    };
    if (panelOpen) document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [panelOpen, setPanelOpen]);

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell trigger */}
      <button
        onClick={togglePanel}
        className="relative p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Panel */}
      <AnimatePresence>
        {panelOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-80 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden z-50"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Notifications
              </h3>
              <div className="flex items-center gap-1">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className="p-1.5 text-[var(--text-muted)] hover:text-blue-400 transition-colors"
                    title="Mark all read"
                  >
                    <CheckCheck className="w-4 h-4" />
                  </button>
                )}
                {notifications.length > 0 && (
                  <button
                    onClick={clearAll}
                    className="p-1.5 text-[var(--text-muted)] hover:text-red-400 transition-colors"
                    title="Clear all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* List */}
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="py-12 text-center">
                  <Bell className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-40" />
                  <p className="text-sm text-[var(--text-muted)]">No notifications</p>
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    className={`flex items-start gap-3 px-4 py-3 border-b border-[var(--border)] last:border-0 cursor-pointer hover:bg-[var(--bg-primary)] transition-colors ${
                      !n.read ? 'bg-blue-500/5' : ''
                    }`}
                    onClick={() => markRead(n.id)}
                  >
                    <div className="mt-0.5 shrink-0">
                      {typeIcons[n.type]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[var(--text-primary)] font-medium truncate">
                        {n.title}
                      </p>
                      <p className="text-xs text-[var(--text-muted)] line-clamp-2">
                        {n.message}
                      </p>
                      <p className="text-[10px] text-[var(--text-muted)] mt-1">
                        {formatTime(n.timestamp)}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeNotification(n.id);
                      }}
                      className="p-1 text-[var(--text-muted)] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
