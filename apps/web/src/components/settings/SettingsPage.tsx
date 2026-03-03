'use client';

import { useState, useEffect } from 'react';
import {
  Settings,
  Key,
  Palette,
  Bell,
  Shield,
  Save,
  Check,
  ExternalLink,
  Eye,
  EyeOff,
  Brain,
  Github,
  TrendingUp,
  Mail,
  Globe,
  RefreshCw,
  Landmark,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { api, API_URL } from '@/lib/api';

type SettingsTab = 'api-keys' | 'integrations' | 'appearance' | 'accessibility' | 'notifications';

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('integrations');

  const tabs = [
    { id: 'api-keys' as const, label: 'API Keys', icon: Key },
    { id: 'integrations' as const, label: 'Integrations', icon: Globe },
    { id: 'appearance' as const, label: 'Appearance', icon: Palette },
    { id: 'accessibility' as const, label: 'Accessibility', icon: Settings },
    { id: 'notifications' as const, label: 'Notifications', icon: Bell },
  ];

  return (
    <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-1">Settings</h1>
          <p className="text-sm text-zinc-500">Configure your Volo instance.</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-8 p-1 rounded-xl bg-surface-dark-2 border border-white/5 overflow-x-auto scrollbar-hide" role="tablist" aria-label="Settings tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all min-h-[44px] flex-shrink-0 whitespace-nowrap',
                activeTab === tab.id
                  ? 'bg-brand-600 text-white'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5'
              )}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`panel-${tab.id}`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div role="tabpanel" id={`panel-${activeTab}`} aria-label={activeTab}>
          {activeTab === 'api-keys' && <ApiKeysSection />}
          {activeTab === 'integrations' && <IntegrationsSection />}
          {activeTab === 'appearance' && <AppearanceSection />}
          {activeTab === 'accessibility' && <AccessibilitySection />}
          {activeTab === 'notifications' && <NotificationsSection />}
        </div>
      </div>
    </div>
  );
}

function ApiKeysSection() {
  const [anthropicKey, setAnthropicKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<Record<string, 'success' | 'error' | null>>({});

  const toggleShow = (key: string) => {
    setShowKeys((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const saveKey = async (keyName: string, value: string) => {
    if (!value.trim()) return;
    setSaving(true);
    try {
      await api.post('/api/config/keys', { key_name: keyName, key_value: value });
      toast.success(`${keyName} saved successfully`);
      setTestResult((prev) => ({ ...prev, [keyName]: 'success' }));
    } catch {
      toast.error('Failed to save key — check API server');
      setTestResult((prev) => ({ ...prev, [keyName]: 'error' }));
    }
    setSaving(false);
  };

  const testKey = async (keyName: string) => {
    try {
      const data = await api.get<{ valid: boolean; message?: string }>(`/api/config/test-key/${keyName}`);
      if (data.valid) {
        toast.success(`${keyName} is valid!`);
        setTestResult((prev) => ({ ...prev, [keyName]: 'success' }));
      } else {
        toast.error(`${keyName} is invalid: ${data.message || 'check the key'}`);
        setTestResult((prev) => ({ ...prev, [keyName]: 'error' }));
      }
    } catch {
      toast.error('Cannot reach API server');
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-brand-600/10 flex items-center justify-center">
            <Brain className="w-5 h-5 text-brand-400" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">AI Model Keys</h3>
            <p className="text-xs text-zinc-500">Required for full agent capabilities</p>
          </div>
        </div>

        <div className="space-y-4">
          <KeyInput
            label="Anthropic API Key"
            placeholder="sk-ant-..."
            value={anthropicKey}
            onChange={setAnthropicKey}
            show={showKeys['anthropic']}
            onToggleShow={() => toggleShow('anthropic')}
            onSave={() => saveKey('ANTHROPIC_API_KEY', anthropicKey)}
            onTest={() => testKey('ANTHROPIC_API_KEY')}
            status={testResult['ANTHROPIC_API_KEY']}
            saving={saving}
            helpUrl="https://console.anthropic.com/"
          />
          <KeyInput
            label="OpenAI API Key"
            placeholder="sk-..."
            value={openaiKey}
            onChange={setOpenaiKey}
            show={showKeys['openai']}
            onToggleShow={() => toggleShow('openai')}
            onSave={() => saveKey('OPENAI_API_KEY', openaiKey)}
            onTest={() => testKey('OPENAI_API_KEY')}
            status={testResult['OPENAI_API_KEY']}
            saving={saving}
            helpUrl="https://platform.openai.com/api-keys"
          />
        </div>
      </div>

      <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-zinc-700/50 flex items-center justify-center">
            <Github className="w-5 h-5 text-zinc-300" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">Integration Tokens</h3>
            <p className="text-xs text-zinc-500">Connect external services</p>
          </div>
        </div>

        <div className="space-y-4">
          <KeyInput
            label="GitHub Personal Access Token"
            placeholder="ghp_..."
            value={githubToken}
            onChange={setGithubToken}
            show={showKeys['github']}
            onToggleShow={() => toggleShow('github')}
            onSave={() => saveKey('GITHUB_TOKEN', githubToken)}
            onTest={() => testKey('GITHUB_TOKEN')}
            status={testResult['GITHUB_TOKEN']}
            saving={saving}
            helpUrl="https://github.com/settings/tokens"
          />
        </div>
      </div>

      {/* Info */}
      <div className="rounded-xl bg-brand-600/5 border border-brand-500/10 p-4">
        <div className="flex gap-3">
          <Shield className="w-4 h-4 text-brand-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-zinc-400 leading-relaxed">
            <p className="font-medium text-zinc-300 mb-1">Security Note</p>
            <p>
              API keys are stored in your server&apos;s environment and never sent to
              any third party. All keys are kept in memory on your machine only.
              For production, use encrypted environment variables.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function KeyInput({
  label,
  placeholder,
  value,
  onChange,
  show,
  onToggleShow,
  onSave,
  onTest,
  status,
  saving,
  helpUrl,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  onToggleShow: () => void;
  onSave: () => void;
  onTest: () => void;
  status: 'success' | 'error' | null | undefined;
  saving: boolean;
  helpUrl: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-zinc-400">{label}</label>
        <a
          href={helpUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[10px] text-brand-400 hover:text-brand-300 flex items-center gap-1"
        >
          Get key <ExternalLink className="w-2.5 h-2.5" />
        </a>
      </div>
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="flex-1 relative">
          <input
            type={show ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={cn(
              'w-full px-3 py-2.5 pr-10 rounded-xl bg-surface-dark-0 border text-sm text-zinc-200 placeholder-zinc-600 outline-none transition-colors font-mono',
              status === 'success'
                ? 'border-emerald-500/50'
                : status === 'error'
                ? 'border-red-500/50'
                : 'border-white/10 focus:border-brand-500/50'
            )}
          />
          <button
            onClick={onToggleShow}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <div className="flex gap-2">
        <button
          onClick={onSave}
          disabled={!value.trim() || saving}
          className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium transition-colors flex items-center justify-center gap-1.5 min-h-[44px]"
        >
          {saving ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : status === 'success' ? (
            <Check className="w-3.5 h-3.5" />
          ) : (
            <Save className="w-3.5 h-3.5" />
          )}
          Save
        </button>
        <button
          onClick={onTest}
          className="flex-1 sm:flex-none px-3 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-zinc-200 text-sm transition-colors min-h-[44px]"
        >
          Test
        </button>
        </div>
      </div>
    </div>
  );
}

function IntegrationsSection() {
  const [integrations, setIntegrations] = useState([
    {
      name: 'GitHub',
      icon: Github,
      category: 'Code',
      description: 'Access repos, PRs, issues, CI/CD',
      connected: false,
      color: 'zinc',
      keyName: 'GITHUB_TOKEN',
    },
    {
      name: 'Gmail',
      icon: Mail,
      category: 'Communication',
      description: 'Email triage, auto-draft, inbox management',
      connected: false,
      color: 'red',
      keyName: 'GOOGLE_OAUTH',
    },
    {
      name: 'Google Calendar',
      icon: Globe,
      category: 'Communication',
      description: 'Schedule events, detect conflicts, meeting briefs',
      connected: false,
      color: 'blue',
      keyName: 'GOOGLE_OAUTH',
    },
    {
      name: 'Alpaca Trading',
      icon: TrendingUp,
      category: 'Finance',
      description: 'Stock trading, portfolio, market data',
      connected: false,
      color: 'emerald',
      keyName: 'ALPACA_API_KEY',
    },
    {
      name: 'CoinGecko',
      icon: TrendingUp,
      category: 'Finance',
      description: 'Live crypto prices (no API key needed)',
      connected: true,
      color: 'amber',
      keyName: '',
    },
    {
      name: 'Plaid',
      icon: Landmark,
      category: 'Finance',
      description: 'Bank accounts, transactions, budgeting',
      connected: false,
      color: 'emerald',
      keyName: 'PLAID',
    },
  ]);

  useEffect(() => {
    api.get<{ github?: boolean; trading?: boolean; email?: boolean }>('/api/system/status')
      .then((data) => {
        setIntegrations((prev) =>
          prev.map((int) => {
            if (int.name === 'GitHub' && data.github) return { ...int, connected: true };
            if (int.name === 'Alpaca Trading' && data.trading) return { ...int, connected: true };
            if (int.name === 'Gmail' && data.email) return { ...int, connected: true };
            if (int.name === 'Google Calendar' && data.email) return { ...int, connected: true };
            return int;
          })
        );
      })
      .catch(() => {});

    // Check Plaid status
    api.get<{ connected?: boolean }>('/api/finance/status')
      .then((data) => {
        if (data.connected) {
          setIntegrations((prev) =>
            prev.map((int) => int.name === 'Plaid' ? { ...int, connected: true } : int)
          );
        }
      })
      .catch(() => {});
  }, []);

  const handleConnect = (int: typeof integrations[0]) => {
    if (int.name === 'Gmail' || int.name === 'Google Calendar') {
      api.get<{ auth_url?: string }>('/api/google/auth-url')
        .then((data) => {
          if (data.auth_url) window.open(data.auth_url, '_blank', 'width=500,height=600');
          else toast.info('Set up Google OAuth credentials in your .env first');
        })
        .catch(() => toast.error('Could not get Google auth URL'));
    } else if (int.name === 'Plaid') {
      toast.info('Set PLAID_CLIENT_ID & PLAID_SECRET in your .env, then use the Finance page to link your bank via Plaid Link');
    } else {
      toast.info(`Add your ${int.keyName} in the API Keys tab to connect ${int.name}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Core Integrations */}
      <div>
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Core Services</h3>
        <div className="space-y-3">
          {integrations.map((int) => (
            <div
              key={int.name}
              className="flex items-center justify-between p-4 sm:p-5 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <div className="flex items-center gap-3 sm:gap-4">
                <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center bg-white/5')}>
                  <int.icon className="w-5 h-5 text-zinc-400" />
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-200">{int.name}</p>
                  <p className="text-xs text-zinc-500 hidden sm:block">{int.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 sm:gap-3">
                <span
                  className={cn(
                    'text-[10px] px-2 sm:px-2.5 py-1 rounded-full font-medium',
                    int.connected
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-zinc-800 text-zinc-500'
                  )}
                >
                  {int.connected ? 'Connected' : 'Not Connected'}
                </span>
                {!int.connected && (
                  <button
                    onClick={() => handleConnect(int)}
                    className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Social Media */}
      <SocialIntegrationsSection />

      {/* Messaging */}
      <MessagingIntegrationsSection />
    </div>
  );
}

function SocialIntegrationsSection() {
  const [socialPlatforms, setSocialPlatforms] = useState<{ id: string; name: string; connected: boolean; username?: string; color: string }[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.get<{ platforms: any[] }>('/api/social/connect/status')
      .then((data) => setSocialPlatforms(data.platforms || []))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const handleConnect = async (platformId: string) => {
    try {
      const data = await api.get<{ url: string }>(`/api/social/connect/${platformId}`);
      if (data.url) window.location.href = data.url;
    } catch {
      toast.error(`Failed to start ${platformId} connection`);
    }
  };

  const handleDisconnect = async (platformId: string) => {
    try {
      await api.delete(`/api/social/connect/${platformId}`);
      toast.success(`Disconnected from ${platformId}`);
      setSocialPlatforms((prev) => prev.map((p) => p.id === platformId ? { ...p, connected: false, username: undefined } : p));
    } catch {
      toast.error('Failed to disconnect');
    }
  };

  const socialIcons: Record<string, string> = {
    twitter: '𝕏', instagram: '📸', tiktok: '🎵', facebook: '📘', reddit: '🔴', linkedin: '💼',
  };

  return (
    <div>
      <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Social Media</h3>
      <div className="space-y-3">
        {socialPlatforms.map((p) => (
          <div
            key={p.id}
            className="flex items-center justify-between p-4 rounded-2xl bg-surface-dark-2 border border-white/5"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-lg">
                {socialIcons[p.id] || '🌐'}
              </div>
              <div>
                <p className="text-sm font-medium text-zinc-200 capitalize">{p.name}</p>
                {p.username && <p className="text-xs text-zinc-500">@{p.username}</p>}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className={cn(
                'text-[10px] px-2.5 py-1 rounded-full font-medium',
                p.connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-800 text-zinc-500'
              )}>
                {p.connected ? 'Connected' : 'Not Connected'}
              </span>
              {p.connected ? (
                <button
                  onClick={() => handleDisconnect(p.id)}
                  className="px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 text-xs font-medium transition-colors"
                >
                  Disconnect
                </button>
              ) : (
                <button
                  onClick={() => handleConnect(p.id)}
                  className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors"
                >
                  Connect
                </button>
              )}
            </div>
          </div>
        ))}
        {socialPlatforms.length === 0 && loaded && (
          <p className="text-sm text-zinc-500 text-center py-4">No social platforms configured</p>
        )}
        {!loaded && (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-2xl bg-surface-dark-2 border border-white/5 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-white/5" />
                  <div className="space-y-1.5"><div className="h-4 bg-white/5 rounded w-24" /><div className="h-3 bg-white/5 rounded w-16" /></div>
                </div>
                <div className="h-5 bg-white/5 rounded-full w-20" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MessagingIntegrationsSection() {
  const [messagingPlatforms, setMessagingPlatforms] = useState<{ id: string; name: string; connected: boolean; icon: string; color: string; has_2fa?: boolean }[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [connectModal, setConnectModal] = useState<{ platform: string; name: string } | null>(null);
  const [tokenInput, setTokenInput] = useState('');
  const [extraInput, setExtraInput] = useState('');
  const [connecting, setConnecting] = useState(false);

  const fetchPlatforms = () => {
    api.get<{ platforms: any[] }>('/api/messages/platforms')
      .then((data) => setMessagingPlatforms(data.platforms || []))
      .catch(() => {})
      .finally(() => setLoaded(true));
  };

  useEffect(() => { fetchPlatforms(); }, []);

  const platformEmojis: Record<string, string> = {
    telegram: '✈️', whatsapp: '💬', whatsapp_business: '💼', imessage: '🍎', signal: '🔒', discord: '🎮', slack: '💼',
  };

  const platformHelp: Record<string, { label: string; placeholder: string; helpText: string; helpUrl: string; extraField?: { label: string; placeholder: string } }> = {
    telegram: {
      label: 'Bot Token',
      placeholder: '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
      helpText: 'Create a bot via @BotFather on Telegram to get your token.',
      helpUrl: 'https://core.telegram.org/bots#botfather',
    },
    whatsapp: {
      label: 'Access Token',
      placeholder: 'EAAxxxxxxx...',
      helpText: 'Get your WhatsApp Cloud API token from Meta Business Suite.',
      helpUrl: 'https://developers.facebook.com/docs/whatsapp/cloud-api/get-started',
      extraField: { label: 'Phone Number ID', placeholder: '1234567890' },
    },
    whatsapp_business: {
      label: 'Business API Token',
      placeholder: 'EAAxxxxxxx...',
      helpText: 'Get your WhatsApp Business API token from Meta.',
      helpUrl: 'https://business.whatsapp.com/developers/developer-hub',
      extraField: { label: 'Phone Number ID', placeholder: '1234567890' },
    },
    discord: {
      label: 'Bot Token',
      placeholder: 'NzkyNzE1NDU0MTk2...',
      helpText: 'Create a bot in the Discord Developer Portal.',
      helpUrl: 'https://discord.com/developers/applications',
    },
    signal: {
      label: 'Signal CLI REST API URL',
      placeholder: 'http://localhost:8080',
      helpText: 'Run signal-cli-rest-api container and provide its URL.',
      helpUrl: 'https://github.com/bbernhard/signal-cli-rest-api',
    },
  };

  const handleSlackConnect = async () => {
    try {
      const data = await api.get<{ url: string }>('/api/auth/slack');
      if (data.url) window.location.href = data.url;
    } catch {
      toast.error('Slack OAuth not configured — set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET');
    }
  };

  const handleTokenConnect = async () => {
    if (!connectModal || !tokenInput.trim()) return;
    setConnecting(true);
    try {
      const extra: Record<string, string> = {};
      if (extraInput.trim()) {
        if (connectModal.platform === 'whatsapp' || connectModal.platform === 'whatsapp_business') {
          extra.phone_id = extraInput.trim();
        }
      }
      await api.post('/api/auth/connect-messaging', {
        platform: connectModal.platform,
        token: tokenInput.trim(),
        extra,
      });
      toast.success(`${connectModal.name} connected!`);
      setConnectModal(null);
      setTokenInput('');
      setExtraInput('');
      fetchPlatforms();
    } catch {
      toast.error('Failed to connect — check your token');
    } finally {
      setConnecting(false);
    }
  };

  return (
    <div>
      <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Messaging</h3>
      <div className="space-y-3">
        {messagingPlatforms.map((p) => {
          const isSlack = p.id === 'slack';
          const isIMessage = p.id === 'imessage';
          const canConnect = !isIMessage; // iMessage auto-detects

          return (
            <div
              key={p.id}
              className="flex items-center justify-between p-4 rounded-2xl bg-surface-dark-2 border border-white/5"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-lg">
                  {platformEmojis[p.id] || '💬'}
                </div>
                <div>
                  <p className="text-sm font-medium text-zinc-200">{p.name}</p>
                  <p className="text-xs text-zinc-500">
                    {p.connected ? 'Connected & receiving messages' : isIMessage ? 'Auto-detected on macOS' : isSlack ? 'Connect via OAuth' : 'Requires API token'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn(
                  'text-[10px] px-2.5 py-1 rounded-full font-medium',
                  p.connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-800 text-zinc-500'
                )}>
                  {p.connected ? 'Connected' : 'Not Connected'}
                </span>
                {!p.connected && canConnect && (
                  <button
                    onClick={() => {
                      if (isSlack) {
                        handleSlackConnect();
                      } else {
                        setConnectModal({ platform: p.id, name: p.name });
                        setTokenInput('');
                        setExtraInput('');
                      }
                    }}
                    className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium transition-colors"
                  >
                    Connect
                  </button>
                )}
              </div>
            </div>
          );
        })}
        {messagingPlatforms.length === 0 && loaded && (
          <p className="text-sm text-zinc-500 text-center py-4">No messaging platforms available</p>
        )}
        {!loaded && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-2xl bg-surface-dark-2 border border-white/5 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-white/5" />
                  <div className="space-y-1.5"><div className="h-4 bg-white/5 rounded w-24" /><div className="h-3 bg-white/5 rounded w-16" /></div>
                </div>
                <div className="h-5 bg-white/5 rounded-full w-20" />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Webhook Info */}
      <div className="mt-4 rounded-xl bg-brand-600/5 border border-brand-500/10 p-4">
        <div className="flex gap-3">
          <Shield className="w-4 h-4 text-brand-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-zinc-400 leading-relaxed">
            <p className="font-medium text-zinc-300 mb-1">Webhook URLs</p>
            <p className="mb-2">Configure these webhook URLs in your platform settings to receive inbound messages:</p>
            <div className="space-y-1 font-mono text-[11px] text-zinc-500">
              <p><span className="text-zinc-300">WhatsApp:</span> {API_URL}/api/webhooks/whatsapp</p>
              <p><span className="text-zinc-300">Telegram:</span> {API_URL}/api/webhooks/telegram</p>
              <p><span className="text-zinc-300">Slack:</span> {API_URL}/api/webhooks/slack</p>
            </div>
          </div>
        </div>
      </div>

      {/* Token Connect Modal */}
      {connectModal && platformHelp[connectModal.platform] && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={() => setConnectModal(null)}>
          <div
            className="w-full max-w-md rounded-2xl bg-surface-dark-1 border border-white/10 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 mb-5">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/5 text-lg">
                {platformEmojis[connectModal.platform] || '💬'}
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Connect {connectModal.name}</h3>
                <p className="text-xs text-zinc-500">{platformHelp[connectModal.platform].helpText}</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-zinc-400 mb-1.5 block">
                  {platformHelp[connectModal.platform].label}
                </label>
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder={platformHelp[connectModal.platform].placeholder}
                  className="w-full px-3 py-2.5 rounded-xl bg-surface-dark-0 border border-white/10 text-sm text-zinc-200 placeholder-zinc-600 outline-none focus:border-brand-500/50 font-mono"
                  autoFocus
                />
              </div>

              {platformHelp[connectModal.platform].extraField && (
                <div>
                  <label className="text-xs font-medium text-zinc-400 mb-1.5 block">
                    {platformHelp[connectModal.platform].extraField!.label}
                  </label>
                  <input
                    type="text"
                    value={extraInput}
                    onChange={(e) => setExtraInput(e.target.value)}
                    placeholder={platformHelp[connectModal.platform].extraField!.placeholder}
                    className="w-full px-3 py-2.5 rounded-xl bg-surface-dark-0 border border-white/10 text-sm text-zinc-200 placeholder-zinc-600 outline-none focus:border-brand-500/50 font-mono"
                  />
                </div>
              )}

              <a
                href={platformHelp[connectModal.platform].helpUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1"
              >
                How to get your token <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setConnectModal(null)}
                className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-400 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleTokenConnect}
                disabled={!tokenInput.trim() || connecting}
                className="flex-1 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
              >
                {connecting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                {connecting ? 'Connecting...' : 'Connect'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AppearanceSection() {
  const [themeStore, setThemeStore] = useState<{
    colorTheme: string;
    setColorTheme: (t: 'midnight' | 'aurora' | 'ember' | 'ocean') => void;
  } | null>(null);
  const [agentName, setAgentName] = useState('Volo');
  const [savingName, setSavingName] = useState(false);

  useEffect(() => {
    let unsub: (() => void) | undefined;
    import('@/stores/themeStore').then(({ useThemeStore }) => {
      const s = useThemeStore.getState();
      setThemeStore({ colorTheme: s.colorTheme, setColorTheme: s.setColorTheme });
      unsub = useThemeStore.subscribe((state) =>
        setThemeStore({ colorTheme: state.colorTheme, setColorTheme: state.setColorTheme })
      );
    });
    return () => unsub?.();
  }, []);

  const themes = [
    { id: 'midnight' as const, name: 'Midnight', colors: ['#09090b', '#4c6ef5', '#e4e4e7'] },
    { id: 'aurora' as const, name: 'Aurora', colors: ['#0a0f0a', '#10b981', '#e4e4e7'] },
    { id: 'ember' as const, name: 'Ember', colors: ['#0f0a08', '#f59e0b', '#e4e4e7'] },
    { id: 'ocean' as const, name: 'Ocean', colors: ['#0a0f14', '#06b6d4', '#e4e4e7'] },
  ];

  const activeTheme = themeStore?.colorTheme ?? 'midnight';

  const selectTheme = (id: 'midnight' | 'aurora' | 'ember' | 'ocean') => {
    themeStore?.setColorTheme(id);
    toast.success(`Theme changed to ${themes.find(t => t.id === id)?.name}`);
  };

  const saveAgentName = async () => {
    setSavingName(true);
    try {
      await api.post('/api/config/agent-name', { name: agentName });
      toast.success('Agent name updated');
    } catch {
      toast.error('Failed to save agent name');
    }
    setSavingName(false);
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
        <h3 className="text-sm font-semibold text-zinc-200 mb-4">Theme</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => selectTheme(theme.id)}
              className={cn(
                'p-4 rounded-xl border transition-all text-center',
                activeTheme === theme.id
                  ? 'border-brand-500/50 bg-brand-500/5'
                  : 'border-white/5 hover:border-white/10 bg-surface-dark-0'
              )}
            >
              <div className="flex gap-1.5 justify-center mb-3">
                {theme.colors.map((c, i) => (
                  <div
                    key={i}
                    className="w-4 h-4 rounded-full border border-white/10"
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
              <p className="text-xs text-zinc-300 font-medium">{theme.name}</p>
              {activeTheme === theme.id && (
                <p className="text-[9px] text-brand-400 mt-1">Active</p>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
        <h3 className="text-sm font-semibold text-zinc-200 mb-4">Agent Name</h3>
        <div className="flex gap-2">
          <input
            type="text"
            value={agentName}
            onChange={(e) => setAgentName(e.target.value)}
            className="w-full max-w-xs px-3 py-2.5 rounded-xl bg-surface-dark-0 border border-white/10 text-sm text-zinc-200 outline-none focus:border-brand-500/50 transition-colors"
          />
          <button
            onClick={saveAgentName}
            disabled={savingName}
            className="px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            {savingName ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-[10px] text-zinc-600 mt-2">
          Change the agent&apos;s display name (white-label support).
        </p>
      </div>
    </div>
  );
}

function AccessibilitySection() {
  // Dynamic import to avoid SSR issues with zustand persist
  const [themeStore, setThemeStore] = useState<{
    fontSize: string;
    highContrast: boolean;
    reducedMotion: boolean;
    setFontSize: (s: 'small' | 'default' | 'large' | 'xl') => void;
    setHighContrast: (v: boolean) => void;
    setReducedMotion: (v: boolean) => void;
  } | null>(null);

  useEffect(() => {
    let unsub: (() => void) | undefined;
    import('@/stores/themeStore').then(({ useThemeStore }) => {
      const s = useThemeStore.getState();
      setThemeStore(s);
      unsub = useThemeStore.subscribe((state) => setThemeStore({ ...state }));
    });
    return () => unsub?.();
  }, []);

  if (!themeStore) return null;

  const fontSizes = [
    { id: 'small' as const, label: 'Small', desc: '14px base', sample: 'Aa' },
    { id: 'default' as const, label: 'Default', desc: '16px base', sample: 'Aa' },
    { id: 'large' as const, label: 'Large', desc: '18px base', sample: 'Aa' },
    { id: 'xl' as const, label: 'Extra Large', desc: '20px base', sample: 'Aa' },
  ];

  return (
    <div className="space-y-6">
      {/* Font Size */}
      <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
        <h3 className="text-sm font-semibold text-zinc-200 mb-2">Text Size</h3>
        <p className="text-xs text-zinc-500 mb-4">Adjust the base font size for better readability.</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {fontSizes.map((fs) => (
            <button
              key={fs.id}
              onClick={() => themeStore.setFontSize(fs.id)}
              className={cn(
                'p-4 rounded-xl border transition-all text-center min-h-[80px] flex flex-col items-center justify-center gap-1',
                themeStore.fontSize === fs.id
                  ? 'border-brand-500/50 bg-brand-500/10 text-brand-400'
                  : 'border-white/5 bg-surface-dark-0 text-zinc-400 hover:border-white/10'
              )}
              aria-label={`Set text size to ${fs.label}`}
              aria-pressed={themeStore.fontSize === fs.id}
            >
              <span style={{ fontSize: fs.desc.split('px')[0] + 'px' }} className="font-bold">{fs.sample}</span>
              <span className="text-xs font-medium">{fs.label}</span>
              <span className="text-[10px] text-zinc-500">{fs.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* High Contrast */}
      <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6">
        <h3 className="text-sm font-semibold text-zinc-200 mb-4">Visual Accessibility</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm text-zinc-200">High Contrast</p>
              <p className="text-xs text-zinc-500">Increase text contrast for better visibility</p>
            </div>
            <button
              onClick={() => themeStore.setHighContrast(!themeStore.highContrast)}
              className={cn(
                'w-12 h-7 rounded-full transition-colors relative min-h-[44px] min-w-[48px] flex items-center',
                themeStore.highContrast ? 'bg-brand-600' : 'bg-zinc-700'
              )}
              role="switch"
              aria-checked={themeStore.highContrast}
              aria-label="Toggle high contrast mode"
            >
              <div
                className={cn(
                  'w-5 h-5 rounded-full bg-white absolute transition-transform',
                  themeStore.highContrast ? 'translate-x-6' : 'translate-x-1'
                )}
              />
            </button>
          </div>

          <div className="flex items-center justify-between py-2">
            <div>
              <p className="text-sm text-zinc-200">Reduce Motion</p>
              <p className="text-xs text-zinc-500">Minimize animations and transitions</p>
            </div>
            <button
              onClick={() => themeStore.setReducedMotion(!themeStore.reducedMotion)}
              className={cn(
                'w-12 h-7 rounded-full transition-colors relative min-h-[44px] min-w-[48px] flex items-center',
                themeStore.reducedMotion ? 'bg-brand-600' : 'bg-zinc-700'
              )}
              role="switch"
              aria-checked={themeStore.reducedMotion}
              aria-label="Toggle reduced motion"
            >
              <div
                className={cn(
                  'w-5 h-5 rounded-full bg-white absolute transition-transform',
                  themeStore.reducedMotion ? 'translate-x-6' : 'translate-x-1'
                )}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Info */}
      <div className="rounded-xl bg-brand-600/5 border border-brand-500/10 p-4">
        <div className="flex gap-3">
          <Shield className="w-4 h-4 text-brand-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-zinc-400 leading-relaxed">
            <p className="font-medium text-zinc-300 mb-1">Accessibility Commitment</p>
            <p>Volo is designed to be usable by everyone. These settings are saved to your device and applied automatically on every visit.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function NotificationsSection() {
  const [settings, setSettings] = useState({
    tradeAlerts: true,
    priceAlerts: false,
    emailDigest: false,
    soundEnabled: true,
  });

  useEffect(() => {
    const saved = localStorage.getItem('volo-notification-settings');
    if (saved) {
      try { setSettings(JSON.parse(saved)); } catch {}
    }
  }, []);

  const toggle = (key: keyof typeof settings) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem('volo-notification-settings', JSON.stringify(next));
      api.post('/api/config/notifications', next).catch(() => {});
      return next;
    });
    toast.success('Setting updated');
  };

  return (
    <div className="rounded-2xl bg-surface-dark-2 border border-white/5 p-6 space-y-4">
      {[
        { key: 'tradeAlerts' as const, label: 'Trade Execution Alerts', desc: 'Notify when orders are filled' },
        { key: 'priceAlerts' as const, label: 'Price Alerts', desc: 'Notify on price target hits' },
        { key: 'emailDigest' as const, label: 'Email Digest', desc: 'Daily summary of agent activity' },
        { key: 'soundEnabled' as const, label: 'Sound Effects', desc: 'Play sounds for notifications' },
      ].map((item) => (
        <div key={item.key} className="flex items-center justify-between py-2">
          <div>
            <p className="text-sm text-zinc-200">{item.label}</p>
            <p className="text-xs text-zinc-500">{item.desc}</p>
          </div>
          <button
            onClick={() => toggle(item.key)}
            role="switch"
            aria-checked={settings[item.key]}
            aria-label={item.label}
            className={cn(
              'w-11 h-6 rounded-full transition-colors relative',
              settings[item.key] ? 'bg-brand-600' : 'bg-zinc-700'
            )}
          >
            <div
              className={cn(
                'w-5 h-5 rounded-full bg-white absolute top-0.5 transition-transform',
                settings[item.key] ? 'translate-x-[22px]' : 'translate-x-0.5'
              )}
            />
          </button>
        </div>
      ))}
    </div>
  );
}
