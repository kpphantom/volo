'use client';

import {
  Brain,
  Zap,
  GitBranch,
  Activity,
  BarChart3,
  TrendingUp,
  MessageSquare,
  Shield,
  Cpu,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';
import { useAppStore } from '@/stores/appStore';
import { useChatStore } from '@/stores/chatStore';

import { api, API_URL } from '@/lib/api';

interface SystemStatus {
  api: 'online' | 'offline' | 'checking';
  ai: 'active' | 'setup-needed' | 'checking';
  integrations: number;
  memories: number;
}

export function DashboardPage() {
  const [status, setStatus] = useState<SystemStatus>({
    api: 'checking',
    ai: 'checking',
    integrations: 0,
    memories: 0,
  });
  const [uptime, setUptime] = useState('');
  const setPage = useAppStore((s) => s.setPage);

  useEffect(() => {
    checkSystemHealth();
    const interval = setInterval(() => {
      setUptime(getUptime());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const checkSystemHealth = async () => {
    try {
      await api.get('/health');
      setStatus((s) => ({ ...s, api: 'online' }));
    } catch {
      setStatus((s) => ({ ...s, api: 'offline' }));
    }

    try {
      const data = await api.get<{ ai_configured?: boolean; integrations_count?: number; memories_count?: number; uptime_seconds?: number }>('/api/system/status');
      setStatus((s) => ({
        ...s,
        ai: data?.ai_configured ? 'active' : 'setup-needed',
        integrations: data?.integrations_count || 0,
        memories: data?.memories_count || 0,
      }));
      if (data?.uptime_seconds) {
        const h = Math.floor(data.uptime_seconds / 3600);
        const m = Math.floor((data.uptime_seconds % 3600) / 60);
        setUptime(`${h}h ${m}m`);
      }
    } catch {
      setStatus((s) => ({ ...s, ai: 'setup-needed' }));
    }
  };

  const getUptime = () => {
    if (uptime) return uptime;
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-sm text-zinc-500">Your Volo command center — everything at a glance.</p>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatusCard
            icon={Activity}
            label="API Status"
            value={status.api === 'online' ? 'Online' : status.api === 'checking' ? 'Checking...' : 'Offline'}
            color={status.api === 'online' ? 'emerald' : status.api === 'checking' ? 'amber' : 'red'}
          />
          <StatusCard
            icon={Brain}
            label="AI Agent"
            value={status.ai === 'active' ? 'Active' : status.ai === 'checking' ? 'Checking...' : 'Setup Needed'}
            color={status.ai === 'active' ? 'emerald' : status.ai === 'checking' ? 'amber' : 'amber'}
          />
          <StatusCard
            icon={Zap}
            label="Integrations"
            value={`${status.integrations} Connected`}
            color={status.integrations > 0 ? 'brand' : 'zinc'}
          />
          <StatusCard
            icon={Shield}
            label="Memories"
            value={`${status.memories} Stored`}
            color={status.memories > 0 ? 'brand' : 'zinc'}
          />
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-zinc-400 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <QuickAction
              icon={MessageSquare}
              title="New Conversation"
              description="Start chatting with Volo"
              onClick={() => setPage('chat')}
            />
            <QuickAction
              icon={GitBranch}
              title="Connect GitHub"
              description="Link your repositories"
              onClick={() => setPage('settings')}
            />
            <QuickAction
              icon={TrendingUp}
              title="Market Prices"
              description="Live crypto & stock data"
              onClick={() => {
                useChatStore.getState().setQueuedMessage("What's the price of Bitcoin, Ethereum, and Solana?");
                setPage('chat');
              }}
            />
          </div>
        </div>

        {/* System Info */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Capabilities */}
          <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
            <h3 className="text-sm font-semibold text-zinc-300 mb-4 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-brand-400" />
              Agent Capabilities
            </h3>
            <div className="space-y-3">
              {[
                { name: 'Code Intelligence', status: 'GitHub Token Required', ready: false },
                { name: 'Trading & Finance', status: 'Live crypto prices active', ready: true },
                { name: 'Email & Calendar', status: 'OAuth setup required', ready: false },
                { name: 'Machine Control', status: 'Daemon not installed', ready: false },
                { name: 'Social Media', status: 'API keys required', ready: false },
                { name: 'Web3 & DeFi', status: 'Wallet address required', ready: false },
                { name: 'Memory System', status: 'Active (in-memory)', ready: true },
                { name: 'White-Label', status: 'Configure via API', ready: true },
              ].map((cap) => (
                <div key={cap.name} className="flex items-center justify-between py-1">
                  <span className="text-sm text-zinc-300">{cap.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-zinc-500">{cap.status}</span>
                    <div
                      className={cn(
                        'w-2 h-2 rounded-full',
                        cap.ready ? 'bg-emerald-400' : 'bg-zinc-600'
                      )}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Architecture */}
          <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
            <h3 className="text-sm font-semibold text-zinc-300 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-brand-400" />
              System Architecture
            </h3>
            <div className="space-y-4 text-xs font-mono">
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">Frontend</span>
                <span className="text-zinc-300">Next.js 14 + React 18 + Tailwind CSS</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">Backend</span>
                <span className="text-zinc-300">FastAPI + Python 3.11+</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">AI Model</span>
                <span className="text-zinc-300">Claude (Anthropic) / GPT-4 (OpenAI)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">State</span>
                <span className="text-zinc-300">Zustand + SSE Streaming</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">Database</span>
                <span className="text-zinc-300">PostgreSQL + pgvector (optional)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">Tools</span>
                <span className="text-zinc-300">18 registered (GitHub, Trading, Memory...)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-500 w-24">Local Time</span>
                <span className="text-brand-400">{uptime || '--:--:--'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    emerald: 'text-emerald-400 bg-emerald-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
    red: 'text-red-400 bg-red-500/10',
    brand: 'text-brand-400 bg-brand-500/10',
    zinc: 'text-zinc-400 bg-zinc-500/10',
  };
  const c = colorMap[color] || colorMap.zinc;

  return (
    <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">
          {label}
        </span>
        <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center', c)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-lg font-semibold text-zinc-200">{value}</p>
    </div>
  );
}

function QuickAction({
  icon: Icon,
  title,
  description,
  onClick,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-4 p-4 rounded-2xl bg-surface-dark-2 border border-white/5 hover:border-brand-500/30 hover:bg-surface-dark-3 transition-all text-left group"
    >
      <div className="w-10 h-10 rounded-xl bg-brand-600/10 flex items-center justify-center group-hover:bg-brand-600/20 transition-colors">
        <Icon className="w-5 h-5 text-brand-400" />
      </div>
      <div>
        <p className="text-sm font-medium text-zinc-200">{title}</p>
        <p className="text-[11px] text-zinc-500">{description}</p>
      </div>
    </button>
  );
}
