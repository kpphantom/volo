'use client';

import { useState, useEffect } from 'react';
import {
  Activity,
  MessageSquare,
  Wrench,
  Clock,
  ArrowRight,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface ActivityItem {
  id: string;
  type: string;
  action: string;
  details: string;
  timestamp: string;
}

const typeIcons: Record<string, React.ReactNode> = {
  chat: <MessageSquare className="w-4 h-4 text-brand-400" />,
  tool_execution: <Wrench className="w-4 h-4 text-purple-400" />,
  integration: <ArrowRight className="w-4 h-4 text-green-400" />,
  default: <Activity className="w-4 h-4 text-[var(--text-muted)]" />,
};

export function ActivityFeed() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchActivity();
  }, []);

  const fetchActivity = async () => {
    setLoading(true);
    setError(false);
    try {
      const data = await api.get<{ items: ActivityItem[] }>('/api/activity/feed?limit=50');
      setItems(data?.items || []);
    } catch {
      setError(true);
      toast.error('Failed to load activity feed');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: string) => {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  };

  const filtered = filter === 'all' ? items : items.filter((i) => i.type === filter);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Activity</h1>
            <p className="text-sm text-[var(--text-muted)]">Everything happening in your Volo workspace</p>
          </div>
          <button
            onClick={fetchActivity}
            className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6">
          {['all', 'chat', 'tool_execution', 'integration'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                filter === f
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/30'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent'
              }`}
            >
              {f === 'all' ? 'All' : f.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Loading Skeleton */}
        {loading && (
          <div className="space-y-1">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg animate-pulse">
                <div className="w-4 h-4 rounded bg-[var(--bg-secondary)] mt-0.5 shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-[var(--bg-secondary)] rounded w-3/4" />
                  <div className="h-3 bg-[var(--bg-secondary)] rounded w-1/2" />
                </div>
                <div className="h-3 bg-[var(--bg-secondary)] rounded w-16 shrink-0" />
              </div>
            ))}
          </div>
        )}

        {/* Timeline */}
        {!loading && <div className="space-y-1">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-3 p-3 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors group"
            >
              <div className="mt-0.5 shrink-0">
                {typeIcons[item.type] || typeIcons.default}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--text-primary)]">{item.action}</p>
                <p className="text-xs text-[var(--text-muted)]">{item.details}</p>
              </div>
              <div className="flex items-center gap-1 text-xs text-[var(--text-muted)] shrink-0">
                <Clock className="w-3 h-3" />
                {formatTime(item.timestamp)}
              </div>
            </div>
          ))}

          {filtered.length === 0 && !loading && (
            <div className="py-12 text-center">
              <Activity className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-40" />
              <p className="text-sm text-[var(--text-muted)]">No activity yet</p>
            </div>
          )}
        </div>}
      </div>
    </div>
  );
}
