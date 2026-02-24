'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  Loader2,
  Check,
  Sparkles,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { toast } from 'sonner';
import { api, API_URL } from '@/lib/api';

/* ─── Social provider config ─── */
const socialProviders = [
  {
    id: 'google',
    name: 'Google',
    color: 'hover:bg-white/10 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
    ),
  },
  {
    id: 'apple',
    name: 'Apple',
    color: 'hover:bg-white/10 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-white">
        <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
      </svg>
    ),
  },
  {
    id: 'github',
    name: 'GitHub',
    color: 'hover:bg-white/10 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-white">
        <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/>
      </svg>
    ),
  },
  {
    id: 'twitter',
    name: 'X / Twitter',
    color: 'hover:bg-white/10 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
      </svg>
    ),
  },
  {
    id: 'discord',
    name: 'Discord',
    color: 'hover:bg-[#5865F2]/20 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#5865F2]">
        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
      </svg>
    ),
  },
  {
    id: 'facebook',
    name: 'Facebook',
    color: 'hover:bg-[#1877F2]/20 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#1877F2]">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>
    ),
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    color: 'hover:bg-[#0A66C2]/20 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#0A66C2]">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
    ),
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    color: 'hover:bg-white/10 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-white">
        <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.27 6.27 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.72a8.16 8.16 0 0 0 4.77 1.52V6.79a4.85 4.85 0 0 1-1.01-.1z"/>
      </svg>
    ),
  },
  {
    id: 'snapchat',
    name: 'Snapchat',
    color: 'hover:bg-[#FFFC00]/20 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#FFFC00]">
        <path d="M12.206.793c.99 0 4.347.276 5.93 3.821.529 1.193.403 3.219.299 4.847l-.003.06c-.012.18-.022.345-.03.51.075.045.203.09.401.09.3-.016.659-.12 1.033-.301.165-.088.344-.104.464-.104.182 0 .359.029.509.09.45.149.734.479.734.838.015.449-.39.839-1.213 1.168-.089.029-.209.075-.344.119-.45.135-1.139.36-1.333.81-.09.224-.061.524.12.868l.015.015c.06.136 1.526 3.475 4.791 4.014.255.044.435.27.42.509 0 .075-.015.149-.045.225-.24.569-1.273.988-3.146 1.271-.059.091-.12.375-.164.57-.029.179-.074.36-.134.553-.076.271-.27.405-.555.405h-.03a3.3 3.3 0 0 0-.553.06c-.27.046-.663.139-1.213.33-.723.254-1.39.376-2.061.376-.016 0-.031 0-.061-.004a6.85 6.85 0 0 1-1.49-.18c-.51-.135-1.065-.406-1.77-.749-.96-.449-1.529-.449-1.97-.449-.015 0-.06 0-.105.004a4.6 4.6 0 0 0-1.364.315 9.8 9.8 0 0 0-.94.38c-.18.088-.389.404-.524.584a2.9 2.9 0 0 1-.165.223c-.119.149-.314.225-.54.225a.7.7 0 0 1-.149-.016c-.27-.044-.449-.134-.555-.404a4.2 4.2 0 0 1-.12-.465c-.045-.194-.104-.48-.164-.57-1.873-.284-2.906-.702-3.146-1.271a.52.52 0 0 1-.044-.225c-.016-.24.164-.465.42-.509 3.264-.54 4.73-3.879 4.791-4.02l.016-.029c.18-.345.224-.645.119-.869-.195-.434-.884-.658-1.332-.809a3.1 3.1 0 0 1-.346-.119c-.625-.255-1.278-.72-1.213-1.168 0-.36.284-.69.734-.838.149-.06.33-.09.509-.09.12 0 .3.015.449.104.374.18.734.3 1.049.3.181 0 .315-.045.391-.09a68 68 0 0 1-.033-.569c-.104-1.627-.225-3.654.3-4.848C7.859 1.07 11.216.793 12.206.793z"/>
      </svg>
    ),
  },
  {
    id: 'instagram',
    name: 'Instagram',
    color: 'hover:bg-[#E4405F]/20 border-white/10',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5 fill-[#E4405F]">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/>
      </svg>
    ),
  },
];

export function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<string | null>(null);
  const [showMoreProviders, setShowMoreProviders] = useState(false);
  const { login } = useAuthStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    if (mode === 'register' && !name) return;

    setLoading(true);
    try {
      const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const body = mode === 'register'
        ? { email, password, name }
        : { email, password };

      const data = await api.post<{ user?: { id: string; email: string; name: string }; access_token?: string; refresh_token?: string }>(endpoint, body);
      const user = data.user;
      login(
        {
          id: user?.id || email,
          email: user?.email || email,
          name: user?.name || name || email.split('@')[0],
          provider: 'email',
          onboardingComplete: false,
        },
        data.access_token || 'dev-token'
      );
      toast.success(mode === 'register' ? 'Account created!' : 'Welcome back!');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Something went wrong';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSocialLogin = async (providerId: string) => {
    // Providers with real OAuth flows on the backend
    const oauthProviders = ['google', 'github', 'twitter', 'discord'];
    const providerName = socialProviders.find((p) => p.id === providerId)?.name || providerId;

    // Providers not yet implemented at all
    if (!oauthProviders.includes(providerId)) {
      toast.info(`${providerName} sign-in coming soon!`);
      return;
    }

    setSocialLoading(providerId);
    try {
      const data = await api.get<{ url?: string }>(`/api/auth/${providerId}`);
      if (data?.url && data.url.startsWith('http')) {
        window.location.href = data.url;
        return;
      }
      toast.error(`${providerName} OAuth not configured on this server.`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : `${providerName} login failed`;
      if (message.includes('501') || message.includes('not configured')) {
        toast.info(`${providerName} sign-in is not configured yet. Ask the admin to set it up.`);
      } else {
        toast.error(message);
      }
    } finally {
      setSocialLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-surface-dark-0 flex">
      {/* Left: Branding Panel */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-600/30 via-surface-dark-0 to-brand-900/20" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(92,124,250,0.15),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_right,rgba(66,99,235,0.1),transparent_50%)]" />

        <div className="relative z-10 flex flex-col justify-center px-16 py-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="flex items-center gap-4 mb-12">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/20">
                <Brain className="w-7 h-7 text-white" />
              </div>
              <span className="text-3xl font-bold tracking-tight gradient-text">VOLO</span>
            </div>

            <h1 className="text-5xl font-bold text-white leading-tight mb-6">
              Your AI<br />
              <span className="gradient-text">Life Operating System</span>
            </h1>

            <p className="text-lg text-zinc-400 mb-12 max-w-md leading-relaxed">
              One agent. Total control. Manage your code, finances, health, social life, and communications — all from one place.
            </p>

            <div className="space-y-4">
              {[
                { icon: <Sparkles className="w-5 h-5" />, text: 'AI-powered assistant that learns your preferences' },
                { icon: <Check className="w-5 h-5" />, text: 'Connect all your services in minutes' },
                { icon: <Mail className="w-5 h-5" />, text: 'Unified inbox for all messages & social media' },
              ].map((feature, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.15 }}
                  className="flex items-center gap-4"
                >
                  <div className="w-10 h-10 rounded-xl bg-brand-500/10 text-brand-400 flex items-center justify-center flex-shrink-0">
                    {feature.icon}
                  </div>
                  <span className="text-zinc-300">{feature.text}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right: Auth Form */}
      <div className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-bold tracking-tight gradient-text">VOLO</span>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-white mb-2">
              {mode === 'login' ? 'Welcome back' : 'Create your account'}
            </h2>
            <p className="text-sm text-zinc-400">
              {mode === 'login'
                ? 'Sign in to your Life OS'
                : 'Get started with Volo in seconds'}
            </p>
          </div>

          {/* Social Login Grid */}
          <div className="grid grid-cols-2 gap-2 mb-6">
            {socialProviders.slice(0, 4).map((provider) => (
              <button
                key={provider.id}
                onClick={() => handleSocialLogin(provider.id)}
                disabled={!!socialLoading}
                className={`flex items-center justify-center gap-2.5 px-4 py-3 rounded-xl border ${provider.color} bg-white/[0.03] transition-all duration-200 disabled:opacity-50 min-h-[48px]`}
                aria-label={`Sign in with ${provider.name}`}
              >
                {socialLoading === provider.id ? (
                  <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                ) : (
                  <>
                    {provider.icon}
                    <span className="text-sm text-zinc-300 font-medium">{provider.name}</span>
                  </>
                )}
              </button>
            ))}
          </div>

          {/* More social options */}
          <div className="mb-6 text-center">
            <button
              onClick={() => setShowMoreProviders(!showMoreProviders)}
              className="text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
            >
              <span className="border-b border-dashed border-zinc-600">
                {showMoreProviders ? 'Fewer options' : 'More sign-in options'}
              </span>
            </button>
            <AnimatePresence>
              {showMoreProviders && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="grid grid-cols-3 gap-2 mt-3">
                    {socialProviders.slice(4).map((provider) => (
                      <button
                        key={provider.id}
                        onClick={() => handleSocialLogin(provider.id)}
                        disabled={!!socialLoading}
                        className={`flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl border ${provider.color} bg-white/[0.03] transition-all duration-200 disabled:opacity-50 min-h-[48px]`}
                        aria-label={`Sign in with ${provider.name}`}
                      >
                        {socialLoading === provider.id ? (
                          <Loader2 className="w-5 h-5 animate-spin text-zinc-400" />
                        ) : (
                          <>
                            {provider.icon}
                            <span className="text-[11px] text-zinc-400">{provider.name}</span>
                          </>
                        )}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex-1 h-px bg-white/5" />
            <span className="text-xs text-zinc-500">or continue with email</span>
            <div className="flex-1 h-px bg-white/5" />
          </div>

          {/* Email Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <AnimatePresence mode="wait">
              {mode === 'register' && (
                <motion.div
                  key="name-field"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <label htmlFor="name" className="block text-sm text-zinc-400 mb-1.5 font-medium">Full name</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                      id="name"
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full pl-11 pr-4 py-3 rounded-xl bg-surface-dark-2 border border-white/5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 transition-all text-sm min-h-[48px]"
                      autoComplete="name"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label htmlFor="email" className="block text-sm text-zinc-400 mb-1.5 font-medium">Email address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full pl-11 pr-4 py-3 rounded-xl bg-surface-dark-2 border border-white/5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 transition-all text-sm min-h-[48px]"
                  autoComplete="email"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm text-zinc-400 mb-1.5 font-medium">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-12 py-3 rounded-xl bg-surface-dark-2 border border-white/5 text-white placeholder:text-zinc-600 focus:outline-none focus:border-brand-500/50 focus:ring-1 focus:ring-brand-500/20 transition-all text-sm min-h-[48px]"
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-white/5 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4 text-zinc-500" />
                  ) : (
                    <Eye className="w-4 h-4 text-zinc-500" />
                  )}
                </button>
              </div>
            </div>

            {mode === 'login' && (
              <div className="text-right">
                <button type="button" onClick={() => { if (!email) { toast.error('Enter your email first'); return; } api.post('/api/auth/forgot-password', { email }).then(() => toast.success('Password reset email sent!')).catch(() => toast.info('Password reset is not configured yet')); }} className="text-xs text-brand-400 hover:text-brand-300 transition-colors">
                  Forgot password?
                </button>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed min-h-[48px] text-sm"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  {mode === 'login' ? 'Sign in' : 'Create account'}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Toggle mode */}
          <p className="text-center text-sm text-zinc-500 mt-6">
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <button
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
              className="text-brand-400 hover:text-brand-300 font-medium transition-colors"
            >
              {mode === 'login' ? 'Sign up' : 'Sign in'}
            </button>
          </p>

          {/* Terms */}
          <p className="text-center text-[11px] text-zinc-600 mt-4 leading-relaxed">
            By continuing, you agree to Volo&apos;s{' '}
            <span className="text-zinc-500 underline cursor-pointer">Terms of Service</span>
            {' '}and{' '}
            <span className="text-zinc-500 underline cursor-pointer">Privacy Policy</span>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
