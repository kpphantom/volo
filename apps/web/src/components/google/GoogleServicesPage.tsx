'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Mail, Calendar, Cloud, Youtube, Users, Image, CheckSquare, Heart,
  ChevronRight, Shield, LogIn, RefreshCw, CheckCircle, AlertCircle,
  ExternalLink, Inbox, Clock, Sparkles, Loader2,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';
import { toast } from 'sonner';
import { useAppStore } from '@/stores/appStore';
import { useTranslation } from '@/lib/i18n';

interface GoogleService {
  id: string;
  name: string;
  icon: string;
  connected: boolean;
  status: string;
}

interface GmailMessage {
  id: string;
  thread_id: string;
  subject: string;
  from: string;
  date: string;
  snippet: string;
  unread: boolean;
}

interface CalendarEvent {
  id: string;
  summary: string;
  description: string;
  start: string;
  end: string;
  location: string;
  status: string;
  html_link: string;
}

const iconMap: Record<string, typeof Mail> = {
  mail: Mail, calendar: Calendar, cloud: Cloud, video: Youtube,
  contacts: Users, image: Image, tasks: CheckSquare, fitness: Heart,
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
};

export function GoogleServicesPage() {
  const [services, setServices] = useState<GoogleService[]>([]);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<{ name?: string; email?: string; picture?: string } | null>(null);
  const [activeService, setActiveService] = useState<string | null>(null);
  const [emails, setEmails] = useState<GmailMessage[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingEmails, setLoadingEmails] = useState(false);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [summarizingEmail, setSummarizingEmail] = useState<string | null>(null);
  const [emailSummaries, setEmailSummaries] = useState<Record<string, string>>({});
  const { t } = useTranslation();

  const fetchServices = useCallback(async () => {
    try {
      const data = await api.get<{ services: GoogleService[]; connected: boolean }>('/api/google/services');
      setServices(data.services || []);
      setConnected(data.connected || false);
    } catch {
      setServices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchProfile = useCallback(async () => {
    try {
      const data = await api.get<{ name?: string | null; email?: string | null; picture?: string | null }>('/api/google/profile');
      if (data.name || data.email) {
        setProfile({ name: data.name || undefined, email: data.email || undefined, picture: data.picture || undefined });
      } else {
        setProfile(null);
      }
    } catch {
      setProfile(null);
    }
  }, []);

  const fetchEmails = useCallback(async () => {
    setLoadingEmails(true);
    try {
      const data = await api.get<{ emails: GmailMessage[]; unread_count: number }>('/api/google/gmail/messages');
      setEmails(data.emails || []);
      setUnreadCount(data.unread_count || 0);
    } catch {
      setEmails([]);
    } finally {
      setLoadingEmails(false);
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    setLoadingEvents(true);
    try {
      const data = await api.get<{ events: CalendarEvent[]; count: number }>('/api/google/calendar/events');
      setEvents(data.events || []);
    } catch {
      setEvents([]);
    } finally {
      setLoadingEvents(false);
    }
  }, []);

  useEffect(() => {
    fetchServices();
    fetchProfile();
  }, [fetchServices, fetchProfile]);

  useEffect(() => {
    if (connected) {
      fetchEmails();
      fetchEvents();
    }
  }, [connected, fetchEmails, fetchEvents]);

  // Listen for OAuth popup callback
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'google-connected' && event.data.success) {
        toast.success('Google account connected!');
        fetchServices();
        fetchProfile();
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [fetchServices, fetchProfile]);

  const handleGoogleSignIn = async () => {
    try {
      const data = await api.get<{ auth_url: string }>('/api/google/auth-url');
      window.open(data.auth_url, '_blank', 'width=500,height=700');
    } catch {
      toast.error('Could not get Google auth URL');
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const formatEventTime = (start: string, end: string) => {
    try {
      const s = new Date(start);
      const e = new Date(end);
      const opts: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' };
      return `${s.toLocaleTimeString([], opts)} - ${e.toLocaleTimeString([], opts)}`;
    } catch {
      return start;
    }
  };

  const parseFrom = (from: string) => {
    const match = from.match(/^(.+?)\s*<.+>$/);
    return match ? match[1].replace(/"/g, '') : from;
  };

  const handleSummarizeEmail = async (email: GmailMessage) => {
    if (emailSummaries[email.id]) {
      setEmailSummaries(prev => { const n = { ...prev }; delete n[email.id]; return n; });
      return;
    }
    setSummarizingEmail(email.id);
    try {
      const data = await api.post<{ summary: string }>('/api/ai/summarize', {
        content: `From: ${email.from}\nSubject: ${email.subject}\n\n${email.snippet}`,
        content_type: 'email',
        style: 'bullet_points',
      });
      setEmailSummaries(prev => ({ ...prev, [email.id]: data.summary }));
    } catch {
      toast.error('Could not summarize email');
    } finally {
      setSummarizingEmail(null);
    }
  };

  const serviceStats = (svc: GoogleService) => {
    if (!connected) return undefined;
    if (svc.id === 'gmail') return `${unreadCount} ${t('google.unread')}`;
    if (svc.id === 'calendar') return `${events.length} ${t('google.upcoming')}`;
    return undefined;
  };

  return (
    <div className="flex-1 overflow-y-auto bg-surface-dark-2">
      {/* Header */}
      <div className="border-b border-white/5 bg-surface-dark-1">
        <div className="max-w-6xl mx-auto px-3 sm:px-6 py-4 sm:py-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-3">
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 flex items-center justify-center shrink-0">
                  <span className="text-white font-bold text-base sm:text-lg">G</span>
                </div>
                <span className="truncate">{t('google.title')}</span>
              </h1>
              <p className="text-zinc-400 mt-1 text-sm">
                {connected
                  ? `${t('google.connectedAs')} ${profile?.email || 'user'} \u2014 ${t('google.allActive')}`
                  : t('google.connectDesc')}
              </p>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 shrink-0">
              {!connected && (
                <button
                  onClick={handleGoogleSignIn}
                  className="flex items-center gap-2 px-4 sm:px-5 py-2.5 bg-white text-gray-800 rounded-xl font-medium text-sm hover:bg-gray-100 transition-colors shadow-lg min-h-[44px]"
                >
                  <LogIn className="w-4 h-4" />
                  {t('google.signInWithGoogle')}
                </button>
              )}
              <button
                onClick={() => { fetchServices(); fetchProfile(); if (connected) { fetchEmails(); fetchEvents(); } }}
                className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-zinc-400 hover:text-white transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {profile && (
            <div className="mt-4 flex items-center gap-4 p-4 rounded-xl bg-white/5 border border-white/5">
              {profile.picture ? (
                <img src={profile.picture} alt="" className="w-12 h-12 rounded-full" />
              ) : (
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                  {profile.name?.[0] || 'G'}
                </div>
              )}
              <div className="flex-1">
                <p className="text-white font-medium">{profile.name}</p>
                <p className="text-zinc-400 text-sm">{profile.email}</p>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Shield className="w-4 h-4 text-green-400" />
                <span className="text-green-400">{t('google.secure')}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Services Grid */}
      <div className="max-w-6xl mx-auto px-3 sm:px-6 py-4 sm:py-6">
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
              const stats = serviceStats(service);
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
                    {service.connected ? t('google.connectedActive') : t('google.connectToEnable')}
                  </p>
                  {stats && (
                    <div className="mt-3 flex items-center justify-between">
                      <span className="text-xs text-zinc-400">{stats}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-white transition-colors" />
                    </div>
                  )}
                </motion.button>
              );
            })}
          </div>
        )}

        {/* Gmail Inbox */}
        {connected && activeService === 'gmail' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Mail className="w-5 h-5 text-red-400" />
                {t('google.gmailInbox')}
                {unreadCount > 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 font-medium">
                    {unreadCount} {t('google.unread')}
                  </span>
                )}
              </h2>
              <button onClick={fetchEmails} disabled={loadingEmails} className="text-xs text-zinc-400 hover:text-white flex items-center gap-1">
                <RefreshCw className={cn('w-3.5 h-3.5', loadingEmails && 'animate-spin')} /> {t('common.refresh')}
              </button>
            </div>
            {loadingEmails && emails.length === 0 ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-16 rounded-xl bg-white/5 animate-pulse" />
                ))}
              </div>
            ) : emails.length === 0 ? (
              <div className="text-center py-8 text-zinc-500">
                <Inbox className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{t('google.noEmails')}</p>
              </div>
            ) : (
              <div className="space-y-1">
                {emails.map((email) => (
                  <div
                    key={email.id}
                    className={cn(
                      'flex items-start gap-3 p-3 rounded-xl border transition-colors cursor-pointer',
                      email.unread
                        ? 'bg-white/[0.05] border-white/10'
                        : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.04]'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={cn('text-sm truncate', email.unread ? 'text-white font-semibold' : 'text-zinc-300')}>
                          {parseFrom(email.from)}
                        </span>
                        <span className="text-xs text-zinc-500 shrink-0">{formatDate(email.date)}</span>
                        {email.unread && <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />}
                      </div>
                      <p className={cn('text-sm truncate mt-0.5', email.unread ? 'text-zinc-200' : 'text-zinc-400')}>
                        {email.subject}
                      </p>
                      <p className="text-xs text-zinc-500 truncate mt-0.5">{email.snippet}</p>
                      <AnimatePresence>
                        {emailSummaries[email.id] && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-2 p-2 rounded-lg bg-brand-500/5 border border-brand-500/10">
                              <p className="text-xs text-zinc-300 flex items-start gap-1.5">
                                <Sparkles className="w-3 h-3 text-brand-400 mt-0.5 flex-shrink-0" />
                                {emailSummaries[email.id]}
                              </p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                    <button
                      onClick={() => handleSummarizeEmail(email)}
                      disabled={summarizingEmail === email.id}
                      className={cn(
                        'p-1.5 rounded-lg transition-colors shrink-0',
                        emailSummaries[email.id]
                          ? 'text-brand-400 bg-brand-500/10'
                          : 'text-zinc-500 hover:text-brand-400 hover:bg-white/10'
                      )}
                      title={t('google.summarizeEmail')}
                    >
                      {summarizingEmail === email.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* Calendar Events */}
        {connected && activeService === 'calendar' && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Calendar className="w-5 h-5 text-blue-400" />
                {t('google.upcomingEvents')}
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-medium">
                  {events.length}
                </span>
              </h2>
              <button onClick={fetchEvents} disabled={loadingEvents} className="text-xs text-zinc-400 hover:text-white flex items-center gap-1">
                <RefreshCw className={cn('w-3.5 h-3.5', loadingEvents && 'animate-spin')} /> {t('common.refresh')}
              </button>
            </div>
            {loadingEvents && events.length === 0 ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-20 rounded-xl bg-white/5 animate-pulse" />
                ))}
              </div>
            ) : events.length === 0 ? (
              <div className="text-center py-8 text-zinc-500">
                <Calendar className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>{t('google.noEvents')}</p>
              </div>
            ) : (
              <div className="space-y-2">
                {events.map((event) => (
                  <a
                    key={event.id}
                    href={event.html_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-start gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] hover:border-white/10 transition-colors block"
                  >
                    <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
                      <Calendar className="w-5 h-5 text-blue-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white font-medium text-sm">{event.summary}</p>
                      <p className="text-zinc-400 text-xs mt-1 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatEventTime(event.start, event.end)}
                      </p>
                      {event.location && (
                        <p className="text-zinc-500 text-xs mt-1 truncate">{event.location}</p>
                      )}
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-zinc-500 shrink-0 mt-1" />
                  </a>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* Quick Actions */}
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-white mb-4">{t('google.quickActions')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { label: t('google.checkEmail'), icon: Mail, desc: t('google.viewLatest'), color: 'text-red-400', svc: 'gmail' as const },
              { label: t('google.todayEvents'), icon: Calendar, desc: t('google.seeCalendar'), color: 'text-blue-400', svc: 'calendar' as const },
              { label: t('google.summarizeVideo'), icon: Youtube, desc: t('google.aiVideoSummary'), color: 'text-red-500', svc: null },
              { label: t('google.healthOverview'), icon: Heart, desc: t('google.fitnessDashboard'), color: 'text-green-400', svc: null },
            ].map((act) => (
              <button
                key={act.label}
                onClick={() => {
                  if (act.svc) { setActiveService(act.svc); }
                  else if (act.label === t('google.summarizeVideo')) { useAppStore.getState().setPage('youtube'); }
                  else { useAppStore.getState().setPage('health'); }
                }}
                className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.06] hover:border-white/10 transition-all text-left group"
              >
                <act.icon className={cn('w-5 h-5', act.color)} />
                <div>
                  <p className="text-white text-sm font-medium">{act.label}</p>
                  <p className="text-zinc-500 text-xs">{act.desc}</p>
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
