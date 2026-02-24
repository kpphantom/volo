'use client';

import { useState, useEffect } from 'react';
import {
  Mail, Calendar, Cloud, Youtube, Users, Image, CheckSquare, Heart,
  MapPin, StickyNote, FileText, Table2, ChevronRight, Shield, LogIn,
  RefreshCw, CheckCircle, AlertCircle, ExternalLink,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { useAppStore } from '@/stores/appStore';
import { useChatStore } from '@/stores/chatStore';

interface GoogleService {
  id: string;
  name: string;
  icon: string;
  connected: boolean;
  status: string;
}

const iconMap: Record<string, typeof Mail> = {
  mail: Mail, calendar: Calendar, cloud: Cloud, video: Youtube,
  contacts: Users, image: Image, tasks: CheckSquare, fitness: Heart,
  map: MapPin, 'sticky-note': StickyNote, 'file-text': FileText,
  table: Table2,
};

const colorMap: Record<string, string> = {
  gmail: 'from-red-500 to-red-600',
  calendar: 'from-blue-500 to-blue-600',
  drive: 'from-yellow-500 to-green-500',
  youtube: 'from-red-600 to-red-700',
  contacts: 'from-blue-400 to-blue-500',
  photos: 'from-amber-400 to-orange-500',
  tasks: 'from-blue-500 to-indigo-500',
  fitness: 'from-green-500 to-emerald-600',
  maps: 'from-green-600 to-green-700',
  keep: 'from-yellow-400 to-yellow-500',
  docs: 'from-blue-500 to-blue-600',
  sheets: 'from-green-500 to-green-600',
};

export function GoogleServicesPage() {
  const [services, setServices] = useState<GoogleService[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<{ name?: string; email?: string; picture?: string } | null>(null);
  const [activeService, setActiveService] = useState<string | null>(null);

  useEffect(() => {
    fetchServices();
    fetchProfile();
  }, []);

  const fetchServices = async () => {
    try {
      const data = await api.get<{ services: GoogleService[]; connected: boolean }>('/api/google/services');
      setServices(data.services || []);
      setConnected(data.connected || false);
    } catch {
      setServices([]);
      toast.error('Could not load Google services — check API connection');
    } finally {
      setLoading(false);
    }
  };

  const fetchProfile = async () => {
    try {
      const data = await api.get<{ name?: string; email?: string; picture?: string }>('/api/google/profile');
      setProfile(data);
    } catch {
      setProfile(null);
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      const data = await api.get<{ auth_url: string }>('/api/google/auth-url');
      window.open(data.auth_url, '_blank', 'width=500,height=600');
    } catch {
      toast.error('Could not get Google auth URL — check API credentials');
    }
  };

  const serviceDetails: Record<string, { description: string; stats: string }> = {
    gmail: { description: 'Read, compose, and manage your emails', stats: '12 unread' },
    calendar: { description: 'View and manage your calendar events', stats: '3 today' },
    drive: { description: 'Access your files and documents', stats: '15 GB used' },
    youtube: { description: 'Watch videos & get AI summaries', stats: '8 subscriptions' },
    contacts: { description: 'View and manage your contacts', stats: '342 contacts' },
    photos: { description: 'Browse your photo library', stats: '2,841 photos' },
    tasks: { description: 'View and manage your tasks', stats: '5 pending' },
    fitness: { description: 'Track your health & fitness data', stats: '8,432 steps today' },
    maps: { description: 'Saved places and directions', stats: '12 saved' },
    keep: { description: 'Notes and reminders', stats: '28 notes' },
    docs: { description: 'View and edit documents', stats: '45 documents' },
    sheets: { description: 'View and edit spreadsheets', stats: '12 sheets' },
  };

  return (
    <div className="flex-1 overflow-y-auto bg-surface-dark-2">
      {/* Header */}
      <div className="border-b border-white/5 bg-surface-dark-1">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 flex items-center justify-center">
                  <span className="text-white font-bold text-lg">G</span>
                </div>
                Google Services
              </h1>
              <p className="text-zinc-400 mt-1">
                {connected
                  ? `Connected as ${profile?.email || 'user'} — all services active`
                  : 'Connect your Google account to unlock all services'
                }
              </p>
            </div>
            <div className="flex items-center gap-3">
              {!connected && (
                <button
                  onClick={handleGoogleSignIn}
                  className="flex items-center gap-2 px-5 py-2.5 bg-white text-gray-800 rounded-xl font-medium text-sm hover:bg-gray-100 transition-colors shadow-lg"
                >
                  <LogIn className="w-4 h-4" />
                  Sign in with Google
                </button>
              )}
              <button
                onClick={fetchServices}
                className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Account Card */}
          {profile && (
            <div className="mt-4 flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/5">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                {profile.name?.[0] || 'V'}
              </div>
              <div className="flex-1">
                <p className="text-white font-medium">{profile.name}</p>
                <p className="text-zinc-400 text-sm">{profile.email}</p>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Shield className="w-4 h-4 text-green-400" />
                <span className="text-green-400">Secure</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Services Grid */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-40 rounded-2xl bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {services.map((service, idx) => {
              const Icon = iconMap[service.icon] || Mail;
              const gradient = colorMap[service.id] || 'from-gray-500 to-gray-600';
              const details = serviceDetails[service.id];
              const isActive = activeService === service.id;

              return (
                <motion.button
                  key={service.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  onClick={() => setActiveService(isActive ? null : service.id)}
                  className={cn(
                    'relative group text-left p-5 rounded-2xl border transition-all duration-200',
                    isActive
                      ? 'bg-white/10 border-white/20 ring-1 ring-brand-500/50'
                      : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06] hover:border-white/10'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className={cn('w-11 h-11 rounded-xl bg-gradient-to-br flex items-center justify-center', gradient)}>
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex items-center gap-1">
                      {service.connected ? (
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-zinc-500" />
                      )}
                    </div>
                  </div>
                  <h3 className="mt-3 text-white font-semibold text-sm">{service.name}</h3>
                  <p className="mt-1 text-zinc-500 text-xs line-clamp-2">
                    {details?.description || 'Google service'}
                  </p>
                  {details?.stats && (
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-xs text-zinc-400">{details.stats}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white transition-colors" />
                    </div>
                  )}
                  {service.status === 'demo' && (
                    <div className="absolute top-2 right-2">
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-medium">
                        DEMO
                      </span>
                    </div>
                  )}
                </motion.button>
              );
            })}
          </div>
        )}

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: 'Check Email', icon: Mail, desc: 'View latest emails', color: 'text-red-400' },
              { label: 'Today\'s Events', icon: Calendar, desc: 'See calendar', color: 'text-blue-400' },
              { label: 'Summarize Video', icon: Youtube, desc: 'AI video summary', color: 'text-red-500' },
              { label: 'Health Overview', icon: Heart, desc: 'Fitness dashboard', color: 'text-green-400' },
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => {
                  const setPage = useAppStore.getState().setPage;
                  if (action.label === 'Health Overview') {
                    setPage('health');
                  } else if (action.label === 'Summarize Video') {
                    setPage('youtube');
                  } else {
                    useChatStore.getState().setQueuedMessage(action.desc);
                    setPage('chat');
                  }
                }}
                className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] hover:border-white/10 transition-all text-left group"
              >
                <action.icon className={cn('w-5 h-5', action.color)} />
                <div>
                  <p className="text-white text-sm font-medium">{action.label}</p>
                  <p className="text-zinc-500 text-xs">{action.desc}</p>
                </div>
                <ExternalLink className="w-3.5 h-3.5 text-zinc-500 ml-auto opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
