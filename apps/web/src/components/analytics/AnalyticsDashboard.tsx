'use client';

import { useState, useEffect } from 'react';
import {
  BarChart3,
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

import { api } from '@/lib/api';

export function AnalyticsDashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<UsageStat[]>([]);
  const [toolUsage, setToolUsage] = useState<ToolUsage[]>([]);
  const [timeRange, setTimeRange] = useState('7d');
  const [dailyData, setDailyData] = useState<number[]>([]);

  useEffect(() => {
    fetchAnalytics();
  }, [timeRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const [usage, convo] = await Promise.all([
        api.get<{ messages_today?: number; tool_calls?: number; avg_response_ms?: number; tools?: ToolUsage[]; daily?: number[] }>(`/api/analytics/usage?range=${timeRange}`),
        api.get<{ total?: number; change?: number }>(`/api/analytics/conversations?range=${timeRange}`),
      ]);
      setStats([
        {
          label: 'Conversations',
          value: String(convo?.total || 0),
          change: convo?.change || 0,
          icon: <MessageSquare className="w-5 h-5" />,
        },
        {
          label: 'Messages',
          value: String(usage?.messages_today || 0),
          change: 0,
          icon: <Zap className="w-5 h-5" />,
        },
        {
          label: 'Tool Calls',
          value: String(usage?.tool_calls || 0),
          change: 0,
          icon: <Wrench className="w-5 h-5" />,
        },
        {
          label: 'Avg Response',
          value: `${usage?.avg_response_ms || 0}ms`,
          change: 0,
          icon: <Clock className="w-5 h-5" />,
        },
      ]);
      if (usage?.tools) setToolUsage(usage.tools);
      if (usage?.daily) setDailyData(usage.daily);
    } catch {
      setStats([
        { label: 'Conversations', value: '0', change: 0, icon: <MessageSquare className="w-5 h-5" /> },
        { label: 'Messages', value: '0', change: 0, icon: <Zap className="w-5 h-5" /> },
        { label: 'Tool Calls', value: '0', change: 0, icon: <Wrench className="w-5 h-5" /> },
        { label: 'Avg Response', value: '0ms', change: 0, icon: <Clock className="w-5 h-5" /> },
      ]);
      setToolUsage([]);
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
                    ? 'bg-brand-500/10 text-brand-400 border border-brand-500/30'
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

        {/* Loading Skeleton */}
        {loading && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-4 animate-pulse">
                  <div className="flex items-center justify-between mb-3">
                    <div className="w-5 h-5 rounded bg-[var(--bg-primary)]" />
                    <div className="w-10 h-3 rounded bg-[var(--bg-primary)]" />
                  </div>
                  <div className="h-8 bg-[var(--bg-primary)] rounded w-20 mb-1" />
                  <div className="h-3 bg-[var(--bg-primary)] rounded w-24" />
                </div>
              ))}
            </div>
            <div className="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl p-6 mb-8 animate-pulse">
              <div className="h-6 bg-[var(--bg-primary)] rounded w-32 mb-4" />
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="h-4 bg-[var(--bg-primary)] rounded w-40" />
                    <div className="flex-1 h-2 bg-[var(--bg-primary)] rounded-full" />
                    <div className="h-3 bg-[var(--bg-primary)] rounded w-12" />
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Stats Cards */}
        {!loading && <>
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
            <Layers className="w-5 h-5 text-brand-400" />
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
                    className="h-full bg-brand-500 rounded-full transition-all"
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
            {(dailyData.length > 0 ? dailyData : Array.from({ length: 30 }, () => 0)).map((val, i) => {
              const maxVal = Math.max(...(dailyData.length > 0 ? dailyData : [1]));
              const height = maxVal > 0 ? (val / maxVal) * 100 : 5;
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div
                    className="w-full bg-brand-500/30 hover:bg-brand-500/50 rounded-t transition-colors"
                    style={{ height: `${Math.max(height, 2)}%` }}
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
        </>}
      </div>
    </div>
  );
}
