'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  User,
  Globe,
  Heart,
  MessageSquare,
  ArrowRight,
  ArrowLeft,
  Check,
  Brain,
  Youtube,
  Share2,
  Chrome,
  Dumbbell,
  Mail,
  Shield,
  Zap,
  Smartphone,
  Code2,
  Activity,
  TrendingUp,
  Bell,
  Terminal,
  FileCode,
  GitBranch,
  Layers,
  Link,
  Github,
  Twitter,
  Loader2,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface OnboardingWizardProps {
  onComplete: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [connectedAccounts, setConnectedAccounts] = useState<Record<string, boolean>>({});
  const [connectingAccount, setConnectingAccount] = useState<string | null>(null);
  const { updateUser, completeOnboarding } = useAuthStore();
  const pollRef = useRef<{ interval: NodeJS.Timeout; timeout: NodeJS.Timeout } | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current.interval);
        clearTimeout(pollRef.current.timeout);
      }
    };
  }, []);

  // Check which accounts are already connected
  const refreshConnectionStatus = useCallback(async () => {
    try {
      const [socialStatus, googleStatus, authProviders] = await Promise.all([
        api.get<{ platforms: { id: string; connected: boolean }[] }>('/api/social/connect/status').catch(() => ({ platforms: [] })),
        api.get<{ connected: boolean }>('/api/google/services').catch(() => ({ connected: false })),
        api.get<{ providers: Record<string, boolean> }>('/api/auth/providers').catch(() => ({ providers: {} })),
      ]);
      const status: Record<string, boolean> = {};
      for (const p of socialStatus.platforms || []) {
        status[p.id] = p.connected;
      }
      status.google = googleStatus.connected || false;
      setConnectedAccounts(status);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { refreshConnectionStatus(); }, [refreshConnectionStatus]);

  // Handle OAuth connect for onboarding
  const handleConnect = async (provider: string) => {
    setConnectingAccount(provider);
    try {
      let data: { url?: string; auth_url?: string };
      if (provider === 'google') {
        data = await api.get<{ auth_url: string }>('/api/google/auth-url');
        window.open(data.auth_url, '_blank', 'width=500,height=700');
      } else if (provider === 'twitter') {
        data = await api.get<{ url: string }>('/api/social/connect/twitter');
        window.open(data.url, '_blank', 'width=500,height=700');
      } else if (provider === 'github') {
        data = await api.get<{ url: string }>('/api/auth/github');
        window.open(data.url, '_blank', 'width=500,height=700');
      }
      // Listen for popup callback — clear interval when component unmounts or connection succeeds
      if (pollRef.current) { clearInterval(pollRef.current.interval); clearTimeout(pollRef.current.timeout); }
      const interval = setInterval(() => { refreshConnectionStatus(); }, 3000);
      const timeout = setTimeout(() => clearInterval(interval), 60000);
      pollRef.current = { interval, timeout };
    } catch {
      toast.error(`Could not start ${provider} connection`);
    } finally {
      setTimeout(() => setConnectingAccount(null), 2000);
    }
  };

  const interests = [
    { id: 'social', label: 'Social Media', icon: Share2, desc: 'Twitter, Instagram, TikTok, Reddit' },
    { id: 'messaging', label: 'Messaging', icon: MessageSquare, desc: 'WhatsApp, Telegram, iMessage' },
    { id: 'google', label: 'Google Services', icon: Chrome, desc: 'Gmail, Calendar, Drive, Photos' },
    { id: 'youtube', label: 'YouTube', icon: Youtube, desc: 'AI video summaries & subscriptions' },
    { id: 'health', label: 'Health & Fitness', icon: Dumbbell, desc: 'Steps, sleep, workouts, vitals' },
    { id: 'email', label: 'Email & Calendar', icon: Mail, desc: 'Inbox triage & meeting prep' },
  ];

  const toggleInterest = (id: string) => {
    setSelectedInterests((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const roles = [
    { label: 'Professional', emoji: '💼' },
    { label: 'Student', emoji: '🎓' },
    { label: 'Creator', emoji: '🎨' },
    { label: 'Developer', emoji: '💻' },
    { label: 'Entrepreneur', emoji: '🚀' },
    { label: 'Other', emoji: '✨' },
  ];

  /* ─── Feature showcase for the "What Volo Does" step ─── */
  const superpowers = [
    {
      icon: <Smartphone className="w-6 h-6" />,
      title: 'Code from Your Phone',
      desc: 'Write, edit, and run code on your desktop — right from your pocket. AI pair-programs with you and asks before running anything.',
      color: 'text-brand-400 bg-brand-500/10 border-brand-500/20',
    },
    {
      icon: <Layers className="w-6 h-6" />,
      title: 'One Feed, Every Platform',
      desc: 'Twitter, Instagram, email, messages — all in one unified feed. Post everywhere at once. Never switch apps again.',
      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
    },
    {
      icon: <Activity className="w-6 h-6" />,
      title: 'Health Dashboard',
      desc: 'Steps, sleep, heart rate, workouts — track everything. AI spots patterns and gives you insights that actually help.',
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    },
    {
      icon: <Brain className="w-6 h-6" />,
      title: 'AI That Knows You',
      desc: 'Chat with Volo about anything. The more you use it, the smarter it gets. It learns your preferences and adapts to you.',
      color: 'text-violet-400 bg-violet-500/10 border-violet-500/20',
    },
  ];

  interface StepDef {
    id: string;
    title: string;
    description: string;
    icon: React.ReactNode;
    iconBg: string;
    content?: React.ReactNode;
  }

  const STEPS: StepDef[] = [
    /* ── Step 0: Welcome / Meet Volo ── */
    {
      id: 'welcome',
      title: 'Meet Volo',
      description: 'Your AI Life Operating System — one place to manage your code, health, social media, messages, and more.',
      icon: <Sparkles className="w-7 h-7" />,
      iconBg: 'from-brand-500 to-brand-700',
      content: (
        <div className="space-y-4 mt-3">
          <p className="text-sm text-zinc-400 leading-relaxed">
            Think of Volo as <span className="text-white font-medium">mission control for your entire life</span>.
            Instead of jumping between 20 different apps, everything lives here — managed by AI that actually understands what you need.
          </p>
          <div className="grid grid-cols-3 gap-2.5">
            {[
              { icon: <Terminal className="w-4 h-4" />, label: 'Code', color: 'text-brand-400 bg-brand-500/10' },
              { icon: <Heart className="w-4 h-4" />, label: 'Health', color: 'text-rose-400 bg-rose-500/10' },
              { icon: <MessageSquare className="w-4 h-4" />, label: 'Messages', color: 'text-cyan-400 bg-cyan-500/10' },
              { icon: <Share2 className="w-4 h-4" />, label: 'Social', color: 'text-violet-400 bg-violet-500/10' },
              { icon: <TrendingUp className="w-4 h-4" />, label: 'Finance', color: 'text-emerald-400 bg-emerald-500/10' },
              { icon: <Bell className="w-4 h-4" />, label: 'Alerts', color: 'text-amber-400 bg-amber-500/10' },
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.06 }}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border border-white/5 ${item.color}`}
              >
                {item.icon}
                <span className="text-[11px] font-medium text-zinc-300">{item.label}</span>
              </motion.div>
            ))}
          </div>
          <div className="flex items-center gap-2 p-3 rounded-xl bg-brand-500/5 border border-brand-500/10">
            <Shield className="w-4 h-4 text-brand-400 flex-shrink-0" />
            <span className="text-xs text-zinc-400">
              <span className="text-zinc-300 font-medium">Your data stays yours.</span> Private, secure, and under your control.
            </span>
          </div>
        </div>
      ),
    },

    /* ── Step 1: What Volo Does / Superpowers ── */
    {
      id: 'superpowers',
      title: 'How Volo Makes Life Better',
      description: 'Here\'s what sets Volo apart — real superpowers, not buzzwords.',
      icon: <Zap className="w-7 h-7" />,
      iconBg: 'from-amber-500 to-orange-600',
      content: (
        <div className="space-y-2.5 mt-2">
          {superpowers.map((sp, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.08 + i * 0.08 }}
              className={`flex gap-3 p-3 rounded-xl border ${sp.color}`}
            >
              <div className="flex-shrink-0 mt-0.5">{sp.icon}</div>
              <div>
                <p className="text-sm font-semibold text-white">{sp.title}</p>
                <p className="text-xs text-zinc-400 leading-relaxed mt-0.5">{sp.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      ),
    },

    /* ── Step 2: Remote Coding Deep-Dive ── */
    {
      id: 'coding',
      title: 'Code From Anywhere',
      description: 'Your phone becomes a remote terminal to your desktop. AI writes, edits, and runs code — but always asks permission first.',
      icon: <Code2 className="w-7 h-7" />,
      iconBg: 'from-brand-500 to-indigo-600',
      content: (
        <div className="space-y-3 mt-2">
          {/* Simulated coding flow */}
          <div className="rounded-xl border border-white/5 bg-white/[0.02] overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 border-b border-white/5 bg-white/[0.02]">
              <FileCode className="w-3.5 h-3.5 text-brand-400" />
              <span className="text-xs text-zinc-400 font-mono">AI Coding Session</span>
            </div>
            <div className="p-3 space-y-2">
              {[
                { role: 'you', text: '"Add a dark mode toggle to the settings page"' },
                { role: 'volo', text: 'I\'ll create the toggle component and update the theme store.' },
                { role: 'action', text: '✏️ write_file → settings/ThemeToggle.tsx', status: 'Keep · Undo' },
                { role: 'action', text: '▶ run_command → npm run build', status: 'Allow · Skip' },
              ].map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 + i * 0.15 }}
                  className={`flex items-start gap-2 text-xs ${
                    msg.role === 'you' ? 'text-zinc-300 italic' :
                    msg.role === 'volo' ? 'text-zinc-400' :
                    'text-zinc-500'
                  }`}
                >
                  {msg.role === 'action' ? (
                    <div className="flex items-center justify-between w-full py-1 px-2 rounded-lg bg-white/[0.03] border border-white/5">
                      <span className="font-mono text-zinc-400">{msg.text}</span>
                      <span className="text-brand-400 font-medium text-[10px]">{msg.status}</span>
                    </div>
                  ) : (
                    <span>{msg.text}</span>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
            <Shield className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span className="text-xs text-zinc-400 leading-relaxed">
              <span className="text-emerald-300 font-medium">You&apos;re always in control.</span> Every file change has Keep/Undo. Every command needs your Allow/Skip.
            </span>
          </div>
        </div>
      ),
    },

    /* ── Step 3: Profile ── */
    {
      id: 'profile',
      title: 'About you',
      description: 'This helps Volo personalize your experience.',
      icon: <User className="w-7 h-7" />,
      iconBg: 'from-violet-500 to-purple-600',
      content: (
        <div className="space-y-5 mt-2">
          <div>
            <label htmlFor="onboard-name" className="block text-sm text-zinc-400 mb-2 font-medium">
              What should we call you?
            </label>
            <input
              id="onboard-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
              className="w-full px-4 py-3 rounded-xl bg-surface-dark-2 border border-white/5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 transition-all text-sm min-h-[48px]"
              autoComplete="name"
            />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-2 font-medium">
              I&apos;m a...
            </label>
            <div className="grid grid-cols-3 gap-2">
              {roles.map((r) => (
                <button
                  key={r.label}
                  onClick={() => setRole(r.label)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm transition-all min-h-[44px] ${
                    role === r.label
                      ? 'border-brand-500/50 bg-brand-500/10 text-brand-400'
                      : 'border-white/5 bg-white/[0.02] text-zinc-400 hover:bg-white/5'
                  }`}
                  aria-label={`Select role: ${r.label}`}
                >
                  <span>{r.emoji}</span>
                  <span>{r.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      ),
    },

    /* ── Step 4: Interests ── */
    {
      id: 'interests',
      title: 'What matters to you?',
      description: 'Select what you\'d like to use. You can change this anytime in Settings.',
      icon: <Globe className="w-7 h-7" />,
      iconBg: 'from-cyan-500 to-blue-600',
      content: (
        <div className="grid grid-cols-2 gap-3 mt-2">
          {interests.map((interest) => {
            const selected = selectedInterests.includes(interest.id);
            return (
              <button
                key={interest.id}
                onClick={() => toggleInterest(interest.id)}
                className={`flex flex-col items-start gap-2 p-4 rounded-xl border text-left transition-all min-h-[48px] ${
                  selected
                    ? 'border-brand-500/50 bg-brand-500/10'
                    : 'border-white/5 bg-white/[0.02] hover:bg-white/5'
                }`}
                aria-label={`${selected ? 'Deselect' : 'Select'} ${interest.label}`}
                aria-pressed={selected}
              >
                <div className="flex items-center justify-between w-full">
                  <interest.icon className={`w-5 h-5 ${selected ? 'text-brand-400' : 'text-zinc-500'}`} />
                  {selected && <Check className="w-4 h-4 text-brand-400" />}
                </div>
                <div>
                  <p className={`text-sm font-medium ${selected ? 'text-white' : 'text-zinc-300'}`}>{interest.label}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{interest.desc}</p>
                </div>
              </button>
            );
          })}
        </div>
      ),
    },

    /* ── Step 5: Connect Accounts ── */
    {
      id: 'connect',
      title: 'Connect Your Accounts',
      description: 'Link your accounts so Volo can pull in your real data — DMs, emails, subscriptions, and more.',
      icon: <Link className="w-7 h-7" />,
      iconBg: 'from-sky-500 to-blue-600',
      content: (
        <div className="space-y-3 mt-2">
          {[
            {
              id: 'google',
              label: 'Google',
              desc: 'Gmail, Calendar, YouTube & Drive',
              icon: <Globe className="w-5 h-5" />,
              color: 'text-red-400',
              border: 'border-red-500/30',
              bg: 'bg-red-500/10',
            },
            {
              id: 'twitter',
              label: 'Twitter / X',
              desc: 'Timeline, DMs & notifications',
              icon: <Twitter className="w-5 h-5" />,
              color: 'text-sky-400',
              border: 'border-sky-500/30',
              bg: 'bg-sky-500/10',
            },
            {
              id: 'github',
              label: 'GitHub',
              desc: 'Repos, issues & pull requests',
              icon: <Github className="w-5 h-5" />,
              color: 'text-purple-400',
              border: 'border-purple-500/30',
              bg: 'bg-purple-500/10',
            },
          ].map((acct) => {
            const isConnected = connectedAccounts[acct.id];
            const isConnecting = connectingAccount === acct.id;
            return (
              <motion.button
                key={acct.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                onClick={() => !isConnected && handleConnect(acct.id)}
                disabled={isConnecting}
                className={`w-full flex items-center gap-4 p-4 rounded-xl border text-left transition-all ${
                  isConnected
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : `${acct.border} ${acct.bg} hover:bg-white/5`
                }`}
              >
                <div className={`w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0 ${isConnected ? 'text-emerald-400' : acct.color}`}>
                  {isConnecting ? <Loader2 className="w-5 h-5 animate-spin" /> : isConnected ? <CheckCircle className="w-5 h-5" /> : acct.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium ${isConnected ? 'text-emerald-300' : 'text-white'}`}>
                    {isConnected ? `${acct.label} Connected` : `Connect ${acct.label}`}
                  </p>
                  <p className="text-xs text-zinc-500 mt-0.5">{acct.desc}</p>
                </div>
                {!isConnected && !isConnecting && (
                  <ExternalLink className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                )}
              </motion.button>
            );
          })}
          <p className="text-xs text-zinc-600 text-center pt-2">
            You can always connect more accounts later in Settings → Integrations
          </p>
        </div>
      ),
    },

    /* ── Step 6: Done ── */
    {
      id: 'done',
      title: 'You\'re all set!',
      description: 'Volo is ready to go. Here\'s how to get started:',
      icon: <Check className="w-7 h-7" />,
      iconBg: 'from-emerald-500 to-green-600',
      content: (
        <div className="space-y-3 mt-2">
          {[
            {
              icon: <Brain className="w-4 h-4" />,
              title: 'Chat with Volo',
              text: 'Ask anything — from "summarize my emails" to "deploy my app"',
              color: 'text-brand-400',
            },
            {
              icon: <GitBranch className="w-4 h-4" />,
              title: 'Connect a repo',
              text: 'Open the Code tab to link your GitHub and start coding remotely',
              color: 'text-violet-400',
            },
            {
              icon: <Globe className="w-4 h-4" />,
              title: 'Explore your dashboard',
              text: 'Social feed, health stats, and messages — all waiting for you',
              color: 'text-cyan-400',
            },
            {
              icon: <Heart className="w-4 h-4" />,
              title: 'It gets smarter over time',
              text: 'The more you use Volo, the better it understands you',
              color: 'text-rose-400',
            },
          ].map((tip, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.08 }}
              className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5"
            >
              <div className={`w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center flex-shrink-0 mt-0.5 ${tip.color}`}>
                {tip.icon}
              </div>
              <div>
                <p className="text-sm font-medium text-white">{tip.title}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{tip.text}</p>
              </div>
            </motion.div>
          ))}
        </div>
      ),
    },
  ];

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;
  const isFirst = step === 0;

  const handleNext = async () => {
    if (isLast) {
      if (name) updateUser({ name });
      // Save preferences to API
      try {
        const { api } = await import('@/lib/api');
        await api.post('/api/user/preferences', {
          name,
          role,
          interests: selectedInterests,
        });
      } catch {
        // Non-blocking — preferences saved locally anyway
      }
      completeOnboarding();
      onComplete();
      return;
    }
    setStep((s) => s + 1);
  };

  const handlePrev = () => setStep((s) => Math.max(0, s - 1));

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-surface-dark-1 border border-white/5 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl shadow-black/50"
      >
        {/* Progress Bar */}
        <div className="flex gap-1.5 px-6 pt-6">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${
                i <= step
                  ? 'bg-gradient-to-r from-brand-500 to-brand-600'
                  : 'bg-white/5'
              }`}
              role="progressbar"
              aria-valuenow={i <= step ? 100 : 0}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Step ${i + 1} of ${STEPS.length}`}
            />
          ))}
        </div>

        {/* Step Counter */}
        <div className="px-6 pt-3">
          <span className="text-xs text-zinc-500 font-medium">
            Step {step + 1} of {STEPS.length}
          </span>
        </div>

        {/* Step Content — scrollable for longer steps */}
        <AnimatePresence mode="wait">
          <motion.div
            key={current.id}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={{ duration: 0.25 }}
            className="px-6 py-6 max-h-[60vh] overflow-y-auto"
          >
            {/* Icon */}
            <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${current.iconBg} flex items-center justify-center text-white mb-5 shadow-lg`}>
              {current.icon}
            </div>

            {/* Title & Description */}
            <h2 className="text-2xl font-bold text-white mb-2">{current.title}</h2>
            <p className="text-sm text-zinc-400 leading-relaxed mb-4">{current.description}</p>

            {/* Dynamic Content */}
            {current.content}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center justify-between p-6 border-t border-white/5">
          <button
            onClick={handlePrev}
            disabled={isFirst}
            className="flex items-center gap-2 px-4 py-2.5 text-zinc-400 hover:text-white disabled:opacity-0 disabled:pointer-events-none transition-all rounded-xl hover:bg-white/5 min-h-[44px] text-sm"
            aria-label="Go back"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          <div className="flex gap-3">
            {!isFirst && !isLast && (
              <button
                onClick={handleNext}
                className="px-4 py-2.5 text-zinc-500 hover:text-zinc-300 transition-colors text-sm min-h-[44px]"
                aria-label="Skip this step"
              >
                Skip
              </button>
            )}
            <button
              onClick={handleNext}
              className="flex items-center gap-2 px-6 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl font-medium transition-all min-h-[44px] text-sm shadow-lg shadow-brand-500/20"
              aria-label={isLast ? 'Start using Volo' : 'Continue to next step'}
            >
              {isLast ? 'Launch Volo' : 'Continue'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
