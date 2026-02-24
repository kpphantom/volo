'use client';

import { useState, useEffect } from 'react';
import {
  Activity,
  MessageSquare,
  Wrench,
  Clock,
  ArrowRight,
  RefreshCw,
  Filter,
} from 'lucide-react';

interface ActivityItem {
  id: string;
  type: string;
  action: string;
  details: string;
  timestamp: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const typeIcons: Record<string, React.ReactNode> = {
  chat: <MessageSquare className="w-4 h-4 text-blue-400" />,
  tool_execution: <Wrench className="w-4 h-4 text-purple-400" />,
  integration: <ArrowRight className="w-4 h-4 text-green-400" />,
  default: <Activity className="w-4 h-4 text-[var(--text-muted)]" />,
};

export function ActivityFeed() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchActivity();
  }, []);

  const fetchActivity = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/activity/feed?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setItems(data.items || []);
      }
    } catch {
      // Placeholder data
      setItems([
        { id: '1', type: 'chat', action: 'Conversation started', details: 'New chat session', timestamp: new Date().toISOString() },
        { id: '2', type: 'tool_execution', action: 'Tool executed', details: 'trading_quote: BTC', timestamp: new Date(Date.now() - 300000).toISOString() },
        { id: '3', type: 'integration', action: 'GitHub synced', details: '3 new commits detected', timestamp: new Date(Date.now() - 600000).toISOString() },
      ]);
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
                  ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent'
              }`}
            >
              {f === 'all' ? 'All' : f.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Timeline */}
        <div className="space-y-1">
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
        </div>
      </div>
    </div>
  );
}
