'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  Brain,
  Code,
  TrendingUp,
  Mail,
  Calendar,
  Terminal,
  Sparkles,
  ArrowRight,
  Sun,
  Moon,
  Sunrise,
  Sunset,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { useTranslation } from '@/lib/i18n';

interface WelcomeScreenProps {
  onSuggestionClick: (text: string) => void;
}

const suggestions = [
  {
    icon: Sparkles,
    titleKey: 'suggestion.getStarted' as const,
    descKey: 'suggestion.getStarted.desc' as const,
    prompt: "Let's get started — help me set up Volo with all my tools and accounts.",
  },
  {
    icon: Code,
    titleKey: 'suggestion.projects' as const,
    descKey: 'suggestion.projects.desc' as const,
    prompt: 'Connect to my GitHub and show me an overview of all my projects.',
  },
  {
    icon: TrendingUp,
    titleKey: 'suggestion.trading' as const,
    descKey: 'suggestion.trading.desc' as const,
    prompt: 'Help me set up my trading integrations — brokerage, crypto, and market data.',
  },
  {
    icon: Mail,
    titleKey: 'suggestion.comms' as const,
    descKey: 'suggestion.comms.desc' as const,
    prompt: 'Connect my email and calendar so you can help me manage communications.',
  },
  {
    icon: Terminal,
    titleKey: 'suggestion.machine' as const,
    descKey: 'suggestion.machine.desc' as const,
    prompt: 'Set up remote machine access so you can execute tasks on my laptop.',
  },
  {
    icon: Calendar,
    titleKey: 'suggestion.briefing' as const,
    descKey: 'suggestion.briefing.desc' as const,
    prompt: 'Give me my morning briefing — calendar, tasks, markets, messages.',
  },
];

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  const [status, setStatus] = useState({ apiOnline: false, integrations: 0, memories: 0 });
  const user = useAuthStore((s) => s.user);
  const { t } = useTranslation();

  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    const firstName = user?.name?.split(' ')[0] || '';
    const name = firstName ? `, ${firstName}` : '';
    if (hour < 6) return { text: `${t('greeting.lateNight')}${name}?`, icon: Moon, sub: t('greeting.sub.lateNight') };
    if (hour < 12) return { text: `${t('greeting.morning')}${name}`, icon: Sunrise, sub: t('greeting.sub.morning') };
    if (hour < 17) return { text: `${t('greeting.afternoon')}${name}`, icon: Sun, sub: t('greeting.sub.afternoon') };
    if (hour < 21) return { text: `${t('greeting.evening')}${name}`, icon: Sunset, sub: t('greeting.sub.evening') };
    return { text: `${t('greeting.night')}${name}`, icon: Moon, sub: t('greeting.sub.night') };
  }, [user?.name, t]);

  useEffect(() => {
    let cancelled = false;
    const fetchStatus = async () => {
      try {
        const [healthRes, systemRes] = await Promise.allSettled([
          api.get('/health'),
          api.get<{ integrations_count?: number; memories_count?: number }>('/api/system/status'),
        ]);
        if (cancelled) return;
        setStatus({
          apiOnline: healthRes.status === 'fulfilled',
          integrations: systemRes.status === 'fulfilled' ? (systemRes.value as { integrations_count?: number }).integrations_count || 0 : 0,
          memories: systemRes.status === 'fulfilled' ? (systemRes.value as { memories_count?: number }).memories_count || 0 : 0,
        });
      } catch {
        if (!cancelled) setStatus({ apiOnline: false, integrations: 0, memories: 0 });
      }
    };
    fetchStatus();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-full px-3 sm:px-4 py-6 sm:py-12">
      {/* Logo & Welcome */}
      <div className="mb-6 sm:mb-10 text-center">
        <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center mx-auto mb-4 sm:mb-6 shadow-lg shadow-brand-500/20">
          <Brain className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 sm:mb-3 flex items-center justify-center gap-2">
          {<greeting.icon className="w-6 h-6 sm:w-7 sm:h-7 text-brand-400" />}
          {greeting.text}
        </h1>
        <p className="text-zinc-500 text-xs sm:text-sm max-w-md px-2">
          {greeting.sub}
        </p>
      </div>

      {/* Suggestion Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3 max-w-3xl w-full">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.titleKey}
            onClick={() => onSuggestionClick(suggestion.prompt)}
            className="group flex flex-col items-start gap-2 sm:gap-3 p-3 sm:p-4 rounded-2xl bg-surface-dark-2 border border-white/5 hover:border-brand-500/30 active:border-brand-500/50 hover:bg-surface-dark-3 transition-all text-left tap-none active:scale-[0.98]"
          >
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-brand-600/10 flex items-center justify-center group-hover:bg-brand-600/20 transition-colors">
              <suggestion.icon className="w-4 h-4 sm:w-5 sm:h-5 text-brand-400" />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-medium text-zinc-200 mb-0.5 sm:mb-1 flex items-center gap-1 sm:gap-2">
                {t(suggestion.titleKey)}
                <ArrowRight className="w-3 h-3 text-zinc-600 group-hover:text-brand-400 group-hover:translate-x-1 transition-all" />
              </h3>
              <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">
                {t(suggestion.descKey)}
              </p>
            </div>
          </button>
        ))}
      </div>

      {/* Status indicators */}
      <div className="flex items-center gap-4 sm:gap-6 mt-6 sm:mt-10 text-[11px] text-zinc-600">
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${status.apiOnline ? 'bg-emerald-500' : 'bg-red-500'}`} />
          {status.apiOnline ? t('status.online') : t('status.offline')}
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${status.integrations > 0 ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
          {status.integrations} {status.integrations !== 1 ? t('status.integrations_plural') : t('status.integrations')}
        </div>
        <div className="flex items-center gap-1.5">
          <span className={`w-1.5 h-1.5 rounded-full ${status.memories > 0 ? 'bg-emerald-500' : 'bg-zinc-600'}`} />
          {status.memories > 0 ? `${status.memories} ${t('status.memories')}` : t('status.memoryEmpty')}
        </div>
      </div>
    </div>
  );
}
