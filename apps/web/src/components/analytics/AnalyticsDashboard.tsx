'use client';

import { useState, useEffect } from 'react';
import {
  BarChart3,
  TrendingUp,
  MessageSquare,
  Wrench,
  Clock,
  ArrowUp,
  ArrowDown,
  RefreshCw,
  Layers,
  Zap,
} from 'lucide-react';

interface UsageStat {
  label: string;
  value: string;
  change: number;
  icon: React.ReactNode;
}

interface ToolUsage {
  name: string;
  count: number;
  percentage: number;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<UsageStat[]>([]);
  const [toolUsage, setToolUsage] = useState<ToolUsage[]>([]);
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [usageRes, convoRes] = await Promise.all([
        fetch(`${API}/api/analytics/usage`),
        fetch(`${API}/api/analytics/conversations`),
      ]);
      if (usageRes.ok) {
        const usage = await usageRes.json();
        const convo = convoRes.ok ? await convoRes.json() : {};
        setStats([
          {
            label: 'Conversations',
            value: String(convo.total || 0),
            change: 12,
            icon: <MessageSquare className="w-5 h-5" />,
          },
          {
            label: 'Messages',
            value: String(usage.messages_today || 0),
            change: 8,
            icon: <Zap className="w-5 h-5" />,
          },
          {
            label: 'Tool Calls',
            value: String(usage.tool_calls || 0),
            change: -3,
            icon: <Wrench className="w-5 h-5" />,
          },
          {
            label: 'Avg Response',
            value: `${usage.avg_response_ms || 0}ms`,
            change: -15,
            icon: <Clock className="w-5 h-5" />,
          },
        ]);
      }
    } catch {
      // Placeholder
      setStats([
        { label: 'Conversations', value: '47', change: 12, icon: <MessageSquare className="w-5 h-5" /> },
        { label: 'Messages', value: '284', change: 8, icon: <Zap className="w-5 h-5" /> },
        { label: 'Tool Calls', value: '156', change: -3, icon: <Wrench className="w-5 h-5" /> },
        { label: 'Avg Response', value: '1.2s', change: -15, icon: <Clock className="w-5 h-5" /> },
      ]);
      setToolUsage([
        { name: 'trading_quote', count: 45, percentage: 29 },
        { name: 'github_list_repos', count: 32, percentage: 21 },
        { name: 'store_memory', count: 28, percentage: 18 },
        { name: 'search_memory', count: 22, percentage: 14 },
        { name: 'email_list_inbox', count: 15, percentage: 10 },
        { name: 'machine_run_command', count: 14, percentage: 9 },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Analytics</h1>
            <p className="text-sm text-[var(--text-muted)]">Track your Volo usage and performance</p>
          </div>
          <div className="flex items-center gap-2">
            {['24h', '7d', '30d', '90d'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                  timeRange === range
                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent'
                }`}
              >
                {range}
              </button>
            ))}
            <button
              onClick={fetchAnalytics}
              className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] ml-2"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[var(--text-muted)]">{stat.icon}</span>
                <span
                  className={`flex items-center gap-0.5 text-xs font-medium ${
                    stat.change >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {stat.change >= 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
                  {Math.abs(stat.change)}%
                </span>
              </div>
              <p className="text-2xl font-bold text-[var(--text-primary)]">{stat.value}</p>
              <p className="text-xs text-[var(--text-muted)] mt-1">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Tool Usage */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <Layers className="w-5 h-5 text-blue-400" />
            Tool Usage
          </h2>
          <div className="space-y-3">
            {toolUsage.map((tool) => (
              <div key={tool.name} className="flex items-center gap-4">
                <span className="text-sm text-[var(--text-secondary)] w-40 truncate font-mono">
                  {tool.name}
                </span>
                <div className="flex-1 h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${tool.percentage}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--text-muted)] w-12 text-right">
                  {tool.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Usage Chart Placeholder */}
        <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            Usage Over Time
          </h2>
          <div className="h-48 flex items-end gap-1">
            {Array.from({ length: 30 }, (_, i) => {
              const height = 20 + Math.random() * 80;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full bg-blue-500/30 hover:bg-blue-500/50 rounded-t transition-colors"
                    style={{ height: `${height}%` }}
                  />
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2 text-[10px] text-[var(--text-muted)]">
            <span>30 days ago</span>
            <span>Today</span>
          </div>
        </div>
      </div>
    </div>
  );
}
